from __future__ import annotations

import os
from typing import Any, Callable

from .embeddings import _mock_embed
from .models import Document


class SupabaseEmbeddingStore:
    """Persistent pgvector store backed by Supabase.

    Run ``supabase/schema.sql`` once in the Supabase SQL editor before using
    this class. The schema expects 768-dimensional embeddings by default.
    """

    TABLE_NAME = "document_chunks"
    MATCH_FUNCTION = "match_document_chunks"

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        client: Any | None = None,
        batch_size: int = 100,
        vector_dimensions: int | None = None,
    ) -> None:
        dimensions = vector_dimensions
        if dimensions is None:
            dimensions = int(os.getenv("SUPABASE_VECTOR_DIMENSIONS", "768"))
        if not collection_name.strip():
            raise ValueError("collection_name must not be empty")
        if batch_size < 1:
            raise ValueError("batch_size must be greater than zero")
        if dimensions < 1:
            raise ValueError("vector_dimensions must be greater than zero")

        self._collection_name = collection_name
        self._embedding_fn = embedding_fn or _mock_embed
        self._batch_size = batch_size
        self._vector_dimensions = dimensions

        if client is not None:
            self._client = client
            return

        url = supabase_url or os.getenv("SUPABASE_URL")
        key = supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )

        from supabase import create_client

        self._client = create_client(url, key)

    def _make_record(self, doc: Document) -> dict[str, Any]:
        metadata = dict(doc.metadata)
        doc_id = str(metadata.get("doc_id") or doc.id)
        metadata.setdefault("doc_id", doc_id)
        embed_document = getattr(self._embedding_fn, "embed_document", None)
        if callable(embed_document):
            embedding = embed_document(doc.content, title=metadata.get("title"))
        else:
            embedding = self._embedding_fn(doc.content)
        return {
            "collection_name": self._collection_name,
            "chunk_id": doc.id,
            "doc_id": doc_id,
            "content": doc.content,
            "metadata": metadata,
            "embedding": self._validate_embedding(embedding),
        }

    def _validate_embedding(self, embedding: list[float]) -> list[float]:
        vector = [float(value) for value in embedding]
        if len(vector) != self._vector_dimensions:
            raise ValueError(
                f"Expected a {self._vector_dimensions}-dimensional embedding, "
                f"received {len(vector)} dimensions"
            )
        return vector

    def add_documents(self, docs: list[Document]) -> None:
        """Embed and idempotently upsert chunks in bounded batches."""
        records = [self._make_record(doc) for doc in docs]
        for start in range(0, len(records), self._batch_size):
            batch = records[start : start + self._batch_size]
            (
                self._client.table(self.TABLE_NAME)
                .upsert(batch, on_conflict="collection_name,chunk_id")
                .execute()
            )

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return self.search_with_filter(query, top_k=top_k)

    def search_with_filter(
        self,
        query: str,
        top_k: int = 3,
        metadata_filter: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Run cosine search and apply a JSONB containment filter in SQL."""
        if top_k <= 0:
            return []

        embed_query = getattr(self._embedding_fn, "embed_query", None)
        embedding = (
            embed_query(query) if callable(embed_query) else self._embedding_fn(query)
        )
        query_embedding = self._validate_embedding(embedding)
        response = self._client.rpc(
            self.MATCH_FUNCTION,
            {
                "p_query_embedding": query_embedding,
                "p_match_count": min(top_k, 200),
                "p_collection_name": self._collection_name,
                "p_filter_metadata": metadata_filter or {},
            },
        ).execute()

        return [
            {
                "id": row["id"],
                "content": row["content"],
                "metadata": row.get("metadata") or {},
                "score": float(row["similarity"]),
            }
            for row in (response.data or [])
        ]

    def get_collection_size(self) -> int:
        response = (
            self._client.table(self.TABLE_NAME)
            .select("chunk_id", count="exact")
            .eq("collection_name", self._collection_name)
            .execute()
        )
        return int(
            response.count if response.count is not None else len(response.data or [])
        )

    def delete_document(self, doc_id: str) -> bool:
        response = (
            self._client.table(self.TABLE_NAME)
            .delete()
            .eq("collection_name", self._collection_name)
            .eq("doc_id", doc_id)
            .execute()
        )
        return bool(response.data)
