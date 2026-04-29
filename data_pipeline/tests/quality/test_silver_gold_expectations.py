"""Suite de Data Quality (Great Expectations style) para Silver e Gold.

Testes que vao alem de `not_null` / `unique` / `accepted_range` que dbt
ja cobre. Aqui validamos:

- Distribuicoes (medias e desvios dentro de range esperado).
- Correlacoes esperadas entre fontes (UIS == WB por construcao).
- Cobertura minima (numero de paises, anos, fontes).
- Consistencia logica (canonical = coalesce; rank entre [1, count]).

Pre-requisito: `dbt build` ja executado e DuckDB populado em
`data/duckdb/education.duckdb`. Caso contrario, todos os testes saltam
com `pytest.skip` (nao reprovam).

Marcado como `@pytest.mark.quality` -- rodar com `pytest -m quality`.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

# Path para o DuckDB. Resolve relativo a este arquivo (`<repo>/data_pipeline/
# tests/quality/test_*.py`) ou usa env var DUCKDB_PATH se disponivel.
REPO_ROOT = Path(__file__).resolve().parents[3]
DUCKDB_PATH = REPO_ROOT / "data" / "duckdb" / "education.duckdb"


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DUCKDB_PATH.exists():
        pytest.skip(f"DuckDB nao encontrado em {DUCKDB_PATH}; rode `dbt build` primeiro.")
    conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    yield conn
    conn.close()


# ----------------------------------------------------------------------
# 1. Distribuicoes esperadas (Silver intermediate)
# ----------------------------------------------------------------------


@pytest.mark.quality
def test_gasto_educacao_mean_in_realistic_range(con: duckdb.DuckDBPyConnection) -> None:
    """Media global de gasto educacao % PIB deve ficar entre 3.5% e 6.5%.

    Referencia: World Bank EdStats agregados — paises tipicamente
    gastam 4-6% do PIB. Media abaixo de 3.5 ou acima de 6.5 indica
    bug (ex.: erro de unidade, agregados nao filtrados).
    """
    avg_value = con.sql("""
        SELECT AVG(value) FROM main_intermediate.int_indicadores__gasto_educacao
        WHERE source = 'worldbank'
    """).fetchone()[0]
    assert avg_value is not None
    assert 3.5 <= avg_value <= 6.5, f"Media gasto educacao = {avg_value:.2f}, fora do range [3.5, 6.5]"


@pytest.mark.quality
def test_alfabetizacao_mean_in_realistic_range(con: duckdb.DuckDBPyConnection) -> None:
    """Media global de alfabetizacao 15+ deve ficar entre 80% e 99%.

    Range refletindo paises em desenvolvimento (~80%) ate desenvolvidos
    (~99%). Fora disso e bug de unidade ou filtro mal-aplicado.
    """
    avg_value = con.sql("""
        SELECT AVG(value) FROM main_intermediate.int_indicadores__alfabetizacao
        WHERE source = 'unesco'
    """).fetchone()[0]
    assert avg_value is not None
    assert 80.0 <= avg_value <= 99.0, f"Media alfabetizacao = {avg_value:.2f}, fora de [80, 99]"


# ----------------------------------------------------------------------
# 2. Correlacoes esperadas entre fontes
# ----------------------------------------------------------------------


@pytest.mark.quality
def test_worldbank_unesco_gasto_match_perfect(con: duckdb.DuckDBPyConnection) -> None:
    """WB e UIS publicam o mesmo gasto educacao -- diferencas devem ser ~0.

    O World Bank ressindica os dados UIS (XGDP.FSGOV vs SE.XPD.TOTL.GD.ZS).
    Diferencas por pais-ano deveriam ser sempre < 0.01pp. Se houver
    divergencia maior, indica bug em algum coletor ou parser.
    """
    max_diff = con.sql("""
        WITH paired AS (
            SELECT
                country_iso3, year,
                MAX(CASE WHEN source='worldbank' THEN value END) AS wb,
                MAX(CASE WHEN source='unesco'    THEN value END) AS ui
            FROM main_intermediate.int_indicadores__gasto_educacao
            WHERE source IN ('worldbank', 'unesco')
            GROUP BY 1, 2
        )
        SELECT MAX(ABS(wb - ui)) FROM paired
        WHERE wb IS NOT NULL AND ui IS NOT NULL
    """).fetchone()[0]
    assert max_diff is not None, "Sem pares WB+UIS encontrados (intermediate vazio?)"
    assert max_diff < 0.01, f"Max divergencia WB-UIS = {max_diff:.4f}pp, deveria ser ~0"


@pytest.mark.quality
def test_worldbank_unesco_alfab_match_perfect(con: duckdb.DuckDBPyConnection) -> None:
    """WB e UIS publicam a mesma taxa de alfabetizacao -- diferencas ~0."""
    max_diff = con.sql("""
        WITH paired AS (
            SELECT
                country_iso3, year,
                MAX(CASE WHEN source='worldbank' THEN value END) AS wb,
                MAX(CASE WHEN source='unesco'    THEN value END) AS ui
            FROM main_intermediate.int_indicadores__alfabetizacao
            WHERE source IN ('worldbank', 'unesco')
            GROUP BY 1, 2
        )
        SELECT MAX(ABS(wb - ui)) FROM paired
        WHERE wb IS NOT NULL AND ui IS NOT NULL
    """).fetchone()[0]
    assert max_diff is not None
    assert max_diff < 0.01, f"Max divergencia WB-UIS alfab = {max_diff:.4f}pp"


# ----------------------------------------------------------------------
# 3. Cobertura minima
# ----------------------------------------------------------------------


@pytest.mark.quality
def test_mart_br_vs_ocde_min_country_coverage(con: duckdb.DuckDBPyConnection) -> None:
    """Mart BR vs OCDE precisa cobrir >= 30 paises (BR + ~30 OCDE)."""
    n_countries = con.sql("""
        SELECT COUNT(DISTINCT country_iso3)
        FROM main_marts.mart_br_vs_ocde__gasto_educacao_timeseries
    """).fetchone()[0]
    assert n_countries >= 30, f"Mart cobre apenas {n_countries} paises; minimo 30."


@pytest.mark.quality
def test_mart_alfabetizacao_latam_min_coverage(con: duckdb.DuckDBPyConnection) -> None:
    """Mart alfabetizacao LATAM precisa cobrir >= 10 paises."""
    n_countries = con.sql("""
        SELECT COUNT(DISTINCT country_iso3)
        FROM main_marts.mart_alfabetizacao__latam_2020s
    """).fetchone()[0]
    assert n_countries >= 10, f"Mart cobre apenas {n_countries} paises LATAM; minimo 10."


@pytest.mark.quality
def test_paises_harmonizados_includes_bra(con: duckdb.DuckDBPyConnection) -> None:
    """BRA precisa estar em paises_harmonizados (sem isso, todos os marts ficam vazios)."""
    has_bra = con.sql("""
        SELECT COUNT(*) FROM main_intermediate.int_geografia__paises_harmonizados
        WHERE country_iso3 = 'BRA'
    """).fetchone()[0]
    assert has_bra == 1, f"BRA nao encontrado em paises_harmonizados (count={has_bra})"


# ----------------------------------------------------------------------
# 4. Consistencia logica
# ----------------------------------------------------------------------


@pytest.mark.quality
def test_value_canonical_never_null_when_any_source_has_value(
    con: duckdb.DuckDBPyConnection,
) -> None:
    """Em mart_br_vs_ocde, value_canonical so pode ser NULL se WB e UIS forem ambos NULL."""
    bad_rows = con.sql("""
        SELECT COUNT(*) FROM main_marts.mart_br_vs_ocde__gasto_educacao_timeseries
        WHERE value_canonical IS NULL
          AND (value_worldbank IS NOT NULL OR value_unesco IS NOT NULL)
    """).fetchone()[0]
    assert bad_rows == 0, f"{bad_rows} linhas com value_canonical NULL apesar de WB/UIS != NULL"


@pytest.mark.quality
def test_rank_within_count_in_rankings_mart(con: duckdb.DuckDBPyConnection) -> None:
    """Em rankings_recente, rank_global deve estar entre 1 e countries_global."""
    bad_rows = con.sql("""
        SELECT COUNT(*) FROM main_marts.mart_indicadores__rankings_recente
        WHERE rank_global < 1 OR rank_global > countries_global
    """).fetchone()[0]
    assert bad_rows == 0, f"{bad_rows} linhas com rank_global fora de [1, countries_global]"


# ----------------------------------------------------------------------
# 5. Sanidade de derivados
# ----------------------------------------------------------------------


@pytest.mark.quality
def test_zscore_ranges_in_marts(con: duckdb.DuckDBPyConnection) -> None:
    """Z-scores em qualquer mart devem ficar dentro de [-5, 5] (ja imposto via dbt test, mas reforca)."""
    extreme_count = con.sql("""
        SELECT COUNT(*) FROM main_marts.mart_br_vs_ocde__gasto_educacao_timeseries
        WHERE zscore_in_oecd_year IS NOT NULL
          AND (zscore_in_oecd_year < -5 OR zscore_in_oecd_year > 5)
    """).fetchone()[0]
    assert extreme_count == 0, f"{extreme_count} z-scores fora de [-5, 5]"


@pytest.mark.quality
def test_trend_slope_within_realistic_range(con: duckdb.DuckDBPyConnection) -> None:
    """Slope de trend de gasto educacao % PIB deve ficar entre [-1, 1]/ano.

    Educacao % PIB nao varia drasticamente -- maior que 1pp/ano de
    crescimento sustentado e implausivel (gastaria 100% PIB em 100 anos).
    """
    slopes = con.sql("""
        SELECT MIN(trend_slope_full_period), MAX(trend_slope_full_period)
        FROM main_marts.mart_br_vs_ocde__gasto_educacao_timeseries
        WHERE trend_slope_full_period IS NOT NULL
    """).fetchone()
    min_slope, max_slope = slopes
    assert min_slope >= -1.0, f"Slope minimo {min_slope:.3f} < -1 (decrescimo implausivel)"
    assert max_slope <= 1.0, f"Slope maximo {max_slope:.3f} > 1 (crescimento implausivel)"
