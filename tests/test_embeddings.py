"""Tests for embedding generation, rate limiting, and 429 retry handling."""

import math
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai import errors

from app.core.embeddings import _normalize, _RateLimiter, _retry_delay_seconds, embed_chunks


def _embed_response(vectors: list[list[float]]) -> MagicMock:
    response = MagicMock()
    response.embeddings = [MagicMock(values=v) for v in vectors]
    return response


def _client_error(retry_delay: str | None) -> errors.ClientError:
    details: dict[str, Any] = {
        "error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "details": []}
    }
    if retry_delay is not None:
        details["error"]["details"] = [
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay}
        ]
    return errors.ClientError(429, details, None)


async def test_embed_chunks_adds_embedding_key(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_client = MagicMock()
    mock_client.aio.models.embed_content = AsyncMock(
        return_value=_embed_response([[0.1, 0.2], [0.3, 0.4]])
    )
    monkeypatch.setattr("app.core.embeddings.genai.Client", lambda **kwargs: mock_client)

    chunks = [{"text": "a"}, {"text": "b"}]
    result = await embed_chunks(chunks)

    assert result[0]["embedding"] == pytest.approx(_normalize([0.1, 0.2]))
    assert result[1]["embedding"] == pytest.approx(_normalize([0.3, 0.4]))
    assert math.isclose(math.sqrt(sum(x * x for x in result[0]["embedding"])), 1.0)


async def test_embed_chunks_retries_after_429_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MagicMock()
    mock_client.aio.models.embed_content = AsyncMock(
        side_effect=[_client_error("0.01s"), _embed_response([[0.1, 0.2]])]
    )
    monkeypatch.setattr("app.core.embeddings.genai.Client", lambda **kwargs: mock_client)

    result = await embed_chunks([{"text": "a"}])

    assert result[0]["embedding"] == pytest.approx(_normalize([0.1, 0.2]))
    assert mock_client.aio.models.embed_content.await_count == 2


def test_normalize_scales_to_unit_length() -> None:
    result = _normalize([3.0, 4.0])

    assert result == pytest.approx([0.6, 0.8])


def test_normalize_leaves_zero_vector_unchanged() -> None:
    assert _normalize([0.0, 0.0]) == [0.0, 0.0]


def test_retry_delay_seconds_parses_retry_info() -> None:
    exc = _client_error("17s")

    assert _retry_delay_seconds(exc) == 17.0


def test_retry_delay_seconds_none_when_missing() -> None:
    exc = _client_error(None)

    assert _retry_delay_seconds(exc) is None


async def test_rate_limiter_delays_once_max_calls_reached() -> None:
    limiter = _RateLimiter(max_calls=2, period=0.05)

    await limiter.acquire()
    await limiter.acquire()
    # A third acquisition within the window must wait for the first to expire
    # rather than raising or silently exceeding the cap.
    await limiter.acquire()

    assert len(limiter._call_times) <= 2
