"""Unit tests para `evaluation.metrics.guardrails_efficacy` — TIA e FP."""

from __future__ import annotations

import pytest

from evaluation.metrics.guardrails_efficacy import (
    QueryResult,
    compute_false_positive_rate,
    compute_guardrail_summary,
    compute_tia,
)
from evaluation.metrics.hallucination_classifier import Classification


# Helpers
def H(id_: str) -> QueryResult:
    return QueryResult(id=id_, classification=Classification.HALLUCINATED)


def B(id_: str) -> QueryResult:
    return QueryResult(id=id_, classification=Classification.BLOCKED)


def C(id_: str) -> QueryResult:
    return QueryResult(id=id_, classification=Classification.CORRECT)


# ----------------------------------------------------------------------
# Caso feliz — TIA
# ----------------------------------------------------------------------


def test_tia_perfeita_todos_interceptados() -> None:
    """Baseline alucina 3 itens; EduQuery bloqueia exatamente esses 3 -> TIA=1."""
    baseline = [H("Q1"), H("Q2"), H("Q3"), C("Q4")]
    eduquery = [B("Q1"), B("Q2"), B("Q3"), C("Q4")]
    assert compute_tia(baseline, eduquery) == 1.0


def test_tia_parcial() -> None:
    """3 alucinacoes no baseline; EduQuery bloqueia 2 -> TIA = 2/3."""
    baseline = [H("Q1"), H("Q2"), H("Q3")]
    eduquery = [B("Q1"), B("Q2"), H("Q3")]
    assert compute_tia(baseline, eduquery) == pytest.approx(2 / 3)


# ----------------------------------------------------------------------
# Casos adversariais — TIA
# ----------------------------------------------------------------------


def test_tia_zero_quando_baseline_nao_aluciona() -> None:
    """Nenhuma alucinacao no baseline -> denominador zero; convencao: TIA=0."""
    baseline = [C("Q1"), C("Q2")]
    eduquery = [C("Q1"), C("Q2")]
    assert compute_tia(baseline, eduquery) == 0.0


def test_tia_so_conta_intersecao_e_nao_bloqueios_aleatorios() -> None:
    """Bloquear itens corretos NAO conta como interceptacao."""
    baseline = [H("Q1"), C("Q2")]
    eduquery = [B("Q1"), B("Q2")]  # bloqueia tambem Q2, que era correto
    # Intersecao(H_baseline={Q1}, B_eduquery={Q1,Q2}) = {Q1}
    # TIA = 1/1 = 1.0
    assert compute_tia(baseline, eduquery) == 1.0


def test_tia_ignora_ids_nao_correspondentes() -> None:
    """Set-based: Q3 esta em ambos mas com classificacoes neutras."""
    baseline = [H("Q1"), H("Q2"), C("Q3")]
    eduquery = [B("Q9"), B("Q1"), C("Q3")]  # bloqueia Q1 e Q9 (que nao alucinou no baseline)
    # H_baseline = {Q1, Q2}; B_eduquery = {Q1, Q9}
    # intersect = {Q1}; TIA = 1/2 = 0.5
    assert compute_tia(baseline, eduquery) == 0.5


# ----------------------------------------------------------------------
# Falsos positivos
# ----------------------------------------------------------------------


def test_fp_rate_zero_quando_sem_bloqueio_indevido() -> None:
    baseline = [C("Q1"), C("Q2"), H("Q3")]
    eduquery = [C("Q1"), C("Q2"), B("Q3")]
    assert compute_false_positive_rate(baseline, eduquery) == 0.0


def test_fp_rate_alto_quando_guardrail_excessivo() -> None:
    """4 itens corretos no baseline; EduQuery bloqueia 2 deles -> FP=0.5."""
    baseline = [C("Q1"), C("Q2"), C("Q3"), C("Q4")]
    eduquery = [B("Q1"), B("Q2"), C("Q3"), C("Q4")]
    assert compute_false_positive_rate(baseline, eduquery) == 0.5


def test_fp_zero_quando_baseline_nao_tem_correct() -> None:
    """Caso degenerado: nada para falsamente bloquear."""
    baseline = [H("Q1"), H("Q2")]
    eduquery = [B("Q1"), B("Q2")]
    assert compute_false_positive_rate(baseline, eduquery) == 0.0


# ----------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------


def test_summary_estrutura_e_contagens() -> None:
    baseline = [H("Q1"), H("Q2"), C("Q3"), C("Q4")]
    eduquery = [B("Q1"), B("Q2"), C("Q3"), B("Q4")]  # interceptou as 2 + 1 FP
    summary = compute_guardrail_summary(baseline, eduquery)
    assert summary["baseline"]["hallucinated"] == 2
    assert summary["baseline"]["correct"] == 2
    assert summary["eduquery"]["blocked"] == 3
    assert summary["tia"] == 1.0  # 2/2
    assert summary["false_positive_rate"] == 0.5  # 1/2
