"""FastAPI gateway — ponto de entrada da aplicação.

Fase 0 (Bootstrap): apenas health check e metadados OpenAPI.
Novos routers serão adicionados nas fases 4+.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: conexões, caches, índices (a preencher nas próximas fases)
    yield
    # Shutdown: limpeza de recursos


def create_app() -> FastAPI:
    app = FastAPI(
        title="Análise Educacional Comparada — API",
        description=(
            "Gateway unificado para o sistema de análise comparada Brasil × Internacional "
            "em educação básica. Expõe endpoints de dados, RAG, chat e visualização."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    cors_origins = os.getenv("API_CORS_ORIGINS", "http://localhost:3000").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    return app


app = create_app()
