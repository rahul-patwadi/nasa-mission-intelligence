# ADR 0004: Retrieval and Generation Strategy

**Status:** Accepted

## Context

`app/core/rag_chain.py` is the first component that ties retrieval and generation together into an actual question-answering pipeline: embed the question, fetch context chunks from the vector store, and ask an LLM to answer using that context. Two failure modes matter most for a document-intelligence tool like this: hallucinating an answer the source documents don't support, and failing to say when the corpus simply doesn't cover a question.

## Decision

### Retrieval: top-5, unranked beyond ChromaDB's similarity order

`answer_query()` retrieves the top 5 chunks (`TOP_K = 5`) from `vectorstore.query()`, optionally scoped by `mission_filter`. No re-ranking or MMR diversity step is applied — this is the simplest retrieval strategy that gives the LLM enough context to answer most single-document questions without an oversized prompt. If answer quality suffers on questions that need synthesis across many documents, revisit `TOP_K` or add re-ranking here.

### Grounding: instructed-refusal prompt, no separate "can this be answered" step

The prompt sent to the model explicitly restricts it to the retrieved context and instructs it to respond with a fixed string (`"I don't have information on that."`) when the context doesn't cover the question, rather than answering from general knowledge. This is enforced by instruction only — there is no separate classifier or retrieval-score threshold gating generation. The one hard-coded exception: **if retrieval returns zero chunks, the LLM is not called at all** and the fixed "don't know" answer is returned directly, since there's no context to reason over.

- **Consequence**: grounding depends on the model actually following the instruction. A model that ignores it and answers from general knowledge would produce plausible-looking but ungrounded answers with no automated check catching it.

### Citations: inline `[source N]` labels tied to the context block

Each retrieved chunk is numbered in the prompt (`[source 1]`, `[source 2]`, ...) alongside its mission and record id, and the model is instructed to cite which source(s) it used. `sources` in the response is always the full list of retrieved chunks' `{record_id, mission, chunk_index}` — it is not filtered down to only the chunks the model actually cited in its answer text. Callers that want to display "sources actually used" need to parse the `[source N]` markers out of `answer` themselves.

### Generation model: `gemini-flash-latest` via `google-genai`

A flash-tier model is used for cost/latency reasons — this is a portfolio project, not a latency- or reasoning-insensitive workload that would justify a larger model. As with `embeddings.py` (ADR 0003), the client is `google-genai`, not the end-of-life `google-generativeai`, for the same reason: no new code should be built against a dead SDK.

**2026-07-23 correction:** the model originally specified here, `gemini-2.5-flash`, is listed by `client.models.list()` but returns 404 ("no longer available to new users") when called — a pinned version can go stale even while still appearing in the catalog. Swapped to `gemini-flash-latest`, Google's maintained alias that always resolves to the current stable flash model, to avoid re-hitting this failure mode as models rotate. Trade-off: behavior can shift silently on Google's release schedule since the alias isn't a fixed version — acceptable here since answers aren't required to be reproducible across time for this project.

## Consequences

- Grounding is prompt-enforced, not verified. A hallucination-detection or citation-verification step is a reasonable future addition if this is used for anything beyond a portfolio demo.
- `sources` always reflects retrieval, not citation — a UI that wants to highlight only the sources actually referenced in the answer needs additional parsing of the answer text.
- Changing `TOP_K`, the prompt's grounding instructions, or the generation model is a behavior change to how answers are produced and should get a new ADR, per the working agreement's rule on retrieval logic changes.
