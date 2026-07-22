"""Missions endpoint: static list of supported missions."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.fetcher.harvest import MISSIONS

router = APIRouter()


class MissionsResponse(BaseModel):
    missions: list[str]


@router.get("/missions", response_model=MissionsResponse)
async def get_missions() -> MissionsResponse:
    """Return the static list of supported missions."""
    return MissionsResponse(missions=MISSIONS)
