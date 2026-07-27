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

# httpx's 5s default timeout is too tight for this API, which we've observed
# take 2-3s per page; use a more generous timeout for both search and PDF downloads.
DEFAULT_TIMEOUT = httpx.Timeout(30.0)


class NTRSClient:
    """Thin async wrapper over the NTRS citations search endpoint."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await self._client.get(f"{BASE_URL}{path}", params=params)
            except httpx.TransportError:
                if attempt == _MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(2**attempt)
                continue
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
            "sort.field": "score",
            "sort.order": "desc",
        }
        data = await self._get("/citations/search", params)
        results: list[dict[str, Any]] = data.get("results", [])
        return results

    async def search(self, query: str, limit: int | None = None) -> list[dict[str, Any]]:
        """Up to `limit` PUBLIC, document-bearing records for one keyword, most
        relevant first. Fetches every matching record if `limit` is None."""
        max_records = (
            min(limit, MAX_RECORDS_PER_QUERY) if limit is not None else MAX_RECORDS_PER_QUERY
        )
        out: list[dict[str, Any]] = []
        offset = 0
        while offset < max_records:
            page = await self._search_page(query, offset)
            if not page:
                break
            out.extend(page)
            offset += PAGE_SIZE
        return out[:limit] if limit is not None else out


def _retry_after(resp: httpx.Response) -> float | None:
    value = resp.headers.get("Retry-After")
    return float(value) if value and value.isdigit() else None
