"""Retrieval-augmented question answering over harvested mission documents."""

from __future__ import annotations

import asyncio
from typing import Any

from google import genai
from google.genai import types

from app.core.config import settings
from app.core.embeddings import embed_chunks
from app.core.reranker import rerank
from app.core.vectorstore import query as vectorstore_query

GENERATION_MODEL = "gemini-flash-latest"
# ADR 0007: over-retrieve by vector similarity, then re-rank with a cross-encoder.
RETRIEVE_TOP_K = 20
RERANK_TOP_N = 5
NO_INFO_ANSWER = "I don't have information on that."

# genai.Client has no timeout by default, so a stalled connection can hang
# indefinitely; bound every request explicitly (see embeddings.py).
_REQUEST_TIMEOUT_MS = 60_000

_SYSTEM_PROMPT = (
    "You are a mission-intelligence assistant. Answer the question using ONLY "
    "the context below, which is drawn from NASA mission documents. Do not use "
    "any outside knowledge. If the context does not contain the answer, "
    f'respond with exactly: "{NO_INFO_ANSWER}"\n\n'
    "When you do answer, cite the source(s) you used by their [source N] label."
)


async def retrieve_chunks(question: str, mission_filter: str | None = None) -> list[dict[str, Any]]:
    """Embed the question, retrieve candidates, and re-rank them to the final context chunks.

    Shared by answer_query and scripts/evaluate_retrieval.py so evals measure the real path.
    """
    [embedded_question] = await embed_chunks([{"text": question}])
    candidates = vectorstore_query(
        embedded_question["embedding"], mission_filter=mission_filter, top_k=RETRIEVE_TOP_K
    )

    if not candidates:
        return []

    # CrossEncoder.predict is synchronous and CPU-bound; keep it off the event loop.
    return await asyncio.to_thread(rerank, question, candidates, RERANK_TOP_N)


async def answer_query(question: str, mission_filter: str | None = None) -> dict[str, Any]:
    """Retrieve re-ranked context chunks for the question and generate a grounded answer."""
    chunks = await retrieve_chunks(question, mission_filter)

    if not chunks:
        return {"answer": NO_INFO_ANSWER, "sources": []}

    context = "\n\n".join(
        f"[source {i}] (mission: {chunk['mission']}, record: {chunk['record_id']})\n{chunk['text']}"
        for i, chunk in enumerate(chunks, start=1)
    )
    prompt = f"{_SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {question}"

    client = genai.Client(
        api_key=settings.google_api_key,
        http_options=types.HttpOptions(timeout=_REQUEST_TIMEOUT_MS),
    )
    response = await client.aio.models.generate_content(model=GENERATION_MODEL, contents=prompt)

    return {
        "answer": response.text or NO_INFO_ANSWER,
        "sources": [
            {
                "record_id": chunk["record_id"],
                "mission": chunk["mission"],
                "chunk_index": chunk["chunk_index"],
            }
            for chunk in chunks
        ],
    }
