"""Query endpoint: retrieval-augmented question answering."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.rag_chain import answer_query

router = APIRouter()


class QueryRequest(BaseModel):
    question: str
    mission_filter: str | None = None


class SourceItem(BaseModel):
    record_id: int
    mission: str
    chunk_index: int


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceItem]


@router.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Answer a natural-language question using retrieval-augmented generation."""
    result = await answer_query(request.question, mission_filter=request.mission_filter)
    return QueryResponse(**result)
