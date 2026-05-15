"""Testes do MP4 fact-check (apos quality-assessment 2026-05-14).

Foco no helper deterministico `check_numeric_consistency` /
`run_fact_check`. Testes do retry do Synthesizer ficam no
`test_visualizer_synthesizer.py` (precisam de mock_llm_call).
"""

from __future__ import annotations

from src.crews._helpers import check_numeric_consistency, run_fact_check
from src.schemas import RetrievedData


# ---------------------------------------------------------------------------
# check_numeric_consistency
# ---------------------------------------------------------------------------


def test_passes_when_numbers_match_within_tolerance():
    md = "Brasil investiu 5.77% do PIB em 2020, vs Finlandia 6.68%."
    rows = [
        {"country_iso3": "BRA", "value": 5.77},
        {"country_iso3": "FIN", "value": 6.68},
    ]
    ok, unmatched = check_numeric_consistency(md, rows)
    assert ok is True
    assert unmatched == []


def test_passes_with_5pct_rounding():
    # 5.8 vs 5.77 = 0.5% off, dentro da tolerancia de 5%.
    md = "Brasil investiu cerca de 5.8 do PIB."
    rows = [{"country_iso3": "BRA", "value": 5.77}]
    ok, _ = check_numeric_consistency(md, rows)
    assert ok is True


def test_fails_when_most_numbers_diverge():
    # Markdown muito alucinado — todos os numeros >>5% off dos reais.
    md = "Brasil 8.0%, Finlandia 9.5%, Mexico 7.2%."
    rows = [
        {"country_iso3": "BRA", "value": 5.77},
        {"country_iso3": "FIN", "value": 6.68},
        {"country_iso3": "MEX", "value": 4.50},
    ]
    ok, unmatched = check_numeric_consistency(md, rows)
    assert ok is False
    assert len(unmatched) == 3


def test_filters_years_from_numbers():
    md = "Em 2020, Brasil investiu 5.77% do PIB."
    rows = [{"country_iso3": "BRA", "value": 5.77}]
    ok, unmatched = check_numeric_consistency(md, rows)
    # "2020" nao deve ser considerado um valor a validar
    assert ok is True
    assert unmatched == []


def test_passes_with_no_numbers_in_markdown():
    md = "O Brasil esta abaixo da media OCDE, com base nos dados do World Bank."
    rows = [{"country_iso3": "BRA", "value": 5.77}]
    ok, unmatched = check_numeric_consistency(md, rows)
    assert ok is True
    assert unmatched == []


def test_passes_with_empty_primary_data():
    md = "Brasil 5.77%."
    ok, _ = check_numeric_consistency(md, None)
    assert ok is True  # sem referencia, nao da pra falsificar


def test_uses_primary_meta_zscore():
    md = "Brasil esta 0.6 sigma acima da media OCDE."
    rows = [{"country_iso3": "BRA", "value": 5.77}]
    meta = {"zscore_in_oecd": 0.606, "percentile_in_oecd": 0.818}
    ok, _ = check_numeric_consistency(md, rows, primary_meta=meta)
    assert ok is True


def test_uses_primary_meta_percentile():
    md = "Brasil aparece no percentil 82 da OCDE."
    rows = [{"country_iso3": "BRA", "value": 5.77}]
    meta = {"percentile_in_oecd": 0.818}
    # Markdown diz "82" ~ 0.818 * 100. _matches testa variants /100 e *100.
    ok, _ = check_numeric_consistency(md, rows, primary_meta=meta)
    assert ok is True


def test_uses_comparison_stats():
    md = "A media foi 5.65 com mediana 5.7."
    meta = {
        "comparison_stats": {"mean": 5.645, "median": 5.7, "min": 4.5, "max": 6.68}
    }
    ok, _ = check_numeric_consistency(md, primary_data=[], primary_meta=meta)
    assert ok is True


# ---------------------------------------------------------------------------
# run_fact_check (wrapper que aceita RetrievedData)
# ---------------------------------------------------------------------------


def test_run_fact_check_accepts_retrieved_data():
    retrieved = RetrievedData(
        summary="Compare 3 paises gasto educ 2020",
        primary_data=[
            {"country_iso3": "BRA", "value": 5.77},
            {"country_iso3": "FIN", "value": 6.68},
        ],
        primary_meta={"zscore_in_oecd": 0.606},
    )
    md = "Brasil 5.77%, Finlandia 6.68%, z-score 0.6 acima da media."
    ok, unmatched = run_fact_check(md, retrieved)
    assert ok is True
    assert unmatched == []


def test_run_fact_check_flags_hallucinated_numbers():
    retrieved = RetrievedData(
        summary="...",
        primary_data=[
            {"country_iso3": "BRA", "value": 5.77},
            {"country_iso3": "FIN", "value": 6.68},
            {"country_iso3": "MEX", "value": 4.50},
        ],
    )
    # Numeros que ficam fora da tolerancia de 5% para todos os refs.
    md = "Brasil 8.0%, Finlandia 9.5%, Mexico 7.2%."
    ok, divergences = run_fact_check(md, retrieved)
    assert ok is False
    assert len(divergences) == 3


def test_run_fact_check_empty_retrieved():
    retrieved = RetrievedData(summary="vazio")
    md = "Texto sem dados."
    ok, _ = run_fact_check(md, retrieved)
    assert ok is True
