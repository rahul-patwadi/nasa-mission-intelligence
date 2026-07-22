"""Tests for the /query and /missions API routes."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.fetcher.harvest import MISSIONS
from app.main import app

client = TestClient(app)


@pytest.fixture
def mock_answer_query(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock(
        return_value={
            "answer": "Apollo 11 landed in 1969.",
            "sources": [{"record_id": 1, "mission": "Apollo", "chunk_index": 0}],
        }
    )
    monkeypatch.setattr("app.api.routes.query.answer_query", mock)
    return mock


def test_query_returns_200_with_expected_shape(mock_answer_query: AsyncMock) -> None:
    response = client.post(
        "/query", json={"question": "When did Apollo 11 land?", "mission_filter": "Apollo"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "answer": "Apollo 11 landed in 1969.",
        "sources": [{"record_id": 1, "mission": "Apollo", "chunk_index": 0}],
    }
    mock_answer_query.assert_awaited_once_with("When did Apollo 11 land?", mission_filter="Apollo")


def test_query_missing_question_returns_422(mock_answer_query: AsyncMock) -> None:
    response = client.post("/query", json={"mission_filter": "Apollo"})

    assert response.status_code == 422
    mock_answer_query.assert_not_awaited()


def test_query_mission_filter_defaults_to_none(mock_answer_query: AsyncMock) -> None:
    response = client.post("/query", json={"question": "What is Voyager?"})

    assert response.status_code == 200
    mock_answer_query.assert_awaited_once_with("What is Voyager?", mission_filter=None)


def test_missions_returns_full_list() -> None:
    response = client.get("/missions")

    assert response.status_code == 200
    assert response.json() == {"missions": MISSIONS}
