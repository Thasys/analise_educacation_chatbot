"""Health check endpoint — verifica se a API está viva."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="edu-api",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )
