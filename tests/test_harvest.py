"""Tests for the mission harvest loop."""

from typing import Any
from unittest.mock import AsyncMock

from app.fetcher.harvest import MISSIONS, RECORDS_PER_MISSION, harvest_all


def _client_with_results(results_by_mission: dict[str, list[dict[str, Any]]]) -> AsyncMock:
    client = AsyncMock()
    client.search.side_effect = lambda mission, limit=None: results_by_mission.get(mission, [])
    return client


def _ingestable_record(record_id: str, title: str) -> dict[str, Any]:
    return {
        "id": record_id,
        "title": title,
        "distribution": "PUBLIC",
        "exportControl": {"itar": "NO", "ear": "NO"},
        "downloadsAvailable": True,
        "downloads": [{"draft": False, "links": {"pdf": "/x.pdf"}}],
    }


async def test_harvest_all_dedups_records_across_missions() -> None:
    apollo_copy = _ingestable_record("1", "Shared report")
    artemis_copy = _ingestable_record("1", "Shared report")
    results_by_mission = {
        "Apollo": [apollo_copy],
        "Artemis": [artemis_copy],
        "ISS": [],
        "Mars": [],
        "Hubble": [],
        "Voyager": [],
    }
    client = _client_with_results(results_by_mission)

    records = await harvest_all(client=client)

    assert len(records) == 1
    assert records[0]["id"] == "1"
    assert client.search.await_count == len(MISSIONS)


async def test_harvest_all_tags_record_with_first_matching_mission() -> None:
    apollo_copy = _ingestable_record("1", "Shared report")
    artemis_copy = _ingestable_record("1", "Shared report")
    results_by_mission = {
        "Apollo": [apollo_copy],
        "Artemis": [artemis_copy],
        "ISS": [],
        "Mars": [],
        "Hubble": [],
        "Voyager": [],
    }
    client = _client_with_results(results_by_mission)

    records = await harvest_all(client=client)

    assert records[0]["mission"] == "Apollo"


async def test_harvest_all_caps_each_mission_search_at_records_per_mission() -> None:
    client = _client_with_results({})

    await harvest_all(client=client)

    for call in client.search.await_args_list:
        assert call.kwargs["limit"] == RECORDS_PER_MISSION


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
