"""Tests for splitting large texts into chunks (map-reduce)."""

import pytest

from backend.core.chunking import count_words, split_text


def test_short_text_is_single_chunk():
    assert split_text("krótki tekst", 1000) == ["krótki tekst"]


def test_empty_text_returns_no_chunks():
    assert split_text("   ", 1000) == []


def test_zero_size_rejected():
    with pytest.raises(ValueError, match="chunk_size"):
        split_text("tekst", 0)


def test_long_text_is_split_into_valid_chunks():
    text = ("Zdanie numer jeden. " * 50 + "\n\n") * 10  # ~6000 chars
    chunks = split_text(text, size=1000, overlap=100)

    assert len(chunks) > 1
    assert all(0 < len(c) <= 1000 for c in chunks)
    # every chunk is "clean" (no extra whitespace at the edges)
    assert all(c == c.strip() for c in chunks)


def test_overlap_is_respected():
    text = "abcdefghij" * 300  # 3000 chars without natural separators
    chunks = split_text(text, size=500, overlap=100)

    for prev, nxt in zip(chunks, chunks[1:], strict=False):
        # the start of the next chunk should overlap with the end of the previous one
        assert prev[-50:] in nxt or prev[-20:] in nxt


def test_all_content_is_preserved():
    text = "".join(f"slowo{i} " for i in range(2000))
    chunks = split_text(text, size=700, overlap=50)
    joined = "".join(chunks)
    # chunks are stripped, but every word must survive
    for word in ("slowo0", "slowo500", "slowo1999"):
        assert word in joined


def test_prefers_breaking_at_paragraph():
    part_a = "A" * 600
    part_b = "B" * 400
    text = f"{part_a}\n\n{part_b}"
    chunks = split_text(text, size=700, overlap=0)

    # the first chunk ends at the paragraph boundary (700 > 600, so the
    # cut happens at \n\n, not in the middle of the A run)
    assert chunks[0] == part_a
    assert chunks[1] == part_b


def test_large_overlap_is_clamped_to_half_size():
    text = "x" * 5000
    chunks = split_text(text, size=100, overlap=10_000)
    assert len(chunks) > 1
    assert all(len(c) <= 100 for c in chunks)


def test_count_words():
    assert count_words(" Ala   ma \n kota ") == 3
    assert count_words("") == 0
