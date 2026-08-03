from __future__ import annotations

import hashlib
import math

# Multilingual model suitable for the Vietnamese corpora used in this Lab.
# The local backend remains optional; required checkpoints use MockEmbedder.
LOCAL_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENROUTER_EMBEDDING_MODEL = "openai/text-embedding-3-small"
OPENROUTER_EMBEDDING_DIMENSIONS = 768
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GEMINI_EMBEDDING_MODEL = "gemini-embedding-2"
GEMINI_EMBEDDING_DIMENSIONS = 768
EMBEDDING_PROVIDER_ENV = "EMBEDDING_PROVIDER"


class MockEmbedder:
    """Deterministic embedding backend used by tests and default classroom runs."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim
        self._backend_name = "mock embeddings fallback"

    def __call__(self, text: str) -> list[float]:
        digest = hashlib.md5(text.encode()).hexdigest()
        seed = int(digest, 16)
        vector = []
        for _ in range(self.dim):
            seed = (seed * 1664525 + 1013904223) & 0xFFFFFFFF
            vector.append((seed / 0xFFFFFFFF) * 2 - 1)
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class LocalEmbedder:
    """Sentence Transformers-backed local embedder."""

    def __init__(self, model_name: str = LOCAL_EMBEDDING_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._backend_name = model_name
        self.model = SentenceTransformer(model_name)

    def __call__(self, text: str) -> list[float]:
        embedding = self.model.encode(text, normalize_embeddings=True)
        if hasattr(embedding, "tolist"):
            return embedding.tolist()
        return [float(value) for value in embedding]


class OpenAIEmbedder:
    """OpenAI embeddings API-backed embedder."""

    def __init__(self, model_name: str = OPENAI_EMBEDDING_MODEL) -> None:
        from openai import OpenAI

        self.model_name = model_name
        self._backend_name = model_name
        self.client = OpenAI()

    def __call__(self, text: str) -> list[float]:
        response = self.client.embeddings.create(model=self.model_name, input=text)
        return [float(value) for value in response.data[0].embedding]


class OpenRouterEmbedder:
    """OpenRouter embedding backend using its OpenAI-compatible API."""

    def __init__(
        self,
        model_name: str = OPENROUTER_EMBEDDING_MODEL,
        dimensions: int = OPENROUTER_EMBEDDING_DIMENSIONS,
        api_key: str | None = None,
    ) -> None:
        import os

        from openai import OpenAI

        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY must be set")
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")

        self.model_name = model_name
        self.dimensions = dimensions
        self._backend_name = f"OpenRouter {model_name} ({dimensions} dimensions)"
        headers = {"X-Title": os.getenv("OPENROUTER_APP_NAME", "K4 RAG Lab")}
        site_url = os.getenv("OPENROUTER_SITE_URL")
        if site_url:
            headers["HTTP-Referer"] = site_url
        self.client = OpenAI(
            api_key=key,
            base_url=OPENROUTER_BASE_URL,
            default_headers=headers,
        )

    def __call__(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=self.model_name,
            input=text,
            dimensions=self.dimensions,
            encoding_format="float",
        )
        vector = [float(value) for value in response.data[0].embedding]
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_document(self, text: str, title: str | None = None) -> list[float]:
        return self(text)

    def embed_query(self, text: str) -> list[float]:
        return self(text)


class GeminiEmbedder:
    """Google Gemini API-backed text embedder.

    ``google-genai`` reads ``GEMINI_API_KEY`` from the environment when an
    explicit API key is not provided. Vectors are normalized because the
    in-memory store ranks results with a dot product.
    """

    def __init__(
        self,
        model_name: str = GEMINI_EMBEDDING_MODEL,
        output_dimensionality: int = GEMINI_EMBEDDING_DIMENSIONS,
        api_key: str | None = None,
    ) -> None:
        from google import genai

        if not 128 <= output_dimensionality <= 3072:
            raise ValueError("output_dimensionality must be between 128 and 3072")

        self.model_name = model_name
        self.output_dimensionality = output_dimensionality
        self._backend_name = f"{model_name} ({output_dimensionality} dimensions)"
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def __call__(self, text: str) -> list[float]:
        return self._embed(text)

    def embed_document(self, text: str, title: str | None = None) -> list[float]:
        """Embed a retrievable document using Gemini Embedding 2 formatting."""
        prepared = f"title: {title or 'none'} | text: {text}"
        return self._embed(prepared)

    def embed_query(self, text: str) -> list[float]:
        """Embed a search query in the same asymmetric retrieval space."""
        return self._embed(f"task: search result | query: {text}")

    def _embed(self, text: str) -> list[float]:
        from google.genai import types

        response = self.client.models.embed_content(
            model=self.model_name,
            contents=text,
            config=types.EmbedContentConfig(
                output_dimensionality=self.output_dimensionality,
            ),
        )
        if not response.embeddings or response.embeddings[0].values is None:
            raise RuntimeError("Gemini API returned no embedding values")

        vector = [float(value) for value in response.embeddings[0].values]
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


_mock_embed = MockEmbedder()
