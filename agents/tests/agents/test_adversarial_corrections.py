"""Fase C — testes das correcoes adversariais (A-022, A-011, A-014..016).

Cobre:
- `compute_divergence` (helper deterministico de cross_source_contradiction);
- os novos campos do schema StatAnalysis;
- a presenca das regras anti-injecao / divergencia / year_confusion nos
  prompts versionados (guarda contra remocao acidental).

A validacao comportamental fim-a-fim (LLM real) e feita pela re-execucao
da bateria em `eduquery_ablation_post.json` — ver
`docs/evaluation/ablation-correcoes-adversariais.md`.
"""

from __future__ import annotations

import pytest

from src.agents._prompt_loader import load_prompt
from src.schemas import StatAnalysis
from src.tools.stats_tools import ComputeStatsTool, compute_divergence


# ----------------------------------------------------------------------
# compute_divergence
# ----------------------------------------------------------------------


def test_divergence_detectada_acima_5pct() -> None:
    """Fontes 93,0 vs 94,4 vs 93,5 => dispersao ~1,5% (<5%, nao detecta)."""
    res = compute_divergence([93.0, 94.4, 93.5])
    assert res["n_sources"] == 3
    assert res["divergence_pct"] == pytest.approx((94.4 - 93.0) / 93.5, abs=1e-4)
    assert res["divergence_detected"] is False


def test_divergence_grande_detectada() -> None:
    """5,0 vs 7,0 (mediana 6,0) => 33% > 5% => detecta."""
    res = compute_divergence([5.0, 7.0, 6.0])
    assert res["divergence_detected"] is True
    assert res["divergence_pct"] == pytest.approx(2.0 / 6.0, abs=1e-4)


def test_divergence_fontes_convergem() -> None:
    """Mesmo valor de duas fontes (A-014) => sem divergencia."""
    res = compute_divergence([5.5, 5.5])
    assert res["divergence_detected"] is False
    assert res["divergence_pct"] == 0.0


def test_divergence_uma_unica_fonte() -> None:
    res = compute_divergence([5.5])
    assert res["divergence_detected"] is False
    assert res["n_sources"] == 1


def test_divergence_mediana_zero_nao_crasha() -> None:
    res = compute_divergence([-1.0, 1.0])  # mediana 0
    assert res["divergence_detected"] is False
    assert res["divergence_pct"] == 0.0


def test_compute_stats_tool_inclui_divergence() -> None:
    """A tool expoe 'divergence' quando source_values e passado."""
    import json

    out = json.loads(
        ComputeStatsTool()._run(values=[5.5], source_values=[5.0, 7.0, 6.0])
    )
    assert out["divergence"]["divergence_detected"] is True


# ----------------------------------------------------------------------
# Schema StatAnalysis — novos campos
# ----------------------------------------------------------------------


def test_statanalysis_aceita_campos_divergencia() -> None:
    sa = StatAnalysis(sample_size=2, divergence_detected=True, divergence_pct=0.33)
    assert sa.divergence_detected is True
    assert sa.divergence_pct == pytest.approx(0.33)


def test_statanalysis_default_sem_divergencia() -> None:
    sa = StatAnalysis(sample_size=5)
    assert sa.divergence_detected is False
    assert sa.divergence_pct is None


# ----------------------------------------------------------------------
# Guardas de prompt (anti-injecao / divergencia / year_confusion)
# ----------------------------------------------------------------------


def test_orchestrator_prompt_tem_regra_anti_injecao() -> None:
    p = load_prompt("orchestrator_system").lower()
    assert "anti-injecao" in p or "anti-injeção" in p
    assert "conhecimento geral" in p


def test_synthesizer_prompt_recusa_injecao() -> None:
    p = load_prompt("synthesizer_system").lower()
    assert "anti-injecao" in p or "anti-injeção" in p
    assert "marts gold" in p
    # deve instruir a reportar divergencia tambem
    assert "divergence_detected" in p


def test_statistician_prompt_tem_divergencia_e_year_confusion() -> None:
    p = load_prompt("statistician_system").lower()
    assert "divergence_pct" in p
    assert "divergence_detected" in p
    assert "year_confusion" in p
