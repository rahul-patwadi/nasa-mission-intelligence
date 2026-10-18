"""Tests for cross-encoder re-ranking (loads the real model)."""

from typing import Any

from app.core.reranker import rerank


def _chunks() -> list[dict[str, Any]]:
    return [
        {"text": "The cafeteria menu includes soup, salad, and sandwiches on Tuesdays."},
        {"text": "Voyager 1 launched on September 5, 1977 to study the outer planets."},
        {"text": "Quarterly budget reports must be filed with the finance office."},
        {"text": "Hubble's primary mirror is 2.4 meters in diameter."},
    ]


def test_rerank_puts_relevant_chunk_first() -> None:
    result = rerank("When did Voyager 1 launch?", _chunks(), top_n=3)

    assert result[0]["text"].startswith("Voyager 1 launched")
    assert len(result) == 3


def test_rerank_adds_scores_sorted_descending_without_mutating_input() -> None:
    chunks = _chunks()

    result = rerank("When did Voyager 1 launch?", chunks)

    scores = [chunk["rerank_score"] for chunk in result]
    assert scores == sorted(scores, reverse=True)
    assert all("rerank_score" not in chunk for chunk in chunks)


def test_rerank_empty_input_returns_empty() -> None:
    assert rerank("anything", []) == []
