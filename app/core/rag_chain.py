"""Retrieval-augmented question answering over harvested mission documents."""

from __future__ import annotations

from typing import Any

from google import genai

from app.core.config import settings
from app.core.embeddings import embed_chunks
from app.core.vectorstore import query as vectorstore_query

GENERATION_MODEL = "gemini-flash-latest"
TOP_K = 5
NO_INFO_ANSWER = "I don't have information on that."

_SYSTEM_PROMPT = (
    "You are a mission-intelligence assistant. Answer the question using ONLY "
    "the context below, which is drawn from NASA mission documents. Do not use "
    "any outside knowledge. If the context does not contain the answer, "
    f'respond with exactly: "{NO_INFO_ANSWER}"\n\n'
    "When you do answer, cite the source(s) you used by their [source N] label."
)


async def answer_query(question: str, mission_filter: str | None = None) -> dict[str, Any]:
    """Embed the question, retrieve context chunks, and generate a grounded answer."""
    [embedded_question] = await embed_chunks([{"text": question}])
    chunks = vectorstore_query(
        embedded_question["embedding"], mission_filter=mission_filter, top_k=TOP_K
    )

    if not chunks:
        return {"answer": NO_INFO_ANSWER, "sources": []}

    context = "\n\n".join(
        f"[source {i}] (mission: {chunk['mission']}, record: {chunk['record_id']})\n{chunk['text']}"
        for i, chunk in enumerate(chunks, start=1)
    )
    prompt = f"{_SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {question}"

    client = genai.Client(api_key=settings.google_api_key)
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
