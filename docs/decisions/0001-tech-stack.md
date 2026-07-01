# ADR 0001: Initial Tech Stack

**Status:** Accepted

## Context

This project is a Retrieval-Augmented Generation (RAG) system over NASA mission data. It is a portfolio project intended to demonstrate production-minded engineering practices. The stack must support rapid iteration, local development without cloud costs, and a credible path to deployment.

## Decision

### FastAPI (backend framework)

FastAPI is the HTTP layer. It is async-native, generates OpenAPI docs automatically, and enforces request/response schemas through Pydantic type annotations. The main tradeoff is that async code introduces complexity around blocking I/O (e.g., database calls must use async drivers or run in a thread pool). We accept this tradeoff because the I/O-heavy nature of RAG pipelines — embedding calls, vector searches, LLM requests — benefits directly from async concurrency.

### LangChain (RAG orchestration)

LangChain provides abstractions for document loading, text splitting, retrieval chains, and prompt management. The criticism of the library — that it over-abstracts and hides what is actually happening — is fair. We accept it here to move faster during the initial build, with the explicit understanding that we will read the source or step through chains when debugging. Any component that becomes a black-box problem will be replaced with direct implementation.

### ChromaDB (vector store, local development)

ChromaDB runs in-process with no external dependencies, which makes local development frictionless. The limitation is that managed deployment platforms (Render, Railway) do not offer persistent local disk that survives redeploys, making ChromaDB impractical for production. To avoid being locked in, the vector store is accessed only through an abstract interface. This allows swapping to Qdrant Cloud or pgvector for deployment without changing the rest of the codebase.

### Gemini API free tier (LLM)

The free tier of the Gemini API eliminates inference costs during development. The known constraint is rate limiting, which will cause failures during bulk document ingestion if not handled. We will implement exponential backoff and retry logic in the ingestion pipeline. The LLM is treated as a swappable component; switching to the OpenAI API should require changing only configuration and a thin adapter layer.

### sentence-transformers (embeddings)

Embeddings are generated locally using a pre-trained `sentence-transformers` model. This removes per-call embedding costs entirely and avoids network latency during ingestion. The tradeoff is that the model must fit in memory on the host and that local embedding quality may differ from API-hosted models. For a document corpus of NASA mission data, a general-purpose sentence transformer is sufficient to validate the architecture.

### PostgreSQL (conversation history and sessions)

Conversation history and session metadata are stored in PostgreSQL. A relational database is appropriate here: the data is structured, queries are predictable, and PostgreSQL has strong ecosystem support. ChromaDB handles vector data; PostgreSQL handles everything else. This avoids the operational complexity of adding a dedicated session store.

### uv (dependency management)

`uv` replaces pip and virtualenv. It is significantly faster for dependency resolution and installation, and it produces a lockfile (`uv.lock`) that pins the full dependency graph for reproducible builds. The main risk is that `uv` is a younger tool; if a dependency has unusual build requirements, fallback to pip may be needed.

### Angular (frontend)

Angular is the frontend framework. It was chosen over React because the author has prior production Angular experience (Dell), and the frontend here is a demonstration layer rather than a core engineering focus — minimizing frontend learning curve preserves time for backend depth.

### mypy, ruff, pytest (code quality)

- **mypy** with strict mode enforces type annotations across the codebase. This catches a class of bugs at development time and makes the code easier to reason about when the project is read by others.
- **ruff** replaces flake8, isort, and parts of pylint with a single fast linter. Configuration lives in `pyproject.toml`.
- **pytest** is the test runner. Tests are co-located with the code they test under `tests/`.

## Consequences

- Local development requires no cloud accounts or running services beyond PostgreSQL (which runs in Docker).
- The vector store abstraction adds a small amount of indirection that must be maintained as the interface evolves.
- LangChain upgrades may introduce breaking changes in chain APIs; version pins in `uv.lock` mitigate this.
- Rate limiting on the Gemini free tier is a real operational constraint during ingestion runs and must be handled explicitly, not assumed away.
- Strict mypy increases upfront development time but reduces debugging time and improves readability for reviewers.
