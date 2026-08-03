from src import HeadingBasedChunker


def test_splits_markdown_sections_and_keeps_headings():
    text = "# Đổi trả\n\nNội dung chung.\n\n## Thời hạn\n\nKhách hàng có 7 ngày."

    chunks = HeadingBasedChunker().chunk(text)

    assert chunks == [
        "# Đổi trả\n\nNội dung chung.",
        "# Đổi trả\n## Thời hạn\n\nKhách hàng có 7 ngày.",
    ]


def test_keeps_preamble_as_its_own_chunk():
    chunks = HeadingBasedChunker().chunk("Lời mở đầu.\n\n# Chính sách\n\nNội dung.")

    assert chunks == ["Lời mở đầu.", "# Chính sách\n\nNội dung."]


def test_repeats_heading_context_when_section_is_too_long():
    text = "# Chính sách\n\n" + ("Quy định áp dụng cho khách hàng. " * 20)

    chunks = HeadingBasedChunker(chunk_size=120).chunk(text)

    assert len(chunks) > 1
    assert all(chunk.startswith("# Chính sách\n\n") for chunk in chunks)
    assert all(len(chunk) <= 120 for chunk in chunks)


def test_ignores_heading_syntax_inside_fenced_code():
    text = "# Ví dụ\n\n```md\n# Không phải heading\n```\n\nKết thúc."

    chunks = HeadingBasedChunker().chunk(text)

    assert len(chunks) == 1
    assert "# Không phải heading" in chunks[0]


def test_empty_text_returns_empty_list():
    assert HeadingBasedChunker().chunk("  \n") == []


def test_preserves_hash_inside_heading_title():
    chunks = HeadingBasedChunker().chunk("# Điều kiện cho C#\n\nNội dung.")

    assert chunks == ["# Điều kiện cho C#\n\nNội dung."]
