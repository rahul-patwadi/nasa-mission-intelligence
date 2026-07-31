"""Generate embeddings for text chunks via Google's Gemini embedding API."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections import deque
from typing import Any, cast

from google import genai
from google.genai import errors, types

from app.core.config import settings

EMBEDDING_MODEL = "gemini-embedding-001"
# ADR 0006: truncate via MRL to shrink data/chroma's HNSW index 4x. Google only
# guarantees pre-normalized (unit-length) output at the model's native 3072
# dims; any other output_dimensionality returns a raw truncated prefix with
# per-text-varying magnitude, so it must be re-normalized below to keep the
# vector store's L2 distance equivalent to cosine similarity.
EMBEDDING_DIMENSIONALITY = 768
BATCH_SIZE = 100  # API max per call
_MAX_RETRIES = 5

# genai.Client has no timeout by default, so a stalled connection can hang
# indefinitely (observed: one call blocked for ~4 hours after a mid-request
# "Connection reset by peer"). Bound every request explicitly.
_REQUEST_TIMEOUT_MS = 60_000

# The free-tier embed_content quota is 100 requests/minute, and we've observed
# 429s starting well before that (likely coarser accounting than a clean
# sliding window). Stay well under it proactively instead of only reacting
# to 429s after the fact.
_RATE_LIMIT_MAX_CALLS = 50
_RATE_LIMIT_PERIOD_SECONDS = 60.0

logger = logging.getLogger(__name__)


class _RateLimiter:
    """Sliding-window limiter: at most `max_calls` acquisitions per `period` seconds."""

    def __init__(self, max_calls: int, period: float) -> None:
        self._max_calls = max_calls
        self._period = period
        self._call_times: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                while self._call_times and now - self._call_times[0] >= self._period:
                    self._call_times.popleft()
                if len(self._call_times) < self._max_calls:
                    self._call_times.append(now)
                    return
                await asyncio.sleep(self._call_times[0] + self._period - now)


_rate_limiter = _RateLimiter(_RATE_LIMIT_MAX_CALLS, _RATE_LIMIT_PERIOD_SECONDS)


async def embed_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add an `embedding` key to each chunk dict, batching requests to the API."""
    client = genai.Client(
        api_key=settings.google_api_key,
        http_options=types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS),
    )

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        embeddings = await _embed_batch(client, [chunk["text"] for chunk in batch])
        for chunk, embedding in zip(batch, embeddings, strict=True):
            chunk["embedding"] = embedding

    return chunks


async def _embed_batch(client: genai.Client, texts: list[str]) -> list[list[float]]:
    config = types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONALITY)
    for attempt in range(_MAX_RETRIES):
        await _rate_limiter.acquire()
        try:
            response = await client.aio.models.embed_content(
                model=EMBEDDING_MODEL, contents=cast(Any, texts), config=config
            )
        except errors.ClientError as exc:
            if exc.code == 429 and attempt < _MAX_RETRIES - 1:
                delay = _retry_delay_seconds(exc) or 2**attempt
                logger.warning("Embedding rate limited, retrying in %.1fs", delay)
                await asyncio.sleep(delay)
                continue
            raise
        return [_normalize(list(embedding.values or [])) for embedding in response.embeddings or []]

    raise RuntimeError("Exceeded retry budget for embedding batch")


def _normalize(vector: list[float]) -> list[float]:
    """L2-normalize a truncated embedding back to unit length (see ADR 0006)."""
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return vector
    return [x / norm for x in vector]


def _retry_delay_seconds(exc: errors.ClientError) -> float | None:
    """Parse the API's suggested wait (e.g. '17s') out of a 429's error details."""
    details = exc.details if isinstance(exc.details, dict) else {}
    for item in details.get("error", {}).get("details", []):
        value = item.get("retryDelay")
        if isinstance(value, str) and value.endswith("s"):
            try:
                return float(value[:-1])
            except ValueError:
                return None
    return None
