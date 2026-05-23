"""Unit tests para `evaluation.reports.statistical_analysis`.

Cada funcao tem >=1 caso feliz + >=1 caso adversarial/degenerado,
conforme exigido pela Fase A.2 do prompt
`docs/evaluation/prompt-analises-pos-resultados.md`.
"""

from __future__ import annotations

import math

import pytest

from evaluation.reports.statistical_analysis import (
    bootstrap_accuracy_ci,
    cliffs_delta,
    cohens_h,
    intra_class_correlation,
    mcnemar_paired,
)


def _items(classifications: list[str], prefix: str = "X") -> list[dict]:
    """Constroi items minimos com id sequencial + classification."""
    return [
        {"id": f"{prefix}-{i:03d}", "classification": c}
        for i, c in enumerate(classifications)
    ]


# ----------------------------------------------------------------------
# McNemar
# ----------------------------------------------------------------------


def test_mcnemar_caso_feliz_10_melhoras() -> None:
    """10 transicoes H->C, 0 C->H => fortemente significativo (p < 0.005)."""
    baseline = _items(["hallucinated"] * 10)
    eduquery = _items(["correct"] * 10)
    res = mcnemar_paired(baseline, eduquery)
    assert res.n_b == 10
    assert res.n_c == 0
    assert res.p_exact < 0.005
    assert res.p_value < 0.005


def test_mcnemar_adversarial_sem_discordancia() -> None:
    """Nenhum par discordante => teste degenera, p = 1.0, chi2 = 0."""
    baseline = _items(["correct", "hallucinated", "correct"])
    eduquery = _items(["correct", "hallucinated", "correct"])
    res = mcnemar_paired(baseline, eduquery)
    assert res.n_b == 0
    assert res.n_c == 0
    assert res.n_discordant == 0
    assert res.p_value == 1.0
    assert res.p_exact == 1.0
    assert res.chi2 == 0.0


def test_mcnemar_borderline_5_0() -> None:
    """5 melhoras / 0 regressoes => p_exact == 0.0625 (NAO significativo).

    Replica o caso real in-scope (n=10). Documenta honestamente que o
    teste e borderline com n pequeno.
    """
    baseline = _items(["hallucinated"] * 5 + ["correct"] * 5)
    eduquery = _items(["correct"] * 5 + ["correct"] * 5)
    res = mcnemar_paired(baseline, eduquery)
    assert res.n_b == 5
    assert res.n_c == 0
    assert res.p_exact == pytest.approx(0.0625, abs=1e-4)
    assert res.p_exact >= 0.05  # borderline: nao significativo a 0.05


def test_mcnemar_conta_regressoes() -> None:
    """Distingue melhoras (n_b) de regressoes (n_c)."""
    baseline = _items(["hallucinated", "hallucinated", "correct"])
    eduquery = _items(["correct", "hallucinated", "hallucinated"])
    res = mcnemar_paired(baseline, eduquery)
    assert res.n_b == 1  # item 0: H->C
    assert res.n_c == 1  # item 2: C->H


def test_mcnemar_pareia_por_id_ignora_faltantes() -> None:
    """Itens sem par nos dois lados sao ignorados."""
    baseline = _items(["hallucinated", "hallucinated"], prefix="A")
    eduquery = _items(["correct", "correct"], prefix="B")  # ids diferentes
    res = mcnemar_paired(baseline, eduquery)
    assert res.n_discordant == 0


def test_mcnemar_subset_por_ids() -> None:
    """O argumento `ids` restringe o conjunto pareado."""
    baseline = _items(["hallucinated", "hallucinated", "hallucinated"])
    eduquery = _items(["correct", "correct", "correct"])
    res = mcnemar_paired(baseline, eduquery, ids=["X-000", "X-001"])
    assert res.n_b == 2


# ----------------------------------------------------------------------
# Bootstrap
# ----------------------------------------------------------------------


def test_bootstrap_caso_feliz_ic_contem_valor_real() -> None:
    """60 corretos / 40 errados => media ~0.6 e IC contem 0.6."""
    items = _items(["correct"] * 60 + ["hallucinated"] * 40)
    res = bootstrap_accuracy_ci(items)
    assert res.mean == pytest.approx(0.6, abs=1e-9)
    assert res.lower <= 0.6 <= res.upper
    assert res.n == 100


def test_bootstrap_adversarial_lista_vazia() -> None:
    """Lista vazia retorna (0, 0, 0, 0) sem crash."""
    res = bootstrap_accuracy_ci([])
    assert res == (0.0, 0.0, 0.0, 0)


def test_bootstrap_reprodutivel_com_seed() -> None:
    """Mesma seed => mesmo IC (reprodutibilidade)."""
    items = _items(["correct"] * 7 + ["hallucinated"] * 3)
    a = bootstrap_accuracy_ci(items, seed=42)
    b = bootstrap_accuracy_ci(items, seed=42)
    assert a == b


def test_bootstrap_todos_corretos() -> None:
    """100% corretos => media 1.0, IC degenera em [1, 1]."""
    res = bootstrap_accuracy_ci(_items(["correct"] * 10))
    assert res.mean == 1.0
    assert res.lower == 1.0
    assert res.upper == 1.0


# ----------------------------------------------------------------------
# Cohen's h
# ----------------------------------------------------------------------


def test_cohens_h_zero_quando_iguais() -> None:
    assert cohens_h(0.5, 0.5) == pytest.approx(0.0, abs=1e-12)


def test_cohens_h_valor_grande() -> None:
    """cohens_h(0.10, 0.633) ~ 1.19 (efeito grande)."""
    assert cohens_h(0.10, 0.633) == pytest.approx(1.197, abs=0.02)


def test_cohens_h_simetrico_em_modulo() -> None:
    assert cohens_h(0.1, 0.6) == pytest.approx(cohens_h(0.6, 0.1), abs=1e-12)


# ----------------------------------------------------------------------
# Cliff's delta
# ----------------------------------------------------------------------


def test_cliffs_delta_dominancia_total() -> None:
    """group2 sempre maior que group1 => delta = 1.0."""
    assert cliffs_delta([0, 0, 0], [1, 1, 1]) == pytest.approx(1.0)


def test_cliffs_delta_grupos_iguais() -> None:
    """Distribuicoes identicas => delta = 0."""
    assert cliffs_delta([1, 0, 1], [1, 0, 1]) == pytest.approx(0.0)


def test_cliffs_delta_grupo_vazio() -> None:
    assert cliffs_delta([], [1, 2, 3]) == 0.0


# ----------------------------------------------------------------------
# ICC
# ----------------------------------------------------------------------


def test_icc_concordancia_perfeita_com_variancia_entre_itens() -> None:
    """Itens distintos, repeticoes identicas => ICC = 1.0 (confiabilidade
    maxima)."""
    matrix = [[1, 1, 1], [0, 0, 0], [1, 1, 1], [0, 0, 0]]
    assert intra_class_correlation(matrix) == pytest.approx(1.0, abs=1e-9)


def test_icc_alta_com_uma_discordancia() -> None:
    """Caso real n=3: maioria consistente, 2 itens com 1 voto divergente
    => ICC ~ 0.74 (bom)."""
    matrix = [
        [1, 1, 0], [1, 1, 0], [1, 1, 1], [1, 1, 1], [0, 0, 0],
        [1, 1, 1], [0, 0, 0], [1, 1, 1], [0, 0, 0], [1, 1, 1],
    ]
    icc = intra_class_correlation(matrix)
    assert 0.65 < icc < 0.85


def test_icc_degenerado_poucos_itens() -> None:
    """Menos de 2 itens ou 2 raters => 0.0 sem crash."""
    assert intra_class_correlation([[1, 1, 1]]) == 0.0
    assert intra_class_correlation([]) == 0.0
