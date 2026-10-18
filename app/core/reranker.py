"""Cross-encoder re-ranking of retrieved chunks (ADR 0007)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from sentence_transformers import CrossEncoder

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=1)
def _get_model() -> CrossEncoder:
    """Load the cross-encoder on first use and reuse it for the process lifetime."""
    model: CrossEncoder = CrossEncoder(RERANKER_MODEL)
    return model


def rerank(question: str, chunks: list[dict[str, Any]], top_n: int = 5) -> list[dict[str, Any]]:
    """Score each (question, chunk text) pair and return the top_n chunks, best first.

    Each returned chunk is a copy of the input with a `rerank_score` added.
    """
    if not chunks:
        return []

    scores = _get_model().predict([(question, chunk["text"]) for chunk in chunks])
    scored = [
        {**chunk, "rerank_score": float(score)} for chunk, score in zip(chunks, scores, strict=True)
    ]
    scored.sort(key=lambda chunk: chunk["rerank_score"], reverse=True)
    return scored[:top_n]
