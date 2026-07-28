"""Wrapper around ChromaDB for storing and querying chunk embeddings."""

from __future__ import annotations

from typing import Any, cast

import chromadb
from chromadb import Collection
from chromadb.api import ClientAPI

PERSIST_DIRECTORY = "./data/chroma"
COLLECTION_NAME = "nasa_missions"

# collection.get() with no limit tries to bind every row's columns as SQL
# variables in one query, which blows past SQLite's bound-variable limit on
# a large collection ("too many SQL variables"). Page it.
_GET_PAGE_SIZE = 500

_client: ClientAPI | None = None


def _get_collection() -> Collection:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=PERSIST_DIRECTORY)
    return _client.get_or_create_collection(COLLECTION_NAME)


def existing_record_ids(collection: Collection | None = None) -> set[Any]:
    """The distinct record_ids that already have chunks stored in the vector store."""
    collection = collection if collection is not None else _get_collection()
    record_ids: set[Any] = set()
    offset = 0
    while True:
        page = collection.get(include=cast(Any, ["metadatas"]), limit=_GET_PAGE_SIZE, offset=offset)
        metadatas = page["metadatas"] or []
        if not metadatas:
            break
        record_ids.update(metadata["record_id"] for metadata in metadatas)
        offset += _GET_PAGE_SIZE
    return record_ids


def upsert_chunks(chunks: list[dict[str, Any]], collection: Collection | None = None) -> None:
    """Store each chunk's text, embedding, and metadata (record_id, mission, chunk_index)."""
    collection = collection if collection is not None else _get_collection()
    collection.upsert(
        ids=[f"{chunk['record_id']}-{chunk['chunk_index']}" for chunk in chunks],
        embeddings=[chunk["embedding"] for chunk in chunks],
        documents=[chunk["text"] for chunk in chunks],
        metadatas=[
            {
                "record_id": chunk["record_id"],
                "mission": chunk["mission"],
                "chunk_index": chunk["chunk_index"],
            }
            for chunk in chunks
        ],
    )


def query(
    query_embedding: list[float],
    mission_filter: str | None = None,
    top_k: int = 5,
    collection: Collection | None = None,
) -> list[dict[str, Any]]:
    """Return the top_k chunks nearest to query_embedding, optionally filtered by mission."""
    collection = collection if collection is not None else _get_collection()
    where = {"mission": mission_filter} if mission_filter else None
    results = collection.query(
        query_embeddings=cast(Any, [query_embedding]),
        n_results=top_k,
        where=cast(Any, where),
    )

    ids = results["ids"][0] if results["ids"] else []
    documents = (results["documents"] or [[]])[0]
    metadatas = (results["metadatas"] or [[]])[0]
    distances = (results["distances"] or [[]])[0]

    return [
        {"id": chunk_id, "text": document, "distance": distance, **metadata}
        for chunk_id, document, metadata, distance in zip(
            ids, documents, metadatas, distances, strict=True
        )
    ]
