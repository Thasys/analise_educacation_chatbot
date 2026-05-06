"""Stats tools — computacao local sobre os dados recuperados.

`compute_summary_stats(values)` e helper puro Python (testavel sem
CrewAI). `ComputeStatsTool` e o wrapper BaseTool que o Statistician
pode invocar. Util quando o conjunto e grande (>10 linhas) e o LLM
preferir delegar a aritmetica para Python.

REGRA METODOLOGICA: estas funcoes assumem **indicadores agregados**
(uma observacao por pais-ano). NAO usar para microdados PISA/TIMSS,
que exigem Plausible Values + BRR/Jackknife.
"""

from __future__ import annotations

import json
import math
import statistics
from typing import Any, ClassVar

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


# ----------------------------------------------------------------------
# Helper puro
# ----------------------------------------------------------------------


def compute_summary_stats(values: list[float]) -> dict[str, float]:
    """Calcula estatisticas descritivas de uma lista de floats.

    Retorna dict com chaves: mean, median, stddev, min, max, cv,
    sample_size. Se a lista tem <2 elementos, stddev e cv ficam 0.
    """
    if not values:
        return {
            "mean": 0.0,
            "median": 0.0,
            "stddev": 0.0,
            "min": 0.0,
            "max": 0.0,
            "cv": 0.0,
            "sample_size": 0,
        }
    n = len(values)
    mean = statistics.fmean(values)
    median = statistics.median(values)
    if n >= 2:
        stddev = statistics.stdev(values)
        cv = (stddev / mean) if mean != 0 else 0.0
    else:
        stddev = 0.0
        cv = 0.0
    return {
        "mean": mean,
        "median": median,
        "stddev": stddev,
        "min": min(values),
        "max": max(values),
        "cv": cv,
        "sample_size": n,
    }


def compute_position(
    value: float,
    universe: list[float],
    *,
    higher_is_better: bool = True,
) -> dict[str, float]:
    """Posiciona um valor em um universo: zscore, percentile, gap, rank.

    Args:
        value: o valor do pais foco.
        universe: TODOS os valores do conjunto (incluindo o foco).
        higher_is_better: se True, percentil alto = melhor (gasto, alfab).
    """
    if not universe:
        return {"zscore": 0.0, "percentile": 0.0, "gap_to_mean": 0.0, "rank": 0}
    stats = compute_summary_stats(universe)
    n = stats["sample_size"]
    mean = stats["mean"]
    stddev = stats["stddev"]
    zscore = (value - mean) / stddev if stddev > 0 else 0.0

    # Percentil: fracao de valores estritamente menores que `value`
    # (alto = melhor se higher_is_better).
    sorted_vals = sorted(universe)
    rank_position = sum(1 for v in sorted_vals if v < value)
    percentile = rank_position / (n - 1) if n > 1 else 0.5
    if not higher_is_better:
        percentile = 1.0 - percentile

    # Rank ordinal (1 = melhor pelo criterio higher_is_better).
    if higher_is_better:
        rank = sum(1 for v in universe if v > value) + 1
    else:
        rank = sum(1 for v in universe if v < value) + 1

    return {
        "zscore": zscore,
        "percentile": percentile,
        "gap_to_mean": value - mean,
        "rank": rank,
    }


# ----------------------------------------------------------------------
# Tool CrewAI
# ----------------------------------------------------------------------


class ComputeStatsArgs(BaseModel):
    """Argumentos da ComputeStatsTool."""

    values: list[float] = Field(
        ..., min_length=1, description="Lista de valores numericos do conjunto."
    )
    focus_value: float | None = Field(
        default=None,
        description="Valor do pais foco para posicionamento (z-score, percentil, rank).",
    )
    higher_is_better: bool = Field(
        default=True,
        description=(
            "True para metricas onde alto=bom (gasto educacional, alfab). "
            "False para metricas onde baixo=bom (taxa abandono, analfab)."
        ),
    )


class ComputeStatsTool(BaseTool):
    """Calcula estatisticas descritivas e posicionamento de um valor."""

    name: str = "compute_stats"
    description: str = (
        "Calcula estatisticas descritivas (mean, median, stddev, min, max, cv) "
        "de uma lista de valores. Se 'focus_value' for passado, retorna tambem "
        "z-score, percentil, gap vs media e rank desse valor no conjunto. "
        "Use APENAS para indicadores AGREGADOS (% PIB, % alfab, taxas) — NAO "
        "para microdados PISA/TIMSS/PIRLS que exigem Plausible Values."
    )
    args_schema: type[BaseModel] = ComputeStatsArgs

    # ClassVar para uniformidade com data_tools (nao usado aqui mas reservado).
    _client_override: ClassVar[None] = None

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Override para capturar ValueError da validacao (mesmo padrao
        de _SafeDataTool)."""
        try:
            return super().run(*args, **kwargs)
        except ValueError as exc:
            return json.dumps(
                {"ok": False, "error": {"error_type": "validation", "message": str(exc)}}
            )

    def _run(
        self,
        values: list[float],
        focus_value: float | None = None,
        higher_is_better: bool = True,
    ) -> str:
        result: dict[str, Any] = {
            "ok": True,
            "summary": compute_summary_stats(values),
        }
        if focus_value is not None:
            result["focus_position"] = compute_position(
                focus_value, values, higher_is_better=higher_is_better
            )
        return json.dumps(result, default=_json_default)


def _json_default(value: Any) -> Any:
    """Serializa NaN/Inf como null para JSON estrito."""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    raise TypeError(f"Nao serializavel: {type(value).__name__}")
