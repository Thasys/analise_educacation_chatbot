"""Metricas puras (sem LLM) usadas pela avaliacao do EduQuery.

Cada submodulo expoe funcoes ou dataclasses deterministicas que
recebem dados ja parseados e retornam um numero ou bool. Nenhuma
metrica chama LLM nem rede (excecao opcional: `doi_validity.is_doi_resolvable`,
que so e usada sob flag explicita).
"""

from evaluation.metrics.numeric_accuracy import NumericResult
from evaluation.metrics.doi_validity import (
    is_doi_syntactically_valid,
    is_doi_resolvable,
)
from evaluation.metrics.source_coverage import compute_source_recall
from evaluation.metrics.hallucination_classifier import (
    classify_response,
    Classification,
)
from evaluation.metrics.guardrails_efficacy import (
    QueryResult,
    compute_tia,
    compute_false_positive_rate,
)

__all__ = [
    "Classification",
    "NumericResult",
    "QueryResult",
    "classify_response",
    "compute_false_positive_rate",
    "compute_source_recall",
    "compute_tia",
    "is_doi_resolvable",
    "is_doi_syntactically_valid",
]
