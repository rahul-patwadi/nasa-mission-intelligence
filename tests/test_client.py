"""Tests for the NTRS search client."""

import httpx

from app.fetcher.client import PAGE_SIZE, NTRSClient

TOTAL_AVAILABLE_RECORDS = 500


def _record(record_id: int) -> dict[str, object]:
    return {"id": record_id}


def _client_with_available_records(total: int) -> tuple[NTRSClient, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        offset = int(request.url.params["from"])
        page = [_record(i) for i in range(offset, min(offset + PAGE_SIZE, total))]
        return httpx.Response(200, json={"results": page})

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return NTRSClient(http_client), requests


async def test_search_page_sorts_by_relevance_descending() -> None:
    client, requests = _client_with_available_records(TOTAL_AVAILABLE_RECORDS)

    await client.search("Apollo", limit=1)

    assert requests[0].url.params["sort.field"] == "score"
    assert requests[0].url.params["sort.order"] == "desc"


async def test_search_stops_paginating_once_limit_reached() -> None:
    client, requests = _client_with_available_records(TOTAL_AVAILABLE_RECORDS)

    results = await client.search("Apollo", limit=300)

    assert len(results) == 300
    assert len(requests) == 300 // PAGE_SIZE


async def test_search_without_limit_fetches_everything_available() -> None:
    client, requests = _client_with_available_records(150)

    results = await client.search("Apollo")

    assert len(results) == 150
    # full page (0-99), partial page (100-149), then an empty page ends the loop
    assert len(requests) == 3
