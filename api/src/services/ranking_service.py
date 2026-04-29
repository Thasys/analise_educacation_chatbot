"""Service: ranking de paises em um indicador."""

from __future__ import annotations

from typing import Any

import duckdb

from src.services.timeseries_service import _intermediate_for


def rank_countries(
    conn: duckdb.DuckDBPyConnection,
    *,
    indicator: str,
    year: int | None,
    grouping: str | None,
    source: str,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Retorna (rows, meta).

    rows: lista ordenada por valor decrescente, top-N.
    meta: total_in_grouping, year_used (resolvido se input year=None).
    """
    table = _intermediate_for(indicator)
    where_parts: list[str] = [
        "i.indicator_id = ?",
        "i.source = ?",
        "i.value IS NOT NULL",
    ]
    params: list[Any] = [indicator, source]

    if grouping:
        where_parts.append("p.grouping = ?")
        params.append(grouping)

    # Resolve ano: se None, pega o ano com MAIOR cobertura (mais paises
    # com dado), desempate por mais recente. Evita pegar anos como 2023
    # onde so 1 pais publicou ainda -- 2022 com 26 paises e mais util.
    if year is None:
        year_q = f"""
            SELECT i.year, COUNT(*) AS n_countries
            FROM main_intermediate.{table} i
            LEFT JOIN main_seeds.iso_3166_paises p ON i.country_iso3 = p.iso3
            WHERE {' AND '.join(where_parts)}
            GROUP BY i.year
            ORDER BY n_countries DESC, i.year DESC
            LIMIT 1
        """
        row = conn.execute(year_q, params).fetchone()
        if row is None:
            return [], {"total_in_grouping": 0, "year_used": None}
        year_used = row[0]
    else:
        year_used = year
    where_parts.append("i.year = ?")
    params.append(year_used)

    where_sql = " AND ".join(where_parts)

    # Total no grouping
    total_q = f"""
        SELECT COUNT(*) FROM main_intermediate.{table} i
        LEFT JOIN main_seeds.iso_3166_paises p ON i.country_iso3 = p.iso3
        WHERE {where_sql}
    """
    total = conn.execute(total_q, params).fetchone()[0]

    # Top-N
    top_q = f"""
        SELECT
            ROW_NUMBER() OVER (ORDER BY i.value DESC) AS rank,
            i.country_iso3,
            p.name_pt   AS country_name,
            p.grouping,
            CAST(i.value AS DOUBLE) AS value
        FROM main_intermediate.{table} i
        LEFT JOIN main_seeds.iso_3166_paises p ON i.country_iso3 = p.iso3
        WHERE {where_sql}
        ORDER BY i.value DESC
        LIMIT ?
    """
    params_with_limit = [*params, limit]
    cur = conn.execute(top_q, params_with_limit)
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r, strict=True)) for r in cur.fetchall()]

    meta = {
        "year_used": year_used,
        "total_in_grouping": total,
        "showing": len(rows),
    }
    return rows, meta
