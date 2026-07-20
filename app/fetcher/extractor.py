"""PDF text extraction for harvested NTRS records."""

from __future__ import annotations

import io
import logging

import httpx
import pdfplumber

logger = logging.getLogger(__name__)


async def extract_text(pdf_url: str, client: httpx.AsyncClient) -> str | None:
    """Download a PDF and extract its text, or None if that isn't possible."""
    try:
        response = await client.get(pdf_url)
        response.raise_for_status()
    except httpx.HTTPError:
        logger.warning("Failed to download PDF from %s", pdf_url, exc_info=True)
        return None

    try:
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception:
        logger.warning("Failed to extract text from PDF at %s", pdf_url, exc_info=True)
        return None

    text = "\n".join(pages).strip()
    if not text:
        logger.warning("No extractable text in PDF at %s", pdf_url)
        return None
    return text
