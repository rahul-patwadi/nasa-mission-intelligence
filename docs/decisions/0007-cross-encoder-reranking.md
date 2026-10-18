# ADR 0007: Cross-Encoder Re-Ranking of Retrieved Chunks

**Status:** Accepted (deployment impact deferred — see Consequences)

## Context

ADR 0004 retrieves the top 5 chunks by vector similarity and sends them straight to the LLM. Bi-encoder similarity (`gemini-embedding-001` + Chroma L2) scores the question and each chunk independently, so a chunk that is topically close but does not actually answer the question can outrank one that does. With only 5 slots, a single misranked chunk displaces the useful one. Baseline retrieval quality (ADR 0006) is precision@5 = 0.70.

A cross-encoder reads the question and a chunk together and scores their relevance directly, which is typically more accurate than embedding distance, but too slow to run over the whole corpus. The standard remedy is two-stage retrieval: over-retrieve cheaply, then re-rank a small candidate set precisely.

## Decision

Add a re-ranking stage between vector retrieval and generation:

- Retrieve the top **20** chunks by vector similarity (`RETRIEVE_TOP_K` in `app/core/rag_chain.py`).
- Re-rank them with `cross-encoder/ms-marco-MiniLM-L-6-v2` via `sentence-transformers` (`app/core/reranker.py`) and keep the top **5** (`RERANK_TOP_N`), which are sent to Gemini exactly as before.
- Each returned chunk gets a `rerank_score` field. The vector store's `distance` is retained but is no longer used for ordering.
- The model is loaded **lazily and cached** (`functools.lru_cache`) rather than at import time, so importing the module, running unrelated tests, and starting the app do not pay the load cost; the first re-rank in a process does.
- `rerank` stays a synchronous function. `answer_query` calls it through `asyncio.to_thread` because `CrossEncoder.predict` is CPU-bound and would otherwise block the event loop.

Unchanged: chunking (ADR 0002), embeddings (ADR 0003/0006), the vector store, the prompt, and the no-information behavior.

## Consequences

**Expected benefit:** better precision@5 because the final 5 are chosen by a model that sees question and chunk together. This is a hypothesis until measured with `scripts/evaluate_retrieval.py` against the 0.70 baseline; as in ADR 0006, a lack of improvement is a reason to revisit this ADR, not to keep the extra cost.

**Costs accepted as a tradeoff:**

- **PyTorch dependency.** `sentence-transformers` pulls in `torch` and `transformers`. This is a large addition to the environment, on the order of 1–2 GB installed.
- **Docker image size.** The `Dockerfile` runs `uv sync --frozen --no-dev`, so the image will include `torch`. ADR 0006 shrank `data/chroma` specifically to fit free-tier hosting limits; this dependency works against that goal.
- **Cold start.** The first request in a fresh process loads the model (and downloads about 90 MB of weights from Hugging Face if not already cached), adding noticeable latency on scale-to-zero platforms such as Cloud Run.
- **Memory.** The backend container needs enough RAM for `torch` plus the model.
- **Per-query latency.** Scoring 20 pairs on CPU adds a small, bounded delay to each query.

**Deployment is explicitly not addressed here.** Options to evaluate after measuring real image size, memory, cold-start, and latency include baking the model into the image, a CPU-only `torch` build, raising container memory or min-instances, and calling a hosted re-ranker instead. Each is a deployment decision that warrants its own ADR if adopted.

**Rollback:** set `RETRIEVE_TOP_K` back to 5 and remove the `rerank` call, which restores ADR 0004 behavior. The dependency can then be dropped.
