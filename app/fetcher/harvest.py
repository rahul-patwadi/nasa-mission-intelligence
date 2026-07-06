"""Harvest NTRS records across all configured missions."""

from __future__ import annotations

from typing import Any

import httpx

from app.fetcher.client import NTRSClient
from app.fetcher.filter import is_ingestable

MISSIONS = ["Apollo", "Artemis", "ISS", "Mars", "Hubble", "Voyager"]


async def harvest_all(client: NTRSClient | None = None) -> list[dict[str, Any]]:
    """Search every mission, dedup by record id, and filter to ingestable records."""
    if client is not None:
        return await _harvest(client)
    async with httpx.AsyncClient() as http_client:
        return await _harvest(NTRSClient(http_client))


async def _harvest(client: NTRSClient) -> list[dict[str, Any]]:
    seen: dict[Any, dict[str, Any]] = {}
    for mission in MISSIONS:
        for record in await client.search(mission):
            seen.setdefault(record["id"], record)

    return [record for record in seen.values() if is_ingestable(record)]
