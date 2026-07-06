"""Async client for the NASA NTRS (STI Repository) OpenAPI.

Public API, no auth. Docs: https://ntrs.nasa.gov/api/openapi/
Constraints (from the official OpenAPI terms of service):
  - 500 requests / 15 minutes
  - max 10,000 records returned per query
  - page size max 100
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

BASE_URL = "https://ntrs.nasa.gov/api"
PAGE_SIZE = 100  # API maximum
MAX_RECORDS_PER_QUERY = 10_000  # API hard cap
_MAX_RETRIES = 4


class NTRSClient:
    """Thin async wrapper over the NTRS citations search endpoint."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(_MAX_RETRIES):
            resp = await self._client.get(f"{BASE_URL}{path}", params=params)
            if resp.status_code == 429 or resp.status_code >= 500:
                await asyncio.sleep(_retry_after(resp) or 2**attempt)
                continue
            resp.raise_for_status()
            result: dict[str, Any] = resp.json()
            return result
        resp.raise_for_status()
        result = resp.json()
        return result

    async def _search_page(self, query: str, offset: int) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "q": query,
            "disseminated": "DOCUMENT_AND_METADATA",  # only records with a real doc
            "distribution": "PUBLIC",
            "page.size": PAGE_SIZE,
            "from": offset,
            "sort.field": "id",
            "sort.order": "asc",
        }
        data = await self._get("/citations/search", params)
        results: list[dict[str, Any]] = data.get("results", [])
        return results

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Every PUBLIC, document-bearing record for one mission keyword."""
        out: list[dict[str, Any]] = []
        offset = 0
        while offset < MAX_RECORDS_PER_QUERY:
            page = await self._search_page(query, offset)
            if not page:
                break
            out.extend(page)
            offset += PAGE_SIZE
        return out


def _retry_after(resp: httpx.Response) -> float | None:
    value = resp.headers.get("Retry-After")
    return float(value) if value and value.isdigit() else None
