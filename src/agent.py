from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def answer(
        self,
        question: str,
        top_k: int = 3,
        metadata_filter: dict | None = None,
    ) -> str:
        if metadata_filter is None:
            results = self.store.search(question, top_k=top_k)
        else:
            results = self.store.search_with_filter(
                question,
                top_k=top_k,
                metadata_filter=metadata_filter,
            )
        if not results:
            return "Không tìm thấy ngữ cảnh phù hợp trong cơ sở tri thức để trả lời câu hỏi."

        context_parts: list[str] = []
        for index, result in enumerate(results, start=1):
            metadata = result.get("metadata") or {}
            doc_id = metadata.get("doc_id") or result.get("id") or "unknown"
            source = metadata.get("source_url") or metadata.get("source") or doc_id
            context_parts.append(
                f"[{index}] doc_id: {doc_id}\n"
                f"source: {source}\n"
                f"{result['content']}"
            )

        context = "\n\n".join(context_parts)
        prompt = (
            "Bạn là trợ lý hỏi đáp dựa trên cơ sở tri thức. "
            "Chỉ sử dụng thông tin trong Context để trả lời. "
            "Hãy dẫn nguồn bằng số thứ tự như [1], [2]. "
            "Nếu Context không đủ thông tin, hãy nói rõ rằng không đủ thông tin.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )
        return self.llm_fn(prompt)
