"""Tests for the RAG question-answering chain."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.rag_chain import NO_INFO_ANSWER, answer_query


async def _fake_embed_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**chunk, "embedding": [0.1, 0.2]} for chunk in chunks]


def _mock_genai_client(answer_text: str) -> MagicMock:
    response = MagicMock()
    response.text = answer_text
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=response)
    return client


@pytest.fixture(autouse=True)
def _patch_embed_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.core.rag_chain.embed_chunks", _fake_embed_chunks)


async def test_answer_query_returns_answer_and_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    chunks = [
        {
            "text": "Apollo 11 landed in 1969.",
            "record_id": 1,
            "mission": "Apollo",
            "chunk_index": 0,
        },
        {
            "text": "Neil Armstrong was the mission commander.",
            "record_id": 2,
            "mission": "Apollo",
            "chunk_index": 3,
        },
    ]
    monkeypatch.setattr("app.core.rag_chain.vectorstore_query", lambda *a, **k: chunks)
    monkeypatch.setattr(
        "app.core.rag_chain.genai.Client",
        lambda **kwargs: _mock_genai_client("Apollo 11 landed in 1969 [source 1]."),
    )

    result = await answer_query("When did Apollo 11 land?")

    assert result["answer"] == "Apollo 11 landed in 1969 [source 1]."
    assert result["sources"] == [
        {"record_id": 1, "mission": "Apollo", "chunk_index": 0},
        {"record_id": 2, "mission": "Apollo", "chunk_index": 3},
    ]


async def test_answer_query_empty_retrieval_triggers_dont_know(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.core.rag_chain.vectorstore_query", lambda *a, **k: [])
    called = False

    def _fail_if_called(**kwargs: Any) -> MagicMock:
        nonlocal called
        called = True
        return _mock_genai_client("should not be used")

    monkeypatch.setattr("app.core.rag_chain.genai.Client", _fail_if_called)

    result = await answer_query("What is the airspeed velocity of an unladen swallow?")

    assert result == {"answer": NO_INFO_ANSWER, "sources": []}
    assert called is False
