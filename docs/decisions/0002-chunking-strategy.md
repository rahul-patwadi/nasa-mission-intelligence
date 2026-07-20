# ADR 0002: Chunking Strategy

**Status:** Accepted

## Context

Extracted document text (`app/fetcher/extractor.py`) must be split into smaller pieces before embedding and storage in the vector store. Chunk boundaries directly affect retrieval quality: chunks that are too large dilute embedding relevance and blow past LLM context budgets when several are retrieved together; chunks that are too small lose surrounding context needed to answer a question.

## Decision

Use LangChain's `RecursiveCharacterTextSplitter` (`langchain-text-splitters`) with `chunk_size=800` and `chunk_overlap=100` characters.

- **`RecursiveCharacterTextSplitter`**: splits on a prioritized list of separators (paragraph, then sentence, then word, then character), recursing only when a piece still exceeds `chunk_size`. This keeps chunks aligned to natural text boundaries in the common case, unlike a naive fixed-width splitter.
- **`chunk_size=800`**: sized for NASA technical report prose — large enough to hold a few complete sentences of technical context, small enough that several retrieved chunks still fit comfortably in an LLM prompt alongside the question and system instructions.
- **`chunk_overlap=100`**: prevents a sentence or fact from being fully lost at a chunk boundary, at the cost of some duplicated text stored in the vector store.

Each chunk is emitted as `{"text", "record_id", "mission", "chunk_index"}`, carrying enough metadata to trace a retrieved chunk back to its source document and reconstruct its position within that document.

## Consequences

- These are fixed constants for now, not per-document-type tunable; revisit if a mission's documents (e.g., short abstracts vs. long technical reports) turn out to need different chunk sizing.
- Overlap means ~12.5% of stored chunk text is duplicated content; this is deliberate.
- Changing `chunk_size`/`chunk_overlap`, or the splitter itself, invalidates existing embeddings and requires re-ingestion — treat that as a breaking change to the ingestion pipeline.
