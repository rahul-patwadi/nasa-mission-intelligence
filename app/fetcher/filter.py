"""Record-level filtering for NTRS search results."""

from __future__ import annotations

from typing import Any

NTRS_BASE_URL = "https://ntrs.nasa.gov"


def pdf_url(record: dict[str, Any]) -> str | None:
    """The absolute PDF download URL for a record, or None if it has no usable PDF."""
    if not record.get("downloadsAvailable"):
        return None
    for download in record.get("downloads", []):
        if download.get("draft"):
            continue
        link = download.get("links", {}).get("pdf")
        if link:
            return f"{NTRS_BASE_URL}{link}"
    return None


def is_ingestable(record: dict[str, Any]) -> bool:
    """Whether a record has a real, non-draft PDF we can download and ingest."""
    if record.get("distribution") != "PUBLIC":
        return False
    if record.get("exportControl", {}).get("itar") != "NO":
        return False
    if record.get("exportControl", {}).get("ear") != "NO":
        return False
    return pdf_url(record) is not None
