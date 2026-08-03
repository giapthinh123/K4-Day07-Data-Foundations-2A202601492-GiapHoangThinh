from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []

        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", text)
            if sentence.strip()
        ]
        limit = self.max_sentences_per_chunk
        return [
            " ".join(sentences[index : index + limit])
            for index in range(0, len(sentences), limit)
        ]


class HeadingBasedChunker:
    """Split Markdown at ATX headings while preserving heading context.

    Each section becomes a separate chunk. Nested sections include their
    ancestor headings, which gives an embedding enough context to distinguish
    similarly named clauses in different parts of a policy. Sections larger
    than ``chunk_size`` are split further and the heading path is repeated in
    every resulting chunk.

    Markdown headings inside fenced code blocks are treated as normal text.
    """

    HEADING_PATTERN = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
    FENCE_PATTERN = re.compile(r"^\s*(`{3,}|~{3,})")
    SPLIT_SEPARATORS = ("\n\n", "\n", ". ", " ")

    def __init__(self, chunk_size: int = 1000) -> None:
        if chunk_size < 50:
            raise ValueError("chunk_size must be at least 50 characters")
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        sections: list[tuple[list[tuple[int, str]], str]] = []
        heading_path: list[tuple[int, str]] = []
        current_lines: list[str] = []
        active_fence: str | None = None

        def flush_section() -> None:
            body = "\n".join(current_lines).strip()
            if body:
                sections.append((list(heading_path), body))

        for line in text.splitlines():
            fence_match = self.FENCE_PATTERN.match(line)
            if fence_match:
                marker = fence_match.group(1)[0]
                if active_fence is None:
                    active_fence = marker
                elif active_fence == marker:
                    active_fence = None
                current_lines.append(line)
                continue

            heading_match = None if active_fence else self.HEADING_PATTERN.match(line)
            if not heading_match:
                current_lines.append(line)
                continue

            flush_section()
            current_lines = []
            level = len(heading_match.group(1))
            # Markdown permits a closing hash sequence only when separated by
            # whitespace; this preserves legitimate titles such as "C#".
            title = re.sub(r"[ \t]+#+[ \t]*$", "", heading_match.group(2)).strip()
            heading_path = [heading for heading in heading_path if heading[0] < level]
            heading_path.append((level, title))

        flush_section()

        # A document containing headings but no body should still be indexable.
        if not sections and heading_path:
            sections.append((heading_path, ""))

        chunks: list[str] = []
        for path, body in sections:
            chunks.extend(self._build_section_chunks(path, body))
        return chunks

    def _build_section_chunks(self, path: list[tuple[int, str]], body: str) -> list[str]:
        header = self._fit_header(path)
        separator = "\n\n" if header and body else ""
        complete_section = f"{header}{separator}{body}".strip()
        if len(complete_section) <= self.chunk_size:
            return [complete_section] if complete_section else []

        body_limit = self.chunk_size - len(header) - len(separator)
        if body_limit < 1:
            return [complete_section[: self.chunk_size].rstrip()]

        pieces = self._split_long_text(body, body_limit)
        return [f"{header}{separator}{piece}".strip() for piece in pieces if piece]

    def _fit_header(self, path: list[tuple[int, str]]) -> str:
        """Fit the most specific heading path inside the configured limit."""
        headings = [f"{'#' * level} {title}" for level, title in path]
        header_limit = self.chunk_size - 2
        while len("\n".join(headings)) > header_limit and len(headings) > 1:
            headings.pop(0)
        header = "\n".join(headings)
        return header if len(header) <= header_limit else header[:header_limit].rstrip()

    def _split_long_text(self, text: str, limit: int) -> list[str]:
        """Split oversized section bodies at the strongest nearby boundary."""
        remaining = text.strip()
        pieces: list[str] = []
        while len(remaining) > limit:
            window = remaining[:limit]
            cut = -1
            separator_length = 0
            for separator in self.SPLIT_SEPARATORS:
                position = window.rfind(separator)
                if position >= limit // 2:
                    cut = position
                    separator_length = len(separator)
                    break
            if cut < 0:
                cut = limit
            else:
                cut += separator_length

            piece = remaining[:cut].strip()
            if piece:
                pieces.append(piece)
            remaining = remaining[cut:].lstrip()

        if remaining:
            pieces.append(remaining)
        return pieces


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return [
            piece.strip()
            for piece in self._split(text, self.separators)
            if piece.strip()
        ]

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if len(current_text) <= self.chunk_size:
            return [current_text]

        if not remaining_separators or remaining_separators[0] == "":
            return [
                current_text[index : index + self.chunk_size]
                for index in range(0, len(current_text), self.chunk_size)
            ]

        separator = remaining_separators[0]
        lower_priority_separators = remaining_separators[1:]
        if separator not in current_text:
            return self._split(current_text, lower_priority_separators)

        raw_parts = current_text.split(separator)
        # Attach separators to the preceding part so punctuation such as ". "
        # remains at the end of its sentence instead of the next chunk.
        parts = [
            part + (separator if index < len(raw_parts) - 1 else "")
            for index, part in enumerate(raw_parts)
        ]

        chunks: list[str] = []
        current_chunk = ""
        for part in parts:
            if not part:
                continue

            candidate = current_chunk + part
            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
                continue

            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            if len(part) > self.chunk_size:
                chunks.extend(self._split(part, lower_priority_separators))
            else:
                current_chunk = part

        if current_chunk:
            chunks.append(current_chunk)
        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    norm_a = math.sqrt(_dot(vec_a, vec_a))
    norm_b = math.sqrt(_dot(vec_b, vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")

        fixed_overlap = min(50, chunk_size - 1)
        strategies = {
            "fixed_size": FixedSizeChunker(
                chunk_size=chunk_size,
                overlap=fixed_overlap,
            ).chunk(text),
            "by_sentences": SentenceChunker().chunk(text),
            "recursive": RecursiveChunker(chunk_size=chunk_size).chunk(text),
        }

        comparison: dict = {}
        for name, chunks in strategies.items():
            count = len(chunks)
            comparison[name] = {
                "count": count,
                "avg_length": (
                    sum(len(chunk) for chunk in chunks) / count if count else 0.0
                ),
                "chunks": chunks,
            }
        return comparison
