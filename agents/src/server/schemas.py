"""Schemas do mini-server de agentes."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.schemas import ProfileKind


class ChatStreamRequest(BaseModel):
    """Body do POST /api/chat/stream."""

    question: str = Field(..., min_length=1, max_length=2000)
    profile_hint: ProfileKind | None = Field(
        default=None,
        description=(
            "Perfil sugerido pelo frontend. Hoje NAO sobrescreve a "
            "deteccao automatica do Orchestrator — reservado para uso "
            "futuro em casos ambiguos."
        ),
    )


# Tipos canonicos de evento que o servidor emite (espelhados em
# frontend/types/domain.ts::StreamEvent).
EventType = Literal[
    "flow_started",
    "agent_started",
    "agent_done",
    "final_answer",
    "error",
]


class ChatStreamEvent(BaseModel):
    """Estrutura de cada evento SSE emitido."""

    type: EventType
    ts: float
    # Campos opcionais conforme `type`. Mantemos schema permissivo.
    agent: str | None = None
    question: str | None = None
    result: dict[str, Any] | None = None
    tool_calls: int | None = None
    method: str | None = None
    sample_size: int | None = None
    items: int | None = None
    chart_type: str | None = None
    elapsed_s: float | None = None
    payload: dict[str, Any] | None = None
    error: str | None = None
