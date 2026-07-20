# ADR 0003: Embeddings Provider

**Status:** Accepted

**Supersedes:** the embeddings section of ADR 0001 (sentence-transformers)

## Context

ADR 0001 chose local `sentence-transformers` embeddings to avoid per-call cost and network latency during ingestion. In practice, running a local embedding model adds meaningful complexity for a solo portfolio project: it requires bundling/downloading model weights, managing memory footprint, and keeping inference code separate from the rest of the (already API-driven) pipeline. The project already depends on the Gemini API for the LLM; adding a second, API-based provider for embeddings keeps the ingestion pipeline consistent — one auth story, one rate-limit story — at the cost of network dependency and (small, free-tier) usage limits during ingestion.

## Decision

Use Google's `text-embedding-004` model via the `google-genai` SDK for chunk embeddings (`app/core/embeddings.py`), instead of local `sentence-transformers`.

- **`google-genai`**, not the older `google-generativeai` package: the latter is end-of-life (no further updates or bug fixes as of this writing) and explicitly tells callers to migrate to `google-genai`. Starting a new module on a dead SDK would be a known liability.
- Requests are batched (100 texts per call, the API's per-call maximum) rather than one embedding call per chunk, to reduce request volume during bulk ingestion.
- 429 (rate limit) responses are retried with exponential backoff up to a fixed retry budget; other errors propagate.

## Consequences

- Ingestion now has a hard network dependency on the Gemini API for embeddings, not just for the LLM step. A Gemini outage or missing/invalid API key blocks ingestion entirely (there is no local fallback).
- Embedding calls consume Gemini free-tier quota alongside LLM calls; large ingestion runs may need to be rate-limited or run over multiple sessions.
- Switching providers again later means re-embedding the full corpus, since embedding vectors from different models/dimensions aren't interchangeable in the vector store.
