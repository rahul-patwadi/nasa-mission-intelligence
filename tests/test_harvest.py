"""Tests for the mission harvest loop."""

from typing import Any
from unittest.mock import AsyncMock

from app.fetcher.harvest import MISSIONS, harvest_all


def _client_with_results(results_by_mission: dict[str, list[dict[str, Any]]]) -> AsyncMock:
    client = AsyncMock()
    client.search.side_effect = lambda mission: results_by_mission.get(mission, [])
    return client


async def test_harvest_all_dedups_records_across_missions() -> None:
    shared_record = {
        "id": "1",
        "title": "Shared report",
        "distribution": "PUBLIC",
        "exportControl": {"itar": "NO", "ear": "NO"},
        "downloadsAvailable": True,
        "downloads": [{"draft": False, "links": {"pdf": "/x.pdf"}}],
    }
    results_by_mission = {
        "Apollo": [shared_record],
        "Artemis": [shared_record],
        "ISS": [],
        "Mars": [],
        "Hubble": [],
        "Voyager": [],
    }
    client = _client_with_results(results_by_mission)

    records = await harvest_all(client=client)

    assert records == [shared_record]
    assert client.search.await_count == len(MISSIONS)


async def test_harvest_all_drops_records_failing_is_ingestable(monkeypatch: Any) -> None:
    keep = {"id": "1", "title": "Keep me"}
    drop = {"id": "2", "title": "Drop me"}
    results_by_mission = {
        "Apollo": [keep, drop],
        "Artemis": [],
        "ISS": [],
        "Mars": [],
        "Hubble": [],
        "Voyager": [],
    }
    client = _client_with_results(results_by_mission)

    monkeypatch.setattr("app.fetcher.harvest.is_ingestable", lambda record: record["id"] == "1")

    records = await harvest_all(client=client)

    assert records == [keep]
