"""Mini FastAPI app do servico de agentes.

Uso (em desenvolvimento):

    cd agents
    .venv/Scripts/uvicorn src.server.main:app --reload --port 8001

Endpoints:
  - GET  /health                — liveness check
  - POST /api/chat/stream       — SSE com progresso do master flow

CORS aberto para localhost:3000 (frontend Next.js dev) por default.
"""

from __future__ import annotations

import os

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.logging_config import configure_logging
from src.server.chat_stream import router as chat_stream_router


log = structlog.get_logger(__name__)


def _cors_origins() -> list[str]:
    raw = os.environ.get("AGENTS_CORS_ORIGINS", "http://localhost:3000")
    return [o.strip() for o in raw.split(",") if o.strip()]


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="EduCompara Agents Server",
        description=(
            "Mini FastAPI do servico de agentes CrewAI. Expoe streaming "
            "SSE do master flow consumido pelo frontend Next.js."
        ),
        version=settings.service_version,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "agents-server",
            "version": settings.service_version,
        }

    app.include_router(chat_stream_router, tags=["chat"])
    log.info(
        "agents.server.ready",
        version=settings.service_version,
        cors_origins=_cors_origins(),
    )
    return app


app = create_app()
