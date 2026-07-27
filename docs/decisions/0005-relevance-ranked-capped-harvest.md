# ADR 0005: Relevance-Ranked, Capped Harvest Per Mission

**Status:** Accepted

**Supersedes:** the harvest-loop portion of ADR's implicit decision described in CLAUDE.md's "Query each keyword, dedup by record id" (id-sorted, exhaustive per-mission fetch)

## Context

The original harvest loop sorted NTRS search results by `id` ascending and paginated through every matching record per mission (bounded only by the API's 10,000-records-per-query hard cap). In practice, a mission keyword like "Hubble" or "Apollo" matches thousands of loosely-related records (NTRS's `q=` search appears to be a broad text match against title/abstract/keywords, not a strict mission tag), so a full ingestion run spent 25+ minutes just paginating through search results for a single mission, without a single PDF downloaded or chunk embedded yet. That's not a viable ingestion loop for a portfolio project meant to be run and re-run during development.

## Decision

- **Sort by relevance, not id**: `NTRSClient._search_page()` now sends `sort.field=score`, `sort.order=desc` instead of `sort.field=id`, `sort.order=asc`. The most relevant hits for a mission keyword come back first.
- **Cap at 100 records per mission**: `harvest.py`'s `RECORDS_PER_MISSION = 100` is passed as `limit` to `NTRSClient.search()`, which now stops paginating as soon as it has collected `limit` records — it does not fetch further pages just to discard them. Six missions x 100 = at most 600 raw search hits considered, versus a potential tens of thousands before. (Originally set to 300; lowered further, see the 2026-07-26 addendum below.)
- The cap applies to raw search results per mission, before `is_ingestable` filtering and cross-mission dedup — the number of records that actually get ingested will be smaller still.
- `NTRSClient.search()` keeps `limit: int | None = None` as an opt-in parameter (default: fetch everything, old behavior) rather than always capping, so the client itself stays a general-purpose wrapper; the per-mission cap policy is a `harvest.py` decision, not a `client.py` one.

We're trading completeness (every matching PUBLIC record with a document) for a corpus that's relevance-ranked and bounded in a predictable amount of time. For a demo/portfolio RAG system, a smaller set of the most relevant documents per mission is a more useful corpus than an unranked, unbounded firehose that takes potentially hours to harvest and embed.

## Consequences

- Some genuinely relevant documents beyond the cap (by NTRS's relevance score, for that mission's exact keyword) will never be ingested. If retrieval quality suffers from missing coverage, `RECORDS_PER_MISSION` is the first knob to revisit — not a return to exhaustive fetching, which reintroduces the original runtime problem.
- Relevance ranking is NTRS's own `score` field — we don't control or inspect its ranking algorithm. This is a change to the actual set of documents that ends up in the corpus, not just to how fast we get there.
- A record could rank in the top N for one mission and never be discovered via another mission's keyword even if genuinely relevant to both, unlike the old exhaustive fetch. `harvest.py`'s existing first-match-wins mission tagging (see the mission-attribution fix from harvest.py) is unaffected by this change, but the input set feeding it is smaller.
- Re-running ingestion after this change requires clearing and rebuilding the vector store's affected records if strict reproducibility of "everything previously ingested" matters — the record set is no longer a strict superset across runs (relevance scores are stable, but the ranking is NTRS-side and could change).

## 2026-07-26 addendum: quota-driven cap reduction and resumable ingestion

Even a relevance-ranked, harvest-capped run still turned out to be bottlenecked by a resource we hadn't accounted for: Gemini's free-tier `embed_content` quota is capped at **1000 requests/day**, not just per-minute. A run that hit this daily ceiling partway through failed every subsequent record for the rest of the day, and re-running from scratch would have re-downloaded and re-embedded records that had already succeeded — wasting quota on work already done.

Two changes address this:

- **`RECORDS_PER_MISSION` lowered from 300 to 100** (600 max raw hits across all six missions instead of 1,800), to leave more headroom under the daily embedding quota, including headroom for repeated runs during development.
- **`scripts/ingest.py` is now resumable**: before processing any record, it calls the new `vectorstore.existing_record_ids()` (queries the collection's stored `metadatas` for distinct `record_id`s) and skips records already present — before downloading a PDF or calling the embedding API, not just before the final upsert. `upsert_chunks()` itself was already idempotent (Chroma's `upsert` overwrites by id), so this fix belongs in the caller's decision of whether to do the expensive work at all, not in the vector store wrapper.
- **`scripts/ingest.py --limit N`** caps the number of *new* (not-already-ingested) records processed in a single run, for controlled, quota-conscious runs during development instead of always attempting the full harvested set.

Consequence: a quota cutoff now costs at most one run's worth of newly-attempted records, not the whole corpus — the next run picks up where the previous one left off.
