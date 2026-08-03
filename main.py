from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from ingest import build_knowledge_base
from src.agent import KnowledgeBaseAgent
from src.chunking import HeadingBasedChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_DIMENSIONS,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    OPENROUTER_EMBEDDING_DIMENSIONS,
    OPENROUTER_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    OpenRouterEmbedder,
    _mock_embed,
)
from src.llms import OPENROUTER_CHAT_MODEL, OpenRouterLLM
from src.store import EmbeddingStore
from src.supabase_store import SupabaseEmbeddingStore

# Thư mục dữ liệu mặc định cho demo = bộ khởi động cố định của lớp K4.
# Đổi bằng biến môi trường: LAB_DATA_DIR=data/<thu-muc-cua-nhom> python3 main.py
DEFAULT_DATA_DIR = "data/k4_ecommerce"


def _select_embedder():
    """Chọn backend: mock | local | openai | gemini | openrouter."""
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    if provider == "local":
        try:
            return LocalEmbedder(model_name=os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL))
        except Exception:
            print("Local embedder không sẵn sàng; tạm dùng mock.")
            return _mock_embed
    if provider == "openai":
        try:
            return OpenAIEmbedder(model_name=os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL))
        except Exception:
            print("OpenAI embedder không sẵn sàng; tạm dùng mock.")
            return _mock_embed
    if provider == "openrouter":
        try:
            dimensions = int(
                os.getenv(
                    "OPENROUTER_EMBEDDING_DIMENSIONS",
                    str(OPENROUTER_EMBEDDING_DIMENSIONS),
                )
            )
            return OpenRouterEmbedder(
                model_name=os.getenv(
                    "OPENROUTER_EMBEDDING_MODEL", OPENROUTER_EMBEDDING_MODEL
                ),
                dimensions=dimensions,
            )
        except Exception as exc:
            print(f"OpenRouter embedder không sẵn sàng ({exc}); tạm dùng mock.")
            return _mock_embed
    if provider == "gemini":
        try:
            dimensions = int(
                os.getenv("GEMINI_EMBEDDING_DIMENSIONS", str(GEMINI_EMBEDDING_DIMENSIONS))
            )
            return GeminiEmbedder(
                model_name=os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL),
                output_dimensionality=dimensions,
            )
        except Exception as exc:
            print(f"Gemini embedder không sẵn sàng ({exc}); tạm dùng mock.")
            return _mock_embed
    return _mock_embed


def demo_llm(prompt: str) -> str:
    """LLM giả lập đơn giản để thử RAG thủ công."""
    preview = prompt[:400].replace("\n", " ")
    return f"[DEMO LLM] Generated answer from prompt preview: {preview}..."


def _select_llm():
    provider = os.getenv("LLM_PROVIDER", "demo").strip().lower()
    if provider == "openrouter":
        return OpenRouterLLM(
            model_name=os.getenv("OPENROUTER_CHAT_MODEL", OPENROUTER_CHAT_MODEL)
        )
    return demo_llm


def run_manual_demo(question: str | None = None, data_dir: str | None = None) -> int:
    data_dir = data_dir or DEFAULT_DATA_DIR
    query = question or "Tóm tắt thông tin chính từ bộ tài liệu."

    print("=== Demo pipeline nạp dữ liệu (ingest.build_knowledge_base) ===")
    print(f"Thư mục dữ liệu: {data_dir}")
    if not Path(data_dir).exists():
        print(f"Không tìm thấy thư mục dữ liệu: {data_dir}")
        print("Thu thập tài liệu vào thư mục này (xem docs/DATA_COLLECTION.md) rồi chạy lại:")
        print("  python3 main.py")
        return 1

    embedder = _select_embedder()
    backend = getattr(embedder, "_backend_name", embedder.__class__.__name__)
    print(f"Backend nhúng: {backend}")
    if backend == "mock embeddings fallback":
        print(
            "Lưu ý: mock chỉ để chạy thử/unit test và KHÔNG phản ánh chất lượng ngữ nghĩa. "
            "Ở Giai đoạn 2, đặt EMBEDDING_PROVIDER=local để so sánh retrieval có ý nghĩa."
        )

    # Chính sách K4 là Markdown có cấu trúc nên demo dùng heading-based chunking.
    chunker = HeadingBasedChunker(
        chunk_size=int(os.getenv("HEADING_CHUNK_SIZE", "1000")),
    )
    print(f"Chunker: HeadingBasedChunker (chunk_size={chunker.chunk_size})")

    store_provider = os.getenv("VECTOR_STORE_PROVIDER", "memory").strip().lower()
    store_class = SupabaseEmbeddingStore if store_provider == "supabase" else EmbeddingStore
    print(f"Vector store: {store_provider}")

    # Pipeline: parse front matter -> heading chunks -> embedding -> vector store.
    store = build_knowledge_base(
        data_dir,
        embedding_fn=embedder,
        chunker=chunker,
        store_class=store_class,
    )
    print(f"Đã nạp {store.get_collection_size()} chunk vào EmbeddingStore")

    print("\n=== Tìm kiếm (EmbeddingStore.search) ===")
    print(f"Câu hỏi: {query}")
    for index, result in enumerate(store.search(query, top_k=3), start=1):
        print(f"{index}. score={result['score']:.3f} source={result['metadata'].get('source')}")
        print(f"   {result['content'][:120].replace(chr(10), ' ')}...")

    print("\n=== KnowledgeBaseAgent ===")
    llm = _select_llm()
    print(f"LLM: {getattr(llm, '_backend_name', 'demo')}")
    agent = KnowledgeBaseAgent(store=store, llm_fn=llm)
    print(agent.answer(query, top_k=3))
    return 0


def main() -> int:
    question = " ".join(sys.argv[1:]).strip() or None
    data_dir = os.getenv("LAB_DATA_DIR", DEFAULT_DATA_DIR)
    return run_manual_demo(question=question, data_dir=data_dir)


if __name__ == "__main__":
    raise SystemExit(main())
