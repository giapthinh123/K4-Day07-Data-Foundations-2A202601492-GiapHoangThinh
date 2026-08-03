from __future__ import annotations

import os

from .embeddings import OPENROUTER_BASE_URL

OPENROUTER_CHAT_MODEL = "openai/gpt-4o-mini"


class OpenRouterLLM:
    """Callable chat-completion adapter for KnowledgeBaseAgent."""

    def __init__(
        self,
        model_name: str = OPENROUTER_CHAT_MODEL,
        api_key: str | None = None,
    ) -> None:
        from openai import OpenAI

        key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY must be set")

        self.model_name = model_name
        self._backend_name = f"OpenRouter {model_name}"
        headers = {"X-Title": os.getenv("OPENROUTER_APP_NAME", "K4 RAG Lab")}
        site_url = os.getenv("OPENROUTER_SITE_URL")
        if site_url:
            headers["HTTP-Referer"] = site_url
        self.client = OpenAI(
            api_key=key,
            base_url=OPENROUTER_BASE_URL,
            default_headers=headers,
        )

    def __call__(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("OpenRouter returned an empty chat response")
        return content
