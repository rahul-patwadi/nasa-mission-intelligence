"""Tests for text chunking."""

from app.fetcher.chunker import chunk_text


def test_chunk_text_splits_long_text_into_multiple_chunks() -> None:
    text = "NASA mission report. " * 200
    chunks = chunk_text(text, record_id=1, mission="Apollo")

    assert len(chunks) > 1


def test_chunk_text_chunks_have_all_required_keys() -> None:
    text = "NASA mission report. " * 200
    chunks = chunk_text(text, record_id=1, mission="Apollo")

    for chunk in chunks:
        assert chunk.keys() == {"text", "record_id", "mission", "chunk_index"}
        assert chunk["record_id"] == 1
        assert chunk["mission"] == "Apollo"


def test_chunk_text_returns_empty_list_for_empty_input() -> None:
    assert chunk_text("", record_id=1, mission="Apollo") == []


def test_chunk_text_returns_empty_list_for_whitespace_only_input() -> None:
    assert chunk_text("   \n\t  ", record_id=1, mission="Apollo") == []


def test_chunk_text_chunk_index_is_sequential_from_zero() -> None:
    text = "NASA mission report. " * 200
    chunks = chunk_text(text, record_id=1, mission="Apollo")

    assert [chunk["chunk_index"] for chunk in chunks] == list(range(len(chunks)))
