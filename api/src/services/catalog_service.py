"""Service: lista marts Gold disponiveis no DuckDB."""

from __future__ import annotations

from typing import Any

import duckdb


# Mapa estatico de descricoes por mart -- preenchido a partir dos
# schema.yml dos marts dbt. Mantido aqui para evitar parse de manifest.json
# em runtime; quando virar um problema, migrar para leitura do manifest.
MART_METADATA: dict[str, dict[str, Any]] = {
    "mart_br_vs_ocde__gasto_educacao_timeseries": {
        "description": (
            "Gasto publico em educacao (% PIB) para Brasil + 38 paises OCDE, "
            "2010-2023. Pivot por fonte (WB/UIS/OECD) + zscore + percentil + "
            "gap_to_oecd_mean + trend slope."
        ),
        "tags": ["gold", "gasto"],
    },
    "mart_alfabetizacao__latam_2020s": {
        "description": (
            "Taxa de alfabetizacao 15+ para Brasil + LATAM, 2020-2024. "
            "Pivot por fonte + zscore_in_latam + gap_to_bra + trend_slope."
        ),
        "tags": ["gold", "alfabetizacao"],
    },
    "mart_indicadores__rankings_recente": {
        "description": (
            "Rankings cross-indicador no ano mais recente disponivel por "
            "(indicador, fonte). Long format. Inclui rank_global e "
            "rank_in_grouping (oecd, latam, ...)."
        ),
        "tags": ["gold", "rankings"],
    },
    "mart_gasto_x_alfabetizacao__correlacao": {
        "description": (
            "Cruzamento gasto educacao x alfabetizacao por (pais, ano). "
            "INNER JOIN dos dois indicadores. Inclui efficiency_ratio e "
            "zscore_diff_alfab_minus_gasto para detectar outliers."
        ),
        "tags": ["gold", "cross"],
    },
    "mart_br__evolucao_indicadores": {
        "description": (
            "Trajetoria temporal completa do Brasil em todos os indicadores "
            "Silver, formato long. Inclui rank_in_ocde e rank_in_latam por "
            "(indicador, fonte, ano)."
        ),
        "tags": ["gold", "br"],
    },
}


def list_marts(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Retorna lista de marts Gold com metadata.

    Consulta `information_schema` filtrando por `table_schema='main_marts'`.
    Para cada tabela encontrada, faz `COUNT(*)` e cruza com MART_METADATA.
    """
    rows = conn.execute(
        """
        SELECT table_name, column_count
        FROM (
            SELECT table_name, COUNT(*) AS column_count
            FROM information_schema.columns
            WHERE table_schema = 'main_marts'
            GROUP BY table_name
        )
        ORDER BY table_name
        """
    ).fetchall()

    catalog: list[dict[str, Any]] = []
    for table_name, col_count in rows:
        row_count = conn.execute(
            f"SELECT COUNT(*) FROM main_marts.{table_name}"
        ).fetchone()[0]
        meta = MART_METADATA.get(table_name, {})
        catalog.append(
            {
                "name": table_name,
                "schema_name": "main_marts",
                "row_count": row_count,
                "column_count": col_count,
                "description": meta.get("description"),
                "tags": meta.get("tags", ["gold"]),
            }
        )
    return catalog
