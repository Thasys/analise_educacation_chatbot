"""FastAPI gateway — ponto de entrada da aplicacao.

Fase 4: lifespan abre/fecha conexao DuckDB read-only; routers de
dados expostos sob /api/data/*. Rate limiting via SlowAPI.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import duckdb
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.config import settings
from src.dependencies.ratelimit import limiter
from src.dependencies.request_id import RequestIdMiddleware
from src.routers import data, health


log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Abre conexao DuckDB read-only no startup; fecha no shutdown."""
    duckdb_path = settings.duckdb_path.resolve()
    if duckdb_path.exists():
        try:
            conn = duckdb.connect(str(duckdb_path), read_only=True)
            conn.execute(f"SET memory_limit='{settings.duckdb_memory_limit}'")
            conn.execute(f"SET threads={settings.duckdb_threads}")
            app.state.duckdb_conn = conn
            log.info(
                "api.startup.duckdb_connected",
                path=str(duckdb_path),
                memory_limit=settings.duckdb_memory_limit,
                threads=settings.duckdb_threads,
            )
        except Exception as exc:
            log.error("api.startup.duckdb_failed", error=str(exc))
            app.state.duckdb_conn = None
    else:
        log.warning(
            "api.startup.duckdb_missing",
            path=str(duckdb_path),
            hint="Rode `dbt build` para criar o arquivo.",
        )
        app.state.duckdb_conn = None

    yield

    if getattr(app.state, "duckdb_conn", None):
        app.state.duckdb_conn.close()
        log.info("api.shutdown.duckdb_closed")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Analise Educacional Comparada — API",
        description=(
            "Gateway unificado para o sistema de analise comparada Brasil x "
            "Internacional em educacao basica. Expoe endpoints de dados "
            "(catalog, timeseries, compare, ranking) consumindo os marts "
            "Gold materializados em DuckDB pelo dbt."
        ),
        version=settings.api_version,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request-ID middleware (acima do CORS na pilha = adicionado depois)
    app.add_middleware(RequestIdMiddleware)

    # Rate limiting (SlowAPI)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Routers
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(data.router, prefix="/api/data", tags=["data"])
    return app


app = create_app()
