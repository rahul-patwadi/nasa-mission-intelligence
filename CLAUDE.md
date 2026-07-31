# NASA Mission Intelligence — Claude Context

## Project

NASA Mission Intelligence — an enterprise document-intelligence RAG system demonstrated on NASA technical reports. Portfolio project for AI engineering roles. Built solo by Rahul Patwadi.

## Tech stack

Python 3.12, FastAPI, LangChain, ChromaDB (abstracted behind an interface), Gemini API, sentence-transformers, PostgreSQL, Docker, Angular frontend. Managed with uv.

## Code standards (enforce these)

- Strict mypy passes — every function fully type-annotated, no untyped defs
- ruff lint + format clean before every commit
- All new code has tests (pytest, async tests via pytest-asyncio)
- Conventional Commits format for messages (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`)

## Working agreement (important)

- Before implementing anything non-trivial, explain your approach in a few bullets and WAIT for confirmation. Do not make architectural decisions unilaterally.
- Do not add new dependencies without asking first.
- Do not change chunking strategy, retrieval logic, or vector store choice without an ADR.

## Structure

```
app/
  api/routes/
  core/
  data/
  db/
tests/
docs/decisions/   # ADRs
frontend/         # Angular (later)
```
## NASA document fetcher (NTRS)

### Data source
- NASA NTRS OpenAPI: root `https://ntrs.nasa.gov/api`, public, no auth.
- Interactive docs: https://ntrs.nasa.gov/api/openapi/

### Architectural decisions (don't relitigate without a new ADR)
- Use the **search API** (`/citations/search`), NOT the yearly bulk ndjson dump.
  Reason: corpus is mission-scoped, fits under the 10k-records/query cap, and
  avoids downloading + filtering the entire repository.
- Scope = six missions (Apollo, Artemis, ISS, Mars, Hubble, Voyager),
  config-driven so more can be added. Query each keyword, sorted by relevance
  (`sort.field=score`, `sort.order=desc`), capped at `RECORDS_PER_MISSION = 300`
  per mission, dedup by record `id` (see ADR 0005 — an exhaustive id-sorted
  fetch was too slow: thousands of loosely-relevant hits per mission keyword).
- Pre-filter at the source with `disseminated=DOCUMENT_AND_METADATA` +
  `distribution=PUBLIC` so we only pull records that actually have a document.

### API constraints (already baked into client.py)
- Rate limit: 500 requests / 15 min. Hard cap: 10,000 records / query.
- Page size max 100 (`page.size` + `from` offset).
- Download links come back relative (`/api/citations/...`) — prefix
  `https://ntrs.nasa.gov`.
- TODO: confirm search param shape (query-string vs POST body) against the
  live endpoint.
- Every architectural decision gets a new ADR.

Current status: backend done + populated, frontend works end-to-end, ADR 0006 rolled out — corpus re-embedded at 768 dims (normalized), data/chroma 1.5GB -> 742MB, precision@5 0.67 -> 0.70 (no regression). Next step: hand-label the 13 NEEDS LABEL chunks scaffolded in scripts/eval_questions.json by the 768-dim eval run.