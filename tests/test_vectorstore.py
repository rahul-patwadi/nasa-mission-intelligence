"""Tests for the ChromaDB vector store wrapper."""

from typing import Any

import chromadb
import pytest
from chromadb import Collection

from app.core.vectorstore import query, upsert_chunks


@pytest.fixture
def collection() -> Collection:
    client = chromadb.EphemeralClient()
    return client.get_or_create_collection("test_collection")


def _chunk(
    text: str, record_id: int, mission: str, chunk_index: int, embedding: list[float]
) -> dict[str, Any]:
    return {
        "text": text,
        "record_id": record_id,
        "mission": mission,
        "chunk_index": chunk_index,
        "embedding": embedding,
    }


def test_upsert_then_query_returns_the_right_chunk(collection: Collection) -> None:
    chunk = _chunk("Apollo 11 landed on the Moon.", 1, "Apollo", 0, [1.0, 0.0])
    other = _chunk("Voyager left the solar system.", 2, "Voyager", 0, [0.0, 1.0])
    upsert_chunks([chunk, other], collection=collection)

    results = query([1.0, 0.0], top_k=1, collection=collection)

    assert len(results) == 1
    assert results[0]["text"] == "Apollo 11 landed on the Moon."
    assert results[0]["record_id"] == 1
    assert results[0]["mission"] == "Apollo"
    assert results[0]["chunk_index"] == 0


def test_query_mission_filter_excludes_other_missions(collection: Collection) -> None:
    apollo_chunk = _chunk("Apollo 11 landed on the Moon.", 1, "Apollo", 0, [1.0, 0.0])
    mars_chunk = _chunk("Mars rover took samples.", 2, "Mars", 0, [0.9, 0.1])
    upsert_chunks([apollo_chunk, mars_chunk], collection=collection)

    results = query([1.0, 0.0], mission_filter="Mars", top_k=5, collection=collection)

    assert len(results) == 1
    assert results[0]["mission"] == "Mars"
