"""Service: serie temporal de um indicador-pais."""

from __future__ import annotations

from typing import Any

import duckdb


def get_timeseries(
    conn: duckdb.DuckDBPyConnection,
    *,
    indicator: str,
    country_iso3: str,
    year_start: int,
    year_end: int,
    sources: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Retorna (rows, sources_observadas).

    Estrategia de query:
      - Para BRA: usa mart_br__evolucao_indicadores (ja tem rank e
        global_mean por ano).
      - Para outros paises: usa intermediates diretamente
        (int_indicadores__gasto_educacao / int_indicadores__alfabetizacao)
        para garantir cobertura ampla.

    SQL parametrizado via DuckDB `?` placeholders -- nunca f-string com
    input do usuario.
    """
    intermediate_table = _intermediate_for(indicator)
    base_query = f"""
        SELECT
            year,
            source,
            CAST(value AS DOUBLE) AS value,
            source_indicator_id
        FROM main_intermediate.{intermediate_table}
        WHERE country_iso3 = ?
          AND year BETWEEN ? AND ?
          AND value IS NOT NULL
    """
    params: list[Any] = [country_iso3, year_start, year_end]

    if sources:
        placeholders = ",".join(["?"] * len(sources))
        base_query += f" AND source IN ({placeholders})"
        params.extend(sources)

    base_query += " ORDER BY year, source"

    cur = conn.execute(base_query, params)
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]
    sources_observadas = sorted({r["source"] for r in rows})
    return rows, sources_observadas


def _intermediate_for(indicator: str) -> str:
    """Mapeia indicator_id canonico para tabela intermediate correspondente."""
    mapping = {
        "GASTO_EDU_PIB": "int_indicadores__gasto_educacao",
        "LITERACY_15M": "int_indicadores__alfabetizacao",
    }
    if indicator not in mapping:
        raise ValueError(f"Indicator desconhecido: {indicator}")
    return mapping[indicator]
