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

- This is a learning project. The human writes core abstractions (vector store, chunker, retriever, RAG pipeline) BY HAND for interview defensibility. Claude assists with boilerplate, config, tests, and review — not core architecture.
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
