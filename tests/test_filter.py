"""Tests for NTRS record filtering."""

from typing import Any

from app.fetcher.filter import is_ingestable, pdf_url


def _record(
    downloads: list[dict[str, Any]],
    downloads_available: bool = True,
    distribution: str = "PUBLIC",
    itar: str = "NO",
    ear: str = "NO",
) -> dict[str, Any]:
    return {
        "downloadsAvailable": downloads_available,
        "downloads": downloads,
        "distribution": distribution,
        "exportControl": {"itar": itar, "ear": ear},
    }


def test_pdf_url_returns_absolute_link_for_curated_pdf() -> None:
    record = _record(
        [
            {
                "draft": False,
                "mimetype": "application/pdf",
                "links": {"pdf": "/api/citations/1/downloads/1.pdf"},
            }
        ]
    )

    assert pdf_url(record) == "https://ntrs.nasa.gov/api/citations/1/downloads/1.pdf"


def test_pdf_url_none_when_downloads_not_available() -> None:
    record = _record(
        [{"draft": False, "mimetype": "application/pdf", "links": {"pdf": "/x.pdf"}}],
        downloads_available=False,
    )

    assert pdf_url(record) is None


def test_pdf_url_skips_draft_entries() -> None:
    record = _record(
        [
            {"draft": True, "mimetype": "application/pdf", "links": {"pdf": "/draft.pdf"}},
            {"draft": False, "mimetype": "application/pdf", "links": {"pdf": "/final.pdf"}},
        ]
    )

    assert pdf_url(record) == "https://ntrs.nasa.gov/final.pdf"


def test_pdf_url_none_when_no_pdf_link_present() -> None:
    record = _record(
        [
            {
                "draft": False,
                "mimetype": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                "links": {"original": "/deck.pptx"},
            }
        ]
    )

    assert pdf_url(record) is None


def test_is_ingestable_true_when_pdf_available() -> None:
    record = _record([{"draft": False, "mimetype": "application/pdf", "links": {"pdf": "/x.pdf"}}])

    assert is_ingestable(record) is True


def test_is_ingestable_false_when_no_downloads() -> None:
    record = _record([], downloads_available=False)

    assert is_ingestable(record) is False


def test_is_ingestable_false_when_not_public() -> None:
    record = _record(
        [{"draft": False, "mimetype": "application/pdf", "links": {"pdf": "/x.pdf"}}],
        distribution="LIMITED",
    )

    assert is_ingestable(record) is False


def test_is_ingestable_false_when_itar_restricted() -> None:
    record = _record(
        [{"draft": False, "mimetype": "application/pdf", "links": {"pdf": "/x.pdf"}}],
        itar="YES",
    )

    assert is_ingestable(record) is False


def test_is_ingestable_false_when_ear_restricted() -> None:
    record = _record(
        [{"draft": False, "mimetype": "application/pdf", "links": {"pdf": "/x.pdf"}}],
        ear="YES",
    )

    assert is_ingestable(record) is False
