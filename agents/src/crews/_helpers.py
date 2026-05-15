"""Helpers compartilhados entre as Crews.

`coerce_output` substitui as variantes locais `_coerce_intent`,
`_coerce_entities` e `_coerce` que existiam em `core_crew.py` e
`analysis_crew.py`. Cobre os 3 formatos de output do CrewAI: instancia
ja tipada, dict, ou string JSON.

`run_single_agent_task` encapsula o padrao "monta payload JSON ->
constroi Task -> kickoff Crew(1 agent, 1 task) -> coerce output". Cada
etapa da Analysis Crew ficava com ~20 linhas; agora ~6.

Ganho secundario (QW3/MP4 do quality-assessment): adicionar um validador
sobre o output do agente (ex.: fact-checker comparando markdown vs
primary_data) e uma edicao deste helper em vez de 4 ou 5 locais.
"""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from crewai import Agent, Crew, Process, Task
from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


# ----------------------------------------------------------------------
# Numeric fact-check (QW3 do quality-assessment 2026-05-14)
# ----------------------------------------------------------------------

# Numeros com ate 4 digitos antes da virgula e ate 3 decimais. Captura
# "5", "5.62", "5,62", "82%", "0.6". Ignora numeros muito grandes (anos)
# para nao falsa-marcar "2022" como divergente.
_NUMBER_RE = re.compile(r"(?<![\w])(\d{1,4}(?:[.,]\d{1,3})?)(?![\w])")


def _extract_numbers(text: str) -> list[float]:
    """Extrai numeros do markdown. Anos (1900-2099 sem decimal) sao filtrados."""
    out: list[float] = []
    for m in _NUMBER_RE.finditer(text):
        raw = m.group(1).replace(",", ".")
        try:
            v = float(raw)
        except ValueError:
            continue
        if v.is_integer() and 1900 <= v <= 2099:
            continue
        out.append(v)
    return out


def _collect_reference_values(
    primary_data: list[dict[str, Any]] | None,
    primary_meta: dict[str, Any] | None,
) -> set[float]:
    """Reune todos os valores numericos de referencia (rows + meta).

    Implementa parte do MP4 (fact-check): alem de `primary_data.value`,
    inclui campos canonicos de `primary_meta` que o mart Gold publica
    (zscore_in_oecd, percentile_in_oecd, gap_to_oecd_mean, trend_slope,
    stats `min/max/mean/median`).
    """
    refs: set[float] = set()
    for row in primary_data or []:
        for key in ("value", "rank", "year"):
            v = row.get(key)
            if v is None:
                continue
            try:
                refs.add(float(v))
            except (TypeError, ValueError):
                continue
    meta = primary_meta or {}
    for key in (
        "zscore_in_oecd",
        "percentile_in_oecd",
        "gap_to_oecd_mean",
        "trend_slope",
        "min",
        "max",
        "mean",
        "median",
    ):
        v = meta.get(key)
        if v is None:
            continue
        try:
            refs.add(float(v))
        except (TypeError, ValueError):
            continue
    # `comparison_stats` aninhado (vem do /api/data/compare).
    stats = meta.get("comparison_stats")
    if isinstance(stats, dict):
        for v in stats.values():
            if isinstance(v, (int, float)):
                refs.add(float(v))
    return refs


def check_numeric_consistency(
    markdown: str,
    primary_data: list[dict[str, Any]] | None,
    *,
    primary_meta: dict[str, Any] | None = None,
    tolerance_pct: float = 0.05,
    max_divergence_ratio: float = 0.20,
) -> tuple[bool, list[float]]:
    """Verifica se >=80% dos numeros do markdown batem com referencias reais.

    Implementa QW3 e e o nucleo do MP4 (fact-check). Extrai todos os
    numeros do markdown (exceto anos), compara cada um com:
      - `primary_data[*].value` (valores brutos do Retriever)
      - `primary_meta.*` (zscore, percentile, gap, stats — do mart Gold)
    Tolerancia de 5% por padrao. Se mais de 20% dos numeros nao casam,
    retorna `(False, divergentes)`.

    Args:
        markdown: texto final do Synthesizer.
        primary_data: lista de rows com `value`.
        primary_meta: dict com estatisticas precomputadas (zscore, etc.).
        tolerance_pct: 0.05 = 5% (default). Aceita arredondamento.
        max_divergence_ratio: 0.20 = 20%. Acima disso, retorna inconsistente.

    Returns:
        (is_consistent, list_of_unmatched_numbers).
    """
    md_numbers = _extract_numbers(markdown)
    if not md_numbers:
        return True, []
    ref_values = _collect_reference_values(primary_data, primary_meta)
    if not ref_values:
        # Sem dados de referencia, nao temos como validar; passa.
        return True, []

    def _matches(target: float) -> bool:
        for ref in ref_values:
            denom = max(abs(ref), 1.0)
            if abs(target - ref) / denom <= tolerance_pct:
                return True
        # Tambem aceita derivados (target ~ ref/100, ref*100) p/
        # percentual <-> proporcao.
        for ref in ref_values:
            for variant in (ref * 100, ref / 100):
                denom = max(abs(variant), 1.0)
                if abs(target - variant) / denom <= tolerance_pct:
                    return True
        return False

    unmatched = [n for n in md_numbers if not _matches(n)]
    ratio = len(unmatched) / len(md_numbers)
    return ratio <= max_divergence_ratio, unmatched


def run_fact_check(
    final_markdown: str,
    retrieved: Any,
    *,
    tolerance_pct: float = 0.05,
    max_divergence_ratio: float = 0.20,
) -> tuple[bool, list[float]]:
    """Wrapper de `check_numeric_consistency` que aceita `RetrievedData`.

    Usa o helper acima passando `primary_data` e `primary_meta` de uma
    instancia do schema `RetrievedData`. E o ponto de entrada usado pelo
    `master_flow` no MP4 (fact-checker apos Synthesizer).
    """
    primary_data = getattr(retrieved, "primary_data", None)
    primary_meta = getattr(retrieved, "primary_meta", None)
    return check_numeric_consistency(
        final_markdown,
        primary_data,
        primary_meta=primary_meta,
        tolerance_pct=tolerance_pct,
        max_divergence_ratio=max_divergence_ratio,
    )


def coerce_output(model_cls: type[M], raw: object) -> M:
    """Converte o output cru do CrewAI numa instancia tipada de `model_cls`.

    CrewAI pode devolver: a propria instancia Pydantic (quando
    `output_pydantic` foi respeitado), um dict (JSON parseado mas nao
    coerced) ou uma string (JSON nao parseado, quando o LLM ignorou
    `output_pydantic`).
    """
    if isinstance(raw, model_cls):
        return raw
    if isinstance(raw, dict):
        return model_cls.model_validate(raw)
    if isinstance(raw, str):
        return model_cls.model_validate(json.loads(raw))
    raise TypeError(
        f"Saida inesperada de agente: esperado {model_cls.__name__}, "
        f"recebeu {type(raw).__name__}"
    )


def run_single_agent_task(
    agent: Agent,
    *,
    description: str,
    output_schema: type[M],
    payload: dict[str, Any] | None = None,
) -> M:
    """Roda um agente isolado em uma Crew com 1 task e devolve o output coerced.

    Args:
        agent: Agent CrewAI ja construido (via `make_agent` ou factory).
        description: instrucao para o agente (o que ele deve fazer).
        output_schema: classe Pydantic do output esperado.
        payload: dict com contexto a serializar como JSON e anexar ao final
            da `description`. Use `None` para descricoes sem contexto.

    Convencao: payload JSON e anexado como bloco "\n\nCONTEXTO:\n{json}"
    apos a descricao. Compativel com prompts atuais dos agentes.
    """
    full_description = description
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False)
        full_description = f"{description}\n\nCONTEXTO:\n{body}"

    task = Task(
        description=full_description,
        expected_output=f"JSON {output_schema.__name__}",
        output_pydantic=output_schema,
        agent=agent,
    )
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    raw = task.output.pydantic or task.output.raw
    return coerce_output(output_schema, raw)
