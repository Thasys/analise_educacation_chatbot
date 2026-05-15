"""Router /api/data — endpoints REST que servem os marts Gold.

Atualizado 2026-05-14 (#6 do DRY pass): cronometragem + montagem de
DataResponse extraidas para `dependencies/response.py`. Cada endpoint
ficou com ~10 linhas de codigo de negocio + 1 chamada de helper.
"""

from __future__ import annotations

from typing import Annotated

import duckdb
from fastapi import APIRouter, Depends, HTTPException, Request

from src.dependencies.duckdb import get_duckdb_conn
from src.dependencies.ratelimit import limiter
from src.dependencies.response import build_data_response, measure_query_ms
from src.schemas.common import DataResponse
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
    with measure_query_ms() as elapsed:
        items = catalog_service.list_marts(conn)
    return build_data_response(items, query_ms=elapsed())


# ----------------------------------------------------------------------
# POST /api/data/timeseries
# ----------------------------------------------------------------------


@router.post("/timeseries", response_model=DataResponse)
@limiter.limit("60/minute")
def get_timeseries(
    request: Request, body: TimeseriesRequest, conn: DuckDBConn
) -> DataResponse:
    """Serie temporal de um indicador para um pais (multi-fonte)."""
    with measure_query_ms() as elapsed:
        rows, sources = timeseries_service.get_timeseries(
            conn,
            indicator=body.indicator,
            country_iso3=body.country_iso3,
            year_start=body.year_start,
            year_end=body.year_end,
            sources=list(body.sources) if body.sources else None,
        )
    return build_data_response(
        rows,
        query_ms=elapsed(),
        sources=sources,
        extra={
            "indicator": body.indicator,
            "country_iso3": body.country_iso3,
            "year_start": body.year_start,
            "year_end": body.year_end,
        },
        empty_note=(
            f"Nenhuma observacao para indicador={body.indicator}, "
            f"pais={body.country_iso3}, periodo={body.year_start}-{body.year_end}."
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
    with measure_query_ms() as elapsed:
        rows, stats = compare_service.compare_countries(
            conn,
            indicator=body.indicator,
            countries=list(body.countries),
            year=body.year,
            source=body.source,
        )
    return build_data_response(
        rows,
        query_ms=elapsed(),
        sources=[body.source],
        extra={
            "indicator": body.indicator,
            "year": body.year,
            "source": body.source,
            "comparison_stats": stats,
        },
        empty_note=(
            f"Nenhum dado para indicador={body.indicator}, ano={body.year}, "
            f"fonte={body.source} entre os paises informados."
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
    with measure_query_ms() as elapsed:
        rows, meta = ranking_service.rank_countries(
            conn,
            indicator=body.indicator,
            year=body.year,
            grouping=body.grouping,
            source=body.source,
            limit=body.limit,
        )
    if meta.get("year_used") is None:
        # Combinacao indicador+fonte+grouping nao tem dados.
        raise HTTPException(
            status_code=404,
            detail=(
                f"Nenhum dado para indicador={body.indicator}, "
                f"fonte={body.source}, grouping={body.grouping or 'global'}."
            ),
        )
    return build_data_response(
        rows,
        query_ms=elapsed(),
        sources=[body.source],
        extra={
            "indicator": body.indicator,
            "year_used": meta["year_used"],
            "year_requested": body.year,
            "grouping": body.grouping,
            "total_in_grouping": meta["total_in_grouping"],
            "showing": meta["showing"],
        },
    )
