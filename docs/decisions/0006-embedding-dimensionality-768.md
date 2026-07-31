# ADR 0006: Truncate Embedding Dimensionality to 768

**Status:** Accepted

## Context

`data/chroma` is 1.5GB for 539 ingested records (87,298 chunks). The HNSW vector index (`data_level0.bin`) alone is 1.03GB — 69% of total size — driven entirely by storing `gemini-embedding-001`'s full 3072-dimensional output as float32 for all 87,298 chunks (87,298 × 3072 × 4 bytes ≈ 1.07GB raw, matching the measured file size almost exactly). At this size, the vector store blocks deploying this portfolio project on typical free-tier hosting (Render/Railway/Fly.io free tiers commonly cap image or disk size well under 1.5GB).

`gemini-embedding-001` is trained with Matryoshka Representation Learning (MRL): its output can be truncated to a shorter prefix via the `output_dimensionality` parameter on `embed_content`, with 768 documented by Google as a validated, well-tested tier — not an arbitrary post-hoc chop of an unrelated vector.

## Decision

Set `output_dimensionality=768` in `app/core/embeddings.py`'s `embed_content` calls, for both chunk embeddings (ingestion) and question embeddings (query time) — both must match, since Chroma computes distance within one vector space.

- 4x reduction in raw vector bytes (3072→768) — expected to shrink the HNSW index from ~1.03GB to ~260MB, and total `data/chroma` from ~1.5GB to ~750MB.
- As with any embedding change (see ADR 0003), vectors from different dimensionalities aren't interchangeable — this requires **wiping `data/chroma` and re-embedding all 539 records from scratch**, no in-place migration.
- Before re-embedding, measure current (3072-dim) retrieval quality with `scripts/evaluate_retrieval.py` as a baseline, then re-run the same harness at 768 dims and compare. A material precision@5 regression on specific questions is a signal to try 1536 as a middle tier, not a reason to silently accept the smaller footprint.
- Rollout is gated on that comparison: this ADR records the architectural direction, but re-embedding the corpus should not proceed until the baseline eval (at 3072 dims) is captured and the post-truncation eval (at 768 dims) shows no material regression against it.

### Investigated and rejected: dropping `documents=` from Chroma upserts

Chroma's SQLite backend auto-builds an unused full-text-search index (~256MB) over stored `documents` on every upsert — this app never does keyword/`where_document` search. This looked like a second easy win, but `app/core/rag_chain.py:41-44` builds the LLM prompt's context directly from `chunk["text"]`, which is Chroma's stored `document` field, with no separate text store backing it. **Removing `documents=` would break `/query`'s ability to answer anything.** Reclaiming this space would require a separate text store (e.g. Postgres — in the stack per CLAUDE.md but not wired up in `app/db/` yet) and fetching text by id at query time — a bigger architectural change with its own sync-failure mode, deserving its own ADR. Deferred.

## Consequences

- Re-embedding all 539 records costs another full pass of Gemini `embed_content` calls, same free-tier quota constraints as the original harvest (ADR 0005's 1000/day ceiling) — may span more than one day.
- `data/chroma` must be wiped, not merged, before re-embedding.
- Any future embedding change (provider or dimension) continues to require a full re-embed.
- If 768 dims measurably regresses retrieval quality, next step is 1536, not an outright revert to 3072.
- The FTS index (~256MB) remains as unused overhead; removing it is out of scope here.

## Results (rollout, 2026-07-31)

Truncated output at `output_dimensionality=768` is **not pre-normalized** by the
API — measured directly against the live endpoint, 3072-dim output is unit-norm
(1.00000) while 768-dim output has per-text-varying norm (~0.586–0.589 observed).
Since the Chroma collection ranks by `hnsw:space=l2`, unnormalized truncated
vectors would make L2 distance diverge from cosine similarity, confounding any
precision@5 change with a magnitude artifact rather than dimensionality itself.
`_embed_batch` in `app/core/embeddings.py` now L2-normalizes every embedding
after truncation (`_normalize`), verified in the rebuilt store: all sampled
768-dim vectors have norm 1.0.

**Retrieval quality** (`scripts/evaluate_retrieval.py`, same 14 questions/labels
from the 3072 baseline — relevance judgments are dimension-independent):

| | precision@5 |
|---|---|
| 3072 dims (baseline, commit `97b62ae`) | 0.67 |
| 768 dims (post-rollout, normalized) | 0.70 |

No regression — retrieval quality holds within noise of the small eval set, so
the rollout gate is satisfied. 13 chunks retrieved at 768 dims were not seen at
3072 dims and have no label yet; the harness scaffolded them as `null` in
`scripts/eval_questions.json` (excluded from the precision@5 above, per the
harness's design) and they should be hand-labeled in a follow-up pass.

**Size** (539 records, full re-embed):

| | 3072 dims | 768 dims | reduction |
|---|---|---|---|
| `data/chroma` total | 1.5GB | 742MB | 51.7% |
| HNSW index (`data_level0.bin`) | 1.03GB | 272MB | 73.6% |

Matches this ADR's projections (~750MB total, ~260MB index) closely. Chunk count
moved from 87,298 to 86,003 for the same 539 records (~1.5% fewer) — attributed to
run-to-run non-determinism in PDF text extraction, not the dimensionality change.

**Status:** was already `Accepted` at authoring time (commit `97b62ae`); this
section records the outcome of the gated rollout, no status transition needed.
