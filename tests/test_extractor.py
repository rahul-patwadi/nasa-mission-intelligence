"""Tests for PDF text extraction."""

import io

import httpx
from reportlab.pdfgen import canvas

from app.fetcher.extractor import extract_text


def _make_pdf_bytes(text: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(100, 750, text)
    pdf.save()
    return buffer.getvalue()


def _client_returning(content: bytes, status_code: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=content)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_extract_text_returns_text_from_valid_pdf() -> None:
    pdf_bytes = _make_pdf_bytes("Hello NTRS")
    async with _client_returning(pdf_bytes) as client:
        result = await extract_text("https://example.com/report.pdf", client)

    assert result is not None
    assert "Hello NTRS" in result


async def test_extract_text_returns_none_for_corrupt_pdf() -> None:
    async with _client_returning(b"not a real pdf") as client:
        result = await extract_text("https://example.com/corrupt.pdf", client)

    assert result is None


async def test_extract_text_returns_none_on_download_failure() -> None:
    async with _client_returning(b"", status_code=404) as client:
        result = await extract_text("https://example.com/missing.pdf", client)

    assert result is None
