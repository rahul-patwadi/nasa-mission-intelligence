"""Split extracted document text into retrieval-sized chunks."""

from __future__ import annotations

from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

_splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)


def chunk_text(text: str, record_id: int, mission: str) -> list[dict[str, Any]]:
    """Split text into overlapping chunks, tagged with their source record."""
    if not text.strip():
        return []

    return [
        {
            "text": chunk,
            "record_id": record_id,
            "mission": mission,
            "chunk_index": index,
        }
        for index, chunk in enumerate(_splitter.split_text(text))
    ]
