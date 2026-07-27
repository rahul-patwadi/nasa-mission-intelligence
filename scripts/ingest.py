"""Full ingestion pipeline: harvest -> extract -> chunk -> embed -> upsert.

Resumable: records whose chunks are already in the vector store are skipped
before any PDF download or embedding call, so a quota cutoff mid-run doesn't
waste already-completed work on the next run.

Run from the repo root with:
    uv run python -m scripts.ingest
    uv run python -m scripts.ingest --limit 20   # cap new records this run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any

import httpx

from app.core.embeddings import embed_chunks
from app.core.vectorstore import existing_record_ids, upsert_chunks
from app.fetcher.chunker import chunk_text
from app.fetcher.client import DEFAULT_TIMEOUT
from app.fetcher.extractor import extract_text
from app.fetcher.filter import pdf_url
from app.fetcher.harvest import harvest_all

logger = logging.getLogger(__name__)


async def _ingest_record(record: dict[str, Any], http_client: httpx.AsyncClient) -> int | None:
    """Extract, chunk, embed, and store one record's PDF.

    Returns the number of chunks stored, or None if the record was skipped
    because no text could be extracted from its PDF.
    """
    record_id = record["id"]
    mission = record["mission"]

    url = pdf_url(record)
    if url is None:
        logger.warning("Skipping record %s (%s): no PDF URL", record_id, mission)
        return None

    text = await extract_text(url, http_client)
    if text is None:
        logger.warning("Skipping record %s (%s): PDF extraction failed", record_id, mission)
        return None

    chunks = chunk_text(text, record_id=record_id, mission=mission)
    if not chunks:
        logger.warning(
            "Skipping record %s (%s): no chunks produced from extracted text", record_id, mission
        )
        return None

    embedded = await embed_chunks(chunks)
    upsert_chunks(embedded)
    return len(embedded)


async def run(limit: int | None = None) -> None:
    logger.info("Harvesting ingestable records across all missions...")
    records = await harvest_all()
    logger.info("Harvested %d ingestable records", len(records))

    already_ingested = existing_record_ids()
    logger.info(
        "%d records already in the vector store; they will be skipped", len(already_ingested)
    )

    total_chunks = 0
    processed = 0
    skipped_extraction = 0
    skipped_other = 0
    skipped_already_ingested = 0

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as http_client:
        for index, record in enumerate(records, start=1):
            mission = record["mission"]
            record_id = record["id"]

            if record_id in already_ingested:
                skipped_already_ingested += 1
                continue

            if limit is not None and processed >= limit:
                logger.info("Reached --limit=%d new records; stopping", limit)
                break

            logger.info(
                "[%d/%d] (%s) processing record %s", index, len(records), mission, record_id
            )

            try:
                chunk_count = await _ingest_record(record, http_client)
            except Exception:
                logger.warning(
                    "Skipping record %s (%s): unexpected error", record_id, mission, exc_info=True
                )
                skipped_other += 1
                continue

            if chunk_count is None:
                skipped_extraction += 1
                continue

            processed += 1
            total_chunks += chunk_count
            logger.info(
                "[%d/%d] (%s) record %s: stored %d chunks",
                index,
                len(records),
                mission,
                record_id,
                chunk_count,
            )

    total_skipped = skipped_extraction + skipped_other
    summary = (
        "\nIngestion summary:\n"
        f"  Records harvested:              {len(records)}\n"
        f"  Records already ingested:       {skipped_already_ingested}\n"
        f"  Records processed (new):        {processed}\n"
        f"  Chunks stored:                  {total_chunks}\n"
        f"  Records skipped (no text):      {skipped_extraction}\n"
        f"  Records skipped (other):        {skipped_other}\n"
        f"  Total new records skipped:      {total_skipped}\n"
    )
    logger.info(summary)
    print(summary)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process up to N new (not-yet-ingested) records this run.",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _parse_args()
    asyncio.run(run(limit=args.limit))


if __name__ == "__main__":
    main()
