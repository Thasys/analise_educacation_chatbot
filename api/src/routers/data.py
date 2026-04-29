"""Router /api/data — endpoints REST que servem os marts Gold."""

from __future__ import annotations

import time
from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Request

from src.dependencies.duckdb import get_duckdb_conn
from src.dependencies.ratelimit import limiter
from src.schemas.common import DataResponse, ResponseMeta
from src.schemas.compare import CompareRequest
from src.schemas.ranking import RankingRequest
from src.schemas.timeseries import TimeseriesRequest
from src.services import (
    catalog_service,
    compare_service,
    ranking_service,
    timeseries_service,
)


router = APIRouter()

DuckDBConn = Annotated[duckdb.DuckDBPyConnection, Depends(get_duckdb_conn)]


# ----------------------------------------------------------------------
# GET /api/data/catalog
# ----------------------------------------------------------------------


@router.get("/catalog", response_model=DataResponse)
@limiter.limit("120/minute")
def get_catalog(request: Request, conn: DuckDBConn) -> DataResponse:
    """Lista marts Gold disponiveis com metadata, contagens e tags."""
    started = time.perf_counter()
    items = catalog_service.list_marts(conn)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return DataResponse(
        data=items,
        meta=ResponseMeta(total_rows=len(items), query_ms=round(elapsed_ms, 2)),
    )


# ----------------------------------------------------------------------
# POST /api/data/timeseries
# ----------------------------------------------------------------------


@router.post("/timeseries", response_model=DataResponse)
@limiter.limit("60/minute")
def get_timeseries(
    request: Request, body: TimeseriesRequest, conn: DuckDBConn
) -> DataResponse:
    """Serie temporal de um indicador para um pais (multi-fonte)."""
    started = time.perf_counter()
    rows, sources = timeseries_service.get_timeseries(
        conn,
        indicator=body.indicator,
        country_iso3=body.country_iso3,
        year_start=body.year_start,
        year_end=body.year_end,
        sources=list(body.sources) if body.sources else None,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    notes: list[str] = []
    if not rows:
        notes.append(
            f"Nenhuma observacao para indicador={body.indicator}, "
            f"pais={body.country_iso3}, periodo={body.year_start}-{body.year_end}."
        )
    return DataResponse(
        data=rows,
        meta=ResponseMeta(
            total_rows=len(rows),
            query_ms=round(elapsed_ms, 2),
            sources=sources,
            notes=notes or None,
            extra={
                "indicator": body.indicator,
                "country_iso3": body.country_iso3,
                "year_start": body.year_start,
                "year_end": body.year_end,
            },
        ),
    )


# ----------------------------------------------------------------------
# POST /api/data/compare
# ----------------------------------------------------------------------


@router.post("/compare", response_model=DataResponse)
@limiter.limit("60/minute")
def post_compare(
    request: Request, body: CompareRequest, conn: DuckDBConn
) -> DataResponse:
    """Comparacao de varios paises em um indicador-ano-fonte."""
    started = time.perf_counter()
    rows, stats = compare_service.compare_countries(
        conn,
        indicator=body.indicator,
        countries=list(body.countries),
        year=body.year,
        source=body.source,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    notes: list[str] = []
    if not rows:
        notes.append(
            f"Nenhum dado para indicador={body.indicator}, ano={body.year}, "
            f"fonte={body.source} entre os paises informados."
        )
    return DataResponse(
        data=rows,
        meta=ResponseMeta(
            total_rows=len(rows),
            query_ms=round(elapsed_ms, 2),
            sources=[body.source],
            notes=notes or None,
            extra={
                "indicator": body.indicator,
                "year": body.year,
                "source": body.source,
                "comparison_stats": stats,
            },
        ),
    )


# ----------------------------------------------------------------------
# POST /api/data/ranking
# ----------------------------------------------------------------------


@router.post("/ranking", response_model=DataResponse)
@limiter.limit("60/minute")
def post_ranking(
    request: Request, body: RankingRequest, conn: DuckDBConn
) -> DataResponse:
    """Ranking de paises em um indicador, opcionalmente filtrado por grouping."""
    started = time.perf_counter()
    rows, meta = ranking_service.rank_countries(
        conn,
        indicator=body.indicator,
        year=body.year,
        grouping=body.grouping,
        source=body.source,
        limit=body.limit,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    if meta.get("year_used") is None:
        # Combinacao indicador+fonte+grouping nao tem dados.
        raise HTTPException(
            status_code=404,
            detail=(
                f"Nenhum dado para indicador={body.indicator}, "
                f"fonte={body.source}, grouping={body.grouping or 'global'}."
            ),
        )
    return DataResponse(
        data=rows,
        meta=ResponseMeta(
            total_rows=len(rows),
            query_ms=round(elapsed_ms, 2),
            sources=[body.source],
            extra={
                "indicator": body.indicator,
                "year_used": meta["year_used"],
                "year_requested": body.year,
                "grouping": body.grouping,
                "total_in_grouping": meta["total_in_grouping"],
                "showing": meta["showing"],
            },
        ),
    )
