"""Analise estatistica inferencial dos resultados da bateria EduQuery.

Computa, de forma 100% deterministica sobre os JSONs ja existentes
(custo $0, sem invocar LLM):

- McNemar pareado (baseline vs EduQuery) — significancia da diferenca
  de acuracia. Reporta chi-quadrado com correcao de continuidade *e* o
  p-valor exato binomial (mais apropriado quando o numero de pares
  discordantes e pequeno).
- Bootstrap IC 95% (5.000 reamostragens) sobre a acuracia in-scope.
- Tamanho de efeito: Cohen's h e Cliff's delta.
- ICC(2,1) entre as repeticoes (n=3) — confiabilidade do classifier.

Decisao metodologica (honestidade > narrativa, ver regra #2 do prompt
`prompt-analises-pos-resultados.md`): reportamos McNemar em tres
recortes, sem cherry-picking:

1. **in-scope (n=10)** — recorte do claim principal (10% -> 60%).
   Subpotente: com 5 pares discordantes todos a favor do EduQuery
   (b=5, c=0), o p-valor exato e 0.0625 — *borderline*, nao
   significativo a alfa=0.05. Honesto reportar.
2. **numeric (n=54)** — todos os factuais+comparativos. Mais poder
   estatistico; a diferenca e fortemente significativa.
3. **in-scope com voto majoritario n=3** — usa a medida mais
   confiavel (3 repeticoes) do EduQuery vs baseline n=1.

scipy nao possui `mcnemar` nativo (ao contrario do que sugere o prompt;
`scipy.stats.contingency.mcnemar` nao existe). Implementamos o teste
diretamente com `scipy.stats.chi2` (continuidade) e `scipy.stats.binomtest`
(exato), evitando a dependencia extra de statsmodels.

CLI:

    python -m evaluation.reports.statistical_analysis \\
        --baseline evaluation/output/baseline_official.json \\
        --eduquery evaluation/output/eduquery_official_tcc.json \\
        --n3 evaluation/output/eduquery_n3.json \\
        --llm-direct evaluation/output/llm_direct.json \\
        --output evaluation/output/statistical_analysis.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, NamedTuple, Sequence

import numpy as np
from scipy.stats import binomtest, chi2 as chi2_dist

# Os 10 itens in-scope (cobertos pelos marts atuais GASTO_EDU_PIB e
# LITERACY_15M). Coincidem com os itens do run llm_direct (Acao #4).
IN_SCOPE_IDS: tuple[str, ...] = (
    "F-015", "F-016", "F-017", "F-018", "F-032",
    "C-001", "C-005", "C-010", "C-011", "C-017",
)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _is_correct(item: dict[str, Any]) -> bool:
    """Um item conta como acerto quando classification == 'correct'."""
    return item.get("classification") == "correct"


def _index_by_id(items: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {it["id"]: it for it in items}


def _accuracy(items: Sequence[dict[str, Any]]) -> float:
    if not items:
        return 0.0
    return sum(_is_correct(it) for it in items) / len(items)


# ----------------------------------------------------------------------
# McNemar pareado
# ----------------------------------------------------------------------


class McNemarResult(NamedTuple):
    chi2: float
    p_value: float       # p continuidade-corrigido (chi-quadrado)
    n_b: int             # pares baseline-errado -> eduquery-certo
    n_c: int             # pares baseline-certo -> eduquery-errado
    p_exact: float       # p exato binomial (two-sided)
    n_discordant: int


def mcnemar_paired(
    baseline_items: Sequence[dict[str, Any]],
    eduquery_items: Sequence[dict[str, Any]],
    ids: Sequence[str] | None = None,
) -> McNemarResult:
    """McNemar pareado por `id`.

    Conta as transicoes discordantes:
      - n_b = baseline ERROU e eduquery ACERTOU (melhora)
      - n_c = baseline ACERTOU e eduquery ERROU  (regressao)

    Retorna chi-quadrado com correcao de continuidade de Yates e o
    p-valor exato binomial (preferivel para n_discordant pequeno).
    Caso degenerado (nenhum par discordante): chi2=0, p=1.0.
    """
    base = _index_by_id(baseline_items)
    edu = _index_by_id(eduquery_items)
    keys = list(ids) if ids is not None else [k for k in base if k in edu]

    n_b = n_c = 0
    for k in keys:
        if k not in base or k not in edu:
            continue
        b_ok = _is_correct(base[k])
        e_ok = _is_correct(edu[k])
        if (not b_ok) and e_ok:
            n_b += 1
        elif b_ok and (not e_ok):
            n_c += 1

    n = n_b + n_c
    if n == 0:
        return McNemarResult(0.0, 1.0, n_b, n_c, 1.0, 0)

    chi2 = (abs(n_b - n_c) - 1) ** 2 / n  # correcao de continuidade
    p_chi = float(chi2_dist.sf(chi2, 1))
    p_exact = float(binomtest(min(n_b, n_c), n, 0.5).pvalue)
    return McNemarResult(float(chi2), p_chi, n_b, n_c, p_exact, n)


# ----------------------------------------------------------------------
# Bootstrap IC 95%
# ----------------------------------------------------------------------


class BootstrapCI(NamedTuple):
    mean: float
    lower: float
    upper: float
    n: int


def bootstrap_accuracy_ci(
    items: Sequence[dict[str, Any]],
    *,
    n_resamples: int = 5000,
    confidence: float = 0.95,
    seed: int = 42,
) -> BootstrapCI:
    """IC bootstrap percentil para a acuracia (fracao de 'correct').

    Reamostragem com reposicao das observacoes binarias item-a-item.
    `numpy.random.default_rng(seed)` garante reprodutibilidade.
    Lista vazia retorna (0, 0, 0, 0) sem crashar.
    """
    if not items:
        return BootstrapCI(0.0, 0.0, 0.0, 0)

    hits = np.array([1.0 if _is_correct(it) else 0.0 for it in items])
    n = len(hits)
    rng = np.random.default_rng(seed)
    # matriz (n_resamples x n) de indices reamostrados
    idx = rng.integers(0, n, size=(n_resamples, n))
    means = hits[idx].mean(axis=1)
    alpha = 1.0 - confidence
    lower = float(np.quantile(means, alpha / 2))
    upper = float(np.quantile(means, 1 - alpha / 2))
    return BootstrapCI(float(hits.mean()), lower, upper, n)


# ----------------------------------------------------------------------
# Tamanhos de efeito
# ----------------------------------------------------------------------


def cohens_h(p1: float, p2: float) -> float:
    """Cohen's h para diferenca entre duas proporcoes.

    h = |2*arcsin(sqrt(p2)) - 2*arcsin(sqrt(p1))|.
    Convencao: 0.2 pequeno, 0.5 medio, 0.8 grande.
    """
    phi1 = 2 * math.asin(math.sqrt(p1))
    phi2 = 2 * math.asin(math.sqrt(p2))
    return abs(phi2 - phi1)


def cliffs_delta(group1: Sequence[float], group2: Sequence[float]) -> float:
    """Cliff's delta nao-parametrico entre dois grupos.

    delta = ( #(g2 > g1) - #(g1 > g2) ) / (n1 * n2).
    Varia de -1 a 1. Sinal positivo => group2 tende a ser maior.
    Grupos vazios retornam 0.0.
    """
    n1, n2 = len(group1), len(group2)
    if n1 == 0 or n2 == 0:
        return 0.0
    greater = lesser = 0
    for a in group2:
        for b in group1:
            if a > b:
                greater += 1
            elif a < b:
                lesser += 1
    return (greater - lesser) / (n1 * n2)


# ----------------------------------------------------------------------
# ICC entre repeticoes (n=3)
# ----------------------------------------------------------------------


def intra_class_correlation(repetitions: Sequence[Sequence[float]]) -> float:
    """ICC(2,1): two-way random effects, single rater, absolute agreement.

    `repetitions` e uma matriz n_itens x k_repeticoes (valores binarios
    0/1 = hallucinated/correct, ou continuos). Mede a confiabilidade do
    classifier entre as k repeticoes.

    Retorna 0.0 para entradas degeneradas (variancia total nula => nada
    a explicar, ou < 2 itens / < 2 raters).
    """
    x = np.asarray(repetitions, dtype=float)
    if x.ndim != 2 or x.shape[0] < 2 or x.shape[1] < 2:
        return 0.0

    n, k = x.shape
    grand = x.mean()
    ss_total = ((x - grand) ** 2).sum()
    if ss_total == 0:
        # Concordancia perfeita e sem variancia entre itens: classifier
        # determinou tudo igual; ICC indefinido -> reportamos 1.0.
        return 1.0

    row_means = x.mean(axis=1)
    col_means = x.mean(axis=0)
    ss_rows = k * ((row_means - grand) ** 2).sum()
    ss_cols = n * ((col_means - grand) ** 2).sum()
    ss_error = ss_total - ss_rows - ss_cols

    ms_rows = ss_rows / (n - 1)
    ms_cols = ss_cols / (k - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))

    denom = ms_rows + (k - 1) * ms_error + (k / n) * (ms_cols - ms_error)
    if denom == 0:
        return 0.0
    return float((ms_rows - ms_error) / denom)


# ----------------------------------------------------------------------
# Orquestracao + JSON estavel
# ----------------------------------------------------------------------


def _n3_matrix(n3_items: Sequence[dict[str, Any]]) -> tuple[list[list[float]], list[str]]:
    """Constroi a matriz itens x repeticoes (ordenada por repetition_idx)."""
    by_base: dict[str, dict[int, float]] = defaultdict(dict)
    for it in n3_items:
        base = it.get("base_id", it["id"])
        rep = int(it.get("repetition_idx", 1))
        by_base[base][rep] = 1.0 if _is_correct(it) else 0.0
    base_ids = sorted(by_base)
    matrix: list[list[float]] = []
    for b in base_ids:
        reps = sorted(by_base[b])
        matrix.append([by_base[b][r] for r in reps])
    return matrix, base_ids


def _n3_majority(n3_items: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Voto majoritario por base_id -> item sintetico com classification."""
    by_base: dict[str, list[bool]] = defaultdict(list)
    for it in n3_items:
        by_base[it.get("base_id", it["id"])].append(_is_correct(it))
    out: dict[str, dict[str, Any]] = {}
    for b, votes in by_base.items():
        is_correct = sum(votes) > len(votes) / 2
        out[b] = {"id": b, "classification": "correct" if is_correct else "hallucinated"}
    return out


def compute_analysis(
    baseline: dict[str, Any],
    eduquery: dict[str, Any],
    n3: dict[str, Any] | None,
    llm_direct: dict[str, Any] | None,
) -> dict[str, Any]:
    b_items = baseline["items"]
    e_items = eduquery["items"]
    b_by_id = _index_by_id(b_items)
    e_by_id = _index_by_id(e_items)

    inscope_present = [k for k in IN_SCOPE_IDS if k in b_by_id and k in e_by_id]
    numeric_ids = [
        it["id"] for it in b_items if it.get("kind") in ("factual", "comparative")
    ]

    # --- McNemar nos tres recortes ---
    mc_inscope = mcnemar_paired(b_items, e_items, ids=inscope_present)
    mc_numeric = mcnemar_paired(b_items, e_items, ids=numeric_ids)

    result: dict[str, Any] = {}

    # --- Bootstrap in-scope ---
    baseline_inscope = [b_by_id[k] for k in inscope_present]
    eduquery_inscope = [e_by_id[k] for k in inscope_present]
    boot_base = bootstrap_accuracy_ci(baseline_inscope)

    # EduQuery in-scope: preferimos a medida mais confiavel (n=3) quando
    # disponivel; senao usamos o run unico.
    if n3 is not None:
        boot_edu = bootstrap_accuracy_ci(n3["items"])
        edu_inscope_acc = boot_edu.mean
        edu_source = "n3"
    else:
        boot_edu = bootstrap_accuracy_ci(eduquery_inscope)
        edu_inscope_acc = boot_edu.mean
        edu_source = "single_run"

    result["mcnemar_in_scope"] = {
        "chi2": round(mc_inscope.chi2, 4),
        "p_value": round(mc_inscope.p_value, 4),
        "p_exact": round(mc_inscope.p_exact, 4),
        "n_b": mc_inscope.n_b,
        "n_c": mc_inscope.n_c,
        "n_discordant": mc_inscope.n_discordant,
        "n_items": len(inscope_present),
        "significant_at_05": mc_inscope.p_exact < 0.05,
    }
    result["mcnemar_numeric"] = {
        "chi2": round(mc_numeric.chi2, 4),
        "p_value": round(mc_numeric.p_value, 4),
        "p_exact": round(mc_numeric.p_exact, 4),
        "n_b": mc_numeric.n_b,
        "n_c": mc_numeric.n_c,
        "n_discordant": mc_numeric.n_discordant,
        "n_items": len(numeric_ids),
        "significant_at_05": mc_numeric.p_exact < 0.05,
    }

    # --- McNemar in-scope com voto majoritario n=3 ---
    if n3 is not None:
        maj = _n3_majority(n3["items"])
        maj_ids = [k for k in inscope_present if k in maj]
        mc_maj = mcnemar_paired(
            [b_by_id[k] for k in maj_ids],
            [maj[k] for k in maj_ids],
            ids=maj_ids,
        )
        result["mcnemar_in_scope_n3_majority"] = {
            "chi2": round(mc_maj.chi2, 4),
            "p_value": round(mc_maj.p_value, 4),
            "p_exact": round(mc_maj.p_exact, 4),
            "n_b": mc_maj.n_b,
            "n_c": mc_maj.n_c,
            "n_discordant": mc_maj.n_discordant,
            "n_items": len(maj_ids),
            "significant_at_05": mc_maj.p_exact < 0.05,
        }

    result["bootstrap_baseline_in_scope"] = {
        "mean": round(boot_base.mean, 4),
        "lower": round(boot_base.lower, 4),
        "upper": round(boot_base.upper, 4),
        "n": boot_base.n,
    }
    result["bootstrap_eduquery_in_scope"] = {
        "mean": round(boot_edu.mean, 4),
        "lower": round(boot_edu.lower, 4),
        "upper": round(boot_edu.upper, 4),
        "n": boot_edu.n,
        "source": edu_source,
    }

    # --- Cohen's h (baseline in-scope vs eduquery in-scope) ---
    p_base = boot_base.mean
    result["cohens_h_baseline_vs_eduquery"] = round(cohens_h(p_base, edu_inscope_acc), 4)

    # --- Cliff's delta entre distribuicoes binarias in-scope ---
    g_base = [1.0 if _is_correct(b_by_id[k]) else 0.0 for k in inscope_present]
    g_edu = [1.0 if _is_correct(e_by_id[k]) else 0.0 for k in inscope_present]
    result["cliffs_delta"] = round(cliffs_delta(g_base, g_edu), 4)

    # --- ICC entre repeticoes n=3 ---
    if n3 is not None:
        matrix, _ = _n3_matrix(n3["items"])
        result["icc_n3"] = round(intra_class_correlation(matrix), 4)

    # --- LLM-direto (ancora) ---
    if llm_direct is not None:
        result["llm_direct_in_scope_accuracy"] = round(_accuracy(llm_direct["items"]), 4)

    # --- metadados ---
    result["_meta"] = {
        "in_scope_ids": inscope_present,
        "n_numeric": len(numeric_ids),
        "bootstrap_resamples": 5000,
        "bootstrap_seed": 42,
        "note": (
            "McNemar in-scope (n=10) e borderline (p_exact=0.0625): subpotente "
            "mas com todos os pares discordantes a favor do EduQuery (b>0, c=0). "
            "O recorte numeric (n=54) e fortemente significativo. Effect size "
            "(Cohen's h) grande. Reportar os tres recortes sem cherry-picking."
        ),
    }
    return result


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def generate(
    baseline_json: Path,
    eduquery_json: Path,
    output: Path,
    *,
    n3_json: Path | None = None,
    llm_direct_json: Path | None = None,
) -> dict[str, Any]:
    baseline = _load(baseline_json)
    eduquery = _load(eduquery_json)
    n3 = _load(n3_json) if n3_json and n3_json.exists() else None
    llm_direct = _load(llm_direct_json) if llm_direct_json and llm_direct_json.exists() else None
    analysis = compute_analysis(baseline, eduquery, n3, llm_direct)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    return analysis


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Analise estatistica inferencial dos resultados da bateria."
    )
    p.add_argument("--baseline", type=Path, required=True)
    p.add_argument("--eduquery", type=Path, required=True)
    p.add_argument("--n3", type=Path, default=None)
    p.add_argument("--llm-direct", type=Path, default=None)
    p.add_argument("--output", type=Path, required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    analysis = generate(
        args.baseline,
        args.eduquery,
        args.output,
        n3_json=args.n3,
        llm_direct_json=args.llm_direct,
    )
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
