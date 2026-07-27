"""Tests for the ChromaDB vector store wrapper."""

import uuid
from typing import Any

import chromadb
import pytest
from chromadb import Collection

from app.core.vectorstore import existing_record_ids, query, upsert_chunks


@pytest.fixture
def collection() -> Collection:
    # A unique name per test: chromadb's EphemeralClient shares collection
    # state across instances within the same process when names collide.
    client = chromadb.EphemeralClient()
    return client.get_or_create_collection(f"test_collection_{uuid.uuid4().hex}")


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


def test_existing_record_ids_empty_for_empty_collection(collection: Collection) -> None:
    assert existing_record_ids(collection=collection) == set()


def test_existing_record_ids_returns_distinct_record_ids(collection: Collection) -> None:
    chunk_a = _chunk("First chunk of record 1.", 1, "Apollo", 0, [1.0, 0.0])
    chunk_b = _chunk("Second chunk of record 1.", 1, "Apollo", 1, [1.0, 0.1])
    other_record = _chunk("Record 2.", 2, "Mars", 0, [0.0, 1.0])
    upsert_chunks([chunk_a, chunk_b, other_record], collection=collection)

    assert existing_record_ids(collection=collection) == {1, 2}
