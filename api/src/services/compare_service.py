"""Service: comparacao de paises em um indicador-ano-fonte."""

from __future__ import annotations

import statistics
from typing import Any

import duckdb

from src.services.timeseries_service import _intermediate_for


def compare_countries(
    conn: duckdb.DuckDBPyConnection,
    *,
    indicator: str,
    countries: list[str],
    year: int,
    source: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Retorna (rows, stats).

    rows: uma linha por pais com `country_iso3, country_name, grouping, value`.
    stats: {min, max, mean, median, countries_with_data}.
    """
    if not countries:
        return [], {}

    table = _intermediate_for(indicator)
    placeholders = ",".join(["?"] * len(countries))

    query = f"""
        SELECT
            i.country_iso3,
            p.name_pt   AS country_name,
            p.grouping,
            CAST(i.value AS DOUBLE) AS value
        FROM main_intermediate.{table} i
        LEFT JOIN main_seeds.iso_3166_paises p
            ON i.country_iso3 = p.iso3
        WHERE i.indicator_id = ?
          AND i.year = ?
          AND i.source = ?
          AND i.country_iso3 IN ({placeholders})
          AND i.value IS NOT NULL
        ORDER BY i.value DESC
    """
    indicator_filter = _native_indicator_filter(indicator, source)
    params: list[Any] = [indicator_filter, year, source, *countries]

    cur = conn.execute(query, params)
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]

    if not rows:
        return [], {
            "min": None, "max": None, "mean": None, "median": None,
            "countries_with_data": 0,
        }

    values = [r["value"] for r in rows]
    stats = {
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "countries_with_data": len(values),
    }
    return rows, stats


def _native_indicator_filter(indicator: str, _source: str) -> str:
    """Os intermediates carregam o canonical indicator_id (GASTO_EDU_PIB / LITERACY_15M),
    nao o native id da fonte. So precisamos filtrar pelo canonico."""
    return indicator
