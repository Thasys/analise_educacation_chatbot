"""Taxa de Interceptacao de Alucinacoes (TIA) e metricas de guardrails.

A TIA e a metrica principal do artigo SBIE 2026 / TPIE. Substitui o
placeholder `[X\\%]` no resumo. Definida como:

    TIA = |H_baseline INTERSECT B_eduquery| / |H_baseline|

onde:
    H_baseline = itens que sairam HALLUCINATED no pipeline RAG sem guardrails
    B_eduquery = itens que sairam BLOCKED no pipeline EduQuery completo

Tambem implementamos a Taxa de Falsos Positivos (FP): itens corretos
no baseline que foram bloqueados pelo EduQuery (i.e., bloqueio
indevido). FP baixo e desejavel.
"""

from __future__ import annotations

from dataclasses import dataclass

from evaluation.metrics.hallucination_classifier import Classification


@dataclass(frozen=True)
class QueryResult:
    """Resultado consolidado de uma consulta para uma execucao do pipeline.

    Attributes:
        id: id do item no golden.
        classification: CORRECT, HALLUCINATED, BLOCKED.
    """

    id: str
    classification: Classification


def _ids_with_class(results: list[QueryResult], target: Classification) -> set[str]:
    return {r.id for r in results if r.classification == target}


def compute_tia(
    baseline: list[QueryResult],
    eduquery: list[QueryResult],
) -> float:
    """Taxa de Interceptacao de Alucinacoes.

    Args:
        baseline: resultados rodando o pipeline SEM guardrails.
        eduquery: resultados rodando o pipeline COM guardrails.

    Returns:
        TIA em [0, 1]. Retorna 0.0 quando o baseline nao gerou
        nenhuma alucinacao (caso degenerado: nada para interceptar).
    """
    baseline_halluc = _ids_with_class(baseline, Classification.HALLUCINATED)
    if not baseline_halluc:
        return 0.0
    eduquery_blocked = _ids_with_class(eduquery, Classification.BLOCKED)
    intercepted = baseline_halluc & eduquery_blocked
    return len(intercepted) / len(baseline_halluc)


def compute_false_positive_rate(
    baseline: list[QueryResult],
    eduquery: list[QueryResult],
) -> float:
    """Taxa de bloqueio INDEVIDO (falsos positivos do guardrail).

    Mede: dos itens que sairam CORRECT no baseline, qual fracao foi
    BLOCKED pelo EduQuery? Quanto menor, melhor.

    Returns:
        FP rate em [0, 1]. Retorna 0.0 quando o baseline nao tem
        nenhum item correto (caso degenerado).
    """
    baseline_correct = _ids_with_class(baseline, Classification.CORRECT)
    if not baseline_correct:
        return 0.0
    eduquery_blocked = _ids_with_class(eduquery, Classification.BLOCKED)
    indevido = baseline_correct & eduquery_blocked
    return len(indevido) / len(baseline_correct)


def compute_guardrail_summary(
    baseline: list[QueryResult],
    eduquery: list[QueryResult],
) -> dict[str, float | int]:
    """Resumo agregado: contagens por classificacao + TIA + FP."""

    def counts(results: list[QueryResult]) -> dict[str, int]:
        return {
            "correct": sum(1 for r in results if r.classification == Classification.CORRECT),
            "hallucinated": sum(
                1 for r in results if r.classification == Classification.HALLUCINATED
            ),
            "blocked": sum(1 for r in results if r.classification == Classification.BLOCKED),
            "total": len(results),
        }

    return {
        "baseline": counts(baseline),
        "eduquery": counts(eduquery),
        "tia": compute_tia(baseline, eduquery),
        "false_positive_rate": compute_false_positive_rate(baseline, eduquery),
    }
