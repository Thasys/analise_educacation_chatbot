"""Unit tests para a Fase B (avaliador externo + Cohen's kappa)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from evaluation.reports.external_evaluator_form import select_items
from evaluation.shared.import_external_eval import (
    cohens_kappa,
    compute_results,
)
from evaluation.shared.loader import load_golden

GOLDEN = Path(__file__).resolve().parents[2] / "evaluation" / "golden"


# ----------------------------------------------------------------------
# Cohen's kappa
# ----------------------------------------------------------------------


def test_kappa_concordancia_perfeita() -> None:
    """Concordancia perfeita com variancia => kappa = 1.0."""
    assert cohens_kappa([1, 1, 0, 0], [1, 1, 0, 0]) == pytest.approx(1.0)


def test_kappa_caso_conhecido() -> None:
    """po=0.7, pe=0.5 => kappa = 0.4."""
    a = [1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
    b = [1, 1, 1, 1, 0, 0, 0, 0, 1, 1]
    assert cohens_kappa(a, b) == pytest.approx(0.4, abs=1e-9)


def test_kappa_degenerado_sem_variancia() -> None:
    """Ambos avaliadores constantes e iguais => pe=1 => kappa NaN."""
    assert math.isnan(cohens_kappa([1, 1, 1], [1, 1, 1]))


def test_kappa_listas_vazias() -> None:
    assert math.isnan(cohens_kappa([], []))


def test_kappa_tamanhos_diferentes() -> None:
    assert math.isnan(cohens_kappa([1, 0], [1]))


# ----------------------------------------------------------------------
# compute_results
# ----------------------------------------------------------------------


def _eval_row(item_id: str, gabarito: str, repr_score: str = "5", comment: str = "") -> dict:
    return {
        "id": item_id,
        "gabarito_correto_sim_nao_incerto": gabarito,
        "representativa_1a5": repr_score,
        "comentario": comment,
    }


def test_compute_results_captura_discordancia() -> None:
    """Avaliador discorda de 1 item; autor afirma todos corretos."""
    rows = [
        _eval_row("F-015", "sim"),
        _eval_row("F-017", "sim"),
        _eval_row("C-001", "nao", comment="valor 2018 errado"),
    ]
    res = compute_results(rows)
    assert res["n_total"] == 3
    assert res["n_paired"] == 3
    assert res["observed_agreement"] == pytest.approx(2 / 3, abs=1e-4)
    divs = [d for d in res["divergences"] if d["kind"] == "discordancia"]
    assert len(divs) == 1
    assert divs[0]["id"] == "C-001"
    assert divs[0]["comment"] == "valor 2018 errado"


def test_compute_results_exclui_incerto() -> None:
    rows = [
        _eval_row("F-015", "sim"),
        _eval_row("C-010", "incerto"),
    ]
    res = compute_results(rows)
    assert res["n_excluded_incerto"] == 1
    assert res["n_paired"] == 1


def test_compute_results_kappa_degenerado_quando_autor_constante() -> None:
    """Autor afirma todos 'sim' e avaliador concorda => sem variancia =>
    kappa degenerado, mas concordancia observada = 1.0."""
    rows = [_eval_row(f"X-{i}", "sim") for i in range(5)]
    res = compute_results(rows)
    assert res["kappa_degenerate"] is True
    assert res["cohens_kappa"] is None
    assert res["observed_agreement"] == pytest.approx(1.0)
    assert res["passes_threshold_075"] is False


def test_compute_results_representatividade_media() -> None:
    rows = [_eval_row("F-015", "sim", "4"), _eval_row("F-017", "sim", "5")]
    res = compute_results(rows)
    assert res["mean_representativeness_1a5"] == pytest.approx(4.5)


# ----------------------------------------------------------------------
# select_items (form generator)
# ----------------------------------------------------------------------


def test_select_items_5_inscope_mais_5_adversariais() -> None:
    golden = load_golden(GOLDEN)
    items = select_items(golden)
    assert len(items) == 10
    kinds = [it.kind for it in items]
    assert kinds.count("adversarial") == 5
    # 5 in-scope sao factuais ou comparativos
    assert sum(k in ("factual", "comparative") for k in kinds) == 5


def test_select_items_categorias_adversariais_distintas() -> None:
    golden = load_golden(GOLDEN)
    items = select_items(golden)
    adv_cats = [it.category for it in items if it.kind == "adversarial"]
    assert len(set(adv_cats)) == 5  # todas distintas
