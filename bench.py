"""Run the locked five-query benchmark for one chunking strategy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

from ingest import build_knowledge_base, load_documents
from src import (
    ChunkingStrategyComparator,
    OPENROUTER_CHAT_MODEL,
    OPENROUTER_EMBEDDING_DIMENSIONS,
    OPENROUTER_EMBEDDING_MODEL,
    HeadingBasedChunker,
    KnowledgeBaseAgent,
    OpenRouterEmbedder,
    OpenRouterLLM,
)

PROJECT_ROOT = Path(__file__).resolve().parent
BENCHMARK_FILE = PROJECT_ROOT / "data" / "benchmark_queries.json"
TOP_K = 3
BASELINE_DOCUMENT_COUNT = 3
BASELINE_CHUNK_SIZE = 200
REQUIRED_QUERY_FIELDS = {
    "id",
    "query",
    "gold_answer",
    "expected_source",
    "expected_sections",
    "evidence_keywords",
    "metadata_filter",
}


class CachedEmbedder:
    """Disk cache keyed by backend configuration, mode, and exact content."""

    def __init__(self, embedder, cache_dir: Path) -> None:
        self.embedder = embedder
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._backend_name = f"{embedder._backend_name} + SHA-256 cache"

    def _get_or_create(
        self,
        mode: str,
        text: str,
        factory: Callable[[], list[float]],
    ) -> list[float]:
        identity = f"{self.embedder._backend_name}\0{mode}\0{text}"
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        path = self.cache_dir / f"{digest}.json"
        if path.exists():
            return [float(value) for value in json.loads(path.read_text("utf-8"))]

        vector = [float(value) for value in factory()]
        temporary_path = path.with_suffix(".tmp")
        temporary_path.write_text(json.dumps(vector), encoding="utf-8")
        temporary_path.replace(path)
        return vector

    def __call__(self, text: str) -> list[float]:
        return self._get_or_create("text", text, lambda: self.embedder(text))

    def embed_document(self, text: str, title: str | None = None) -> list[float]:
        method = getattr(self.embedder, "embed_document", None)
        if not callable(method):
            return self(text)
        mode = f"document:{title or ''}"
        return self._get_or_create(mode, text, lambda: method(text, title=title))

    def embed_query(self, text: str) -> list[float]:
        method = getattr(self.embedder, "embed_query", None)
        if not callable(method):
            return self(text)
        return self._get_or_create("query", text, lambda: method(text))


def load_locked_benchmark() -> tuple[list[dict], str]:
    raw = BENCHMARK_FILE.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    queries = json.loads(raw.decode("utf-8"))
    if not isinstance(queries, list) or len(queries) != 5:
        raise ValueError("data/benchmark_queries.json must contain exactly 5 queries")

    ids: set[int] = set()
    for index, item in enumerate(queries, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Benchmark item {index} must be an object")
        missing = REQUIRED_QUERY_FIELDS - item.keys()
        if missing:
            raise ValueError(
                f"Benchmark item {index} is missing: {', '.join(sorted(missing))}"
            )
        if item["id"] in ids:
            raise ValueError(f"Duplicate benchmark id: {item['id']}")
        ids.add(item["id"])
    return queries, digest


def preview(text: str, limit: int = 180) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact if len(compact) <= limit else compact[: limit - 3] + "..."


def retrieve(store, benchmark: dict, top_k: int = 3) -> list[dict]:
    metadata_filter = benchmark["metadata_filter"]
    if metadata_filter is None:
        return store.search(benchmark["query"], top_k=top_k)
    return store.search_with_filter(
        benchmark["query"],
        top_k=top_k,
        metadata_filter=metadata_filter,
    )


def evaluate_result(result: dict, benchmark: dict) -> dict:
    metadata = result.get("metadata") or {}
    source_name = Path(str(metadata.get("source", ""))).name
    content_lower = result["content"].casefold()
    matched_sections = [
        section
        for section in benchmark["expected_sections"]
        if section.casefold() in content_lower
    ]
    matched_keywords = [
        keyword
        for keyword in benchmark["evidence_keywords"]
        if keyword.casefold() in content_lower
    ]
    return {
        "id": result.get("id"),
        "score": float(result["score"]),
        "doc_id": metadata.get("doc_id"),
        "chunk_index": metadata.get("chunk_index"),
        "source": source_name,
        "expected_source_match": source_name == benchmark["expected_source"],
        "matched_sections": matched_sections,
        "matched_keywords": matched_keywords,
        "preview": preview(result["content"]),
    }


def run_baseline(data_dir: Path) -> list[dict]:
    """Compare built-in strategies on parsed bodies, never YAML front matter."""
    documents = load_documents(data_dir)[:BASELINE_DOCUMENT_COUNT]
    comparator = ChunkingStrategyComparator()
    rows: list[dict] = []
    print("\n=== BASELINE (front matter removed) ===")
    for document in documents:
        comparison = comparator.compare(
            document.content,
            chunk_size=BASELINE_CHUNK_SIZE,
        )
        for strategy, stats in comparison.items():
            row = {
                "doc_id": document.id,
                "strategy": strategy,
                "count": stats["count"],
                "avg_length": float(stats["avg_length"]),
            }
            rows.append(row)
            print(
                f"doc_id={document.id} strategy={strategy} "
                f"count={stats['count']} avg_length={stats['avg_length']:.2f}"
            )
    return rows


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        default=os.getenv(
            "LAB_DATA_DIR", "data/k4_ecommerce_dang_van_nhan"
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.is_absolute():
        data_dir = PROJECT_ROOT / data_dir
    if not data_dir.exists():
        parser.error(f"Corpus directory does not exist: {data_dir}")

    benchmarks, benchmark_sha256 = load_locked_benchmark()
    baseline_rows = run_baseline(data_dir)

    # STRATEGY: this is the only experiment-specific line shared members change.
    chunker = HeadingBasedChunker(chunk_size=1000)
    strategy_name = chunker.__class__.__name__
    strategy_params = {
        key: value
        for key, value in vars(chunker).items()
        if not key.startswith("_")
    }
    strategy_slug = re.sub(r"(?<!^)(?=[A-Z])", "_", strategy_name).lower()
    strategy_slug = re.sub(r"[^a-z0-9]+", "_", strategy_slug).strip("_")

    raw_embedder = OpenRouterEmbedder(
        model_name=os.getenv(
            "OPENROUTER_EMBEDDING_MODEL", OPENROUTER_EMBEDDING_MODEL
        ),
        dimensions=int(
            os.getenv(
                "OPENROUTER_EMBEDDING_DIMENSIONS",
                str(OPENROUTER_EMBEDDING_DIMENSIONS),
            )
        ),
    )
    embedding_fn = CachedEmbedder(
        raw_embedder,
        PROJECT_ROOT / ".embedding_cache",
    )
    store = build_knowledge_base(
        data_dir,
        embedding_fn,
        chunker=chunker,
        collection_name=f"benchmark_{strategy_slug}",
    )
    llm = OpenRouterLLM(
        model_name=os.getenv("OPENROUTER_CHAT_MODEL", OPENROUTER_CHAT_MODEL)
    )
    agent = KnowledgeBaseAgent(store=store, llm_fn=llm)

    print("=== LOCKED RETRIEVAL BENCHMARK ===")
    print(f"benchmark_file={BENCHMARK_FILE.relative_to(PROJECT_ROOT)}")
    print(f"benchmark_sha256={benchmark_sha256}")
    print(f"strategy={strategy_name}")
    print(f"strategy_params={strategy_params}")
    print(f"corpus={data_dir}")
    print(f"embedder={embedding_fn._backend_name}")
    print(f"chunks={store.get_collection_size()}")

    output_rows: list[dict] = []
    top3_source_hits = 0
    for benchmark in benchmarks:
        results = retrieve(store, benchmark, top_k=TOP_K)
        evaluated_results = [
            evaluate_result(result, benchmark) for result in results
        ]
        source_hit = any(
            result["expected_source_match"] for result in evaluated_results[:3]
        )
        top3_source_hits += int(source_hit)
        answer = agent.answer(
            benchmark["query"],
            top_k=TOP_K,
            metadata_filter=benchmark["metadata_filter"],
        )

        print(f"\n--- Query {benchmark['id']} ---")
        print(f"question: {benchmark['query']}")
        print(f"filter: {benchmark['metadata_filter']}")
        print(f"expected_source: {benchmark['expected_source']}")
        for rank, result in enumerate(evaluated_results, start=1):
            print(
                f"[{rank}] score={result['score']:.6f} "
                f"doc_id={result['doc_id']} chunk={result['chunk_index']} "
                f"source={result['source']}"
            )
            print(f"    preview={result['preview']}")
            print(
                f"    expected_source_match={result['expected_source_match']} "
                f"evidence={result['matched_keywords']}"
            )
        print(f"agent_answer: {answer}")
        print(f"gold_answer: {benchmark['gold_answer']}")

        output_rows.append(
            {
                "benchmark": benchmark,
                "retrieval": evaluated_results,
                "top3_expected_source_hit": source_hit,
                "agent_answer": answer,
            }
        )

    summary = {
        "benchmark_file": str(BENCHMARK_FILE.relative_to(PROJECT_ROOT)),
        "benchmark_sha256": benchmark_sha256,
        "strategy": strategy_name,
        "strategy_params": strategy_params,
        "corpus": str(data_dir),
        "embedder": embedding_fn._backend_name,
        "chunk_count": store.get_collection_size(),
        "top3_expected_source_hits": top3_source_hits,
        "query_count": len(benchmarks),
        "baseline": baseline_rows,
        "results": output_rows,
    }
    output_path = Path(
        args.output or f"report/benchmark_{strategy_slug}.json"
    )
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nsummary: top3_expected_source_hits={top3_source_hits}/5")
    print(f"output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
