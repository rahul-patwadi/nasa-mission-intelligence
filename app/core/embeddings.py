"""Generate embeddings for text chunks via Google's Gemini embedding API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, cast

from google import genai
from google.genai import errors

from app.core.config import settings

EMBEDDING_MODEL = "text-embedding-004"
BATCH_SIZE = 100  # API max per call
_MAX_RETRIES = 5

logger = logging.getLogger(__name__)


async def embed_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add an `embedding` key to each chunk dict, batching requests to the API."""
    client = genai.Client(api_key=settings.google_api_key)

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        embeddings = await _embed_batch(client, [chunk["text"] for chunk in batch])
        for chunk, embedding in zip(batch, embeddings, strict=True):
            chunk["embedding"] = embedding

    return chunks


async def _embed_batch(client: genai.Client, texts: list[str]) -> list[list[float]]:
    for attempt in range(_MAX_RETRIES):
        try:
            response = await client.aio.models.embed_content(
                model=EMBEDDING_MODEL, contents=cast(Any, texts)
            )
        except errors.ClientError as exc:
            if exc.code == 429 and attempt < _MAX_RETRIES - 1:
                delay = 2**attempt
                logger.warning("Embedding rate limited, retrying in %ss", delay)
                await asyncio.sleep(delay)
                continue
            raise
        return [list(embedding.values or []) for embedding in response.embeddings or []]

    raise RuntimeError("Exceeded retry budget for embedding batch")
