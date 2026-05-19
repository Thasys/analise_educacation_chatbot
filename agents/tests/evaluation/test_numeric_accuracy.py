"""Unit tests para `evaluation.metrics.numeric_accuracy`."""

from __future__ import annotations

import pytest

from evaluation.metrics.numeric_accuracy import NumericResult, aggregate_accuracy


# ----------------------------------------------------------------------
# Caso feliz
# ----------------------------------------------------------------------


def test_dentro_da_tolerancia_padrao_5pct() -> None:
    """PISA 2022 Brasil: esperado 379, sistema responde 380 (0.26%)."""
    nr = NumericResult(expected=379, actual=380, tolerance_pct=5)
    assert nr.within_tolerance is True
    assert nr.relative_error is not None
    assert nr.relative_error == pytest.approx(1 / 379, rel=1e-6)


def test_borda_tolerancia_exata() -> None:
    """Erro relativo == tolerancia: e considerado dentro."""
    nr = NumericResult(expected=100, actual=105, tolerance_pct=5)
    assert nr.within_tolerance is True


def test_aggregate_metrics_basicas() -> None:
    results = [
        NumericResult(expected=379, actual=380, tolerance_pct=5),  # ok
        NumericResult(expected=100, actual=120, tolerance_pct=5),  # nok
        NumericResult(expected=50, actual=49.5, tolerance_pct=5),  # ok
    ]
    agg = aggregate_accuracy(results)
    assert agg["n"] == 3
    assert agg["n_correct"] == 2
    assert agg["accuracy"] == pytest.approx(2 / 3)
    # mean_rel_err deve ser > 0
    assert agg["mean_rel_err"] > 0


# ----------------------------------------------------------------------
# Casos adversariais
# ----------------------------------------------------------------------


def test_actual_none_falha() -> None:
    """Sem numero extraido da resposta, classificacao deve falhar."""
    nr = NumericResult(expected=379, actual=None, tolerance_pct=5)
    assert nr.within_tolerance is False
    assert nr.relative_error is None


def test_valor_fora_da_tolerancia() -> None:
    """Sistema alucinou 450 pts no PISA Math; gabarito 379."""
    nr = NumericResult(expected=379, actual=450, tolerance_pct=5)
    assert nr.within_tolerance is False
    assert nr.relative_error is not None and nr.relative_error > 0.05


def test_expected_zero_caso_de_borda() -> None:
    """Quando expected eh 0, comparamos absoluto contra tolerance_pct/100."""
    nr_ok = NumericResult(expected=0, actual=0.04, tolerance_pct=5)  # 0.04 <= 0.05
    nr_nok = NumericResult(expected=0, actual=1, tolerance_pct=5)
    assert nr_ok.within_tolerance is True
    assert nr_nok.within_tolerance is False
    # relative_error e indefinido quando expected=0
    assert nr_ok.relative_error is None


def test_aggregate_vazio() -> None:
    """Lista vazia nao deve quebrar."""
    agg = aggregate_accuracy([])
    assert agg == {"n": 0, "n_correct": 0, "accuracy": 0.0, "mean_rel_err": 0.0}


def test_valor_negativo_simetrico() -> None:
    """Sinal nao deve confundir a tolerancia (abs)."""
    nr = NumericResult(expected=-100, actual=-104, tolerance_pct=5)
    assert nr.within_tolerance is True
