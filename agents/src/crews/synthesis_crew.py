"""Synthesis Crew — Visualizer + Response Synthesizer.

Estrategia: process=sequential, Visualizer primeiro (Synthesizer pode
referenciar a viz no markdown via VizSpec). Os dois agentes recebem o
mesmo contexto consolidado: IntentDecision + EntityExtraction +
RetrievedData + StatAnalysis + ComparativeContext.

Em uma versao futura podemos paralelizar os dois com
Process.hierarchical, ja que a saida do Visualizer entra no Synthesizer
mas pode ser computada simultaneamente em ~70% dos casos.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from crewai import Crew, Process, Task

from src.agents import build_synthesizer, build_visualizer
from src.schemas import (
    ComparativeContext,
    CoreFlowOutput,
    FinalAnswer,
    RetrievedData,
    StatAnalysis,
    VizSpec,
)


log = structlog.get_logger(__name__)


def _build_context(
    core: CoreFlowOutput,
    retrieved: RetrievedData,
    stats: StatAnalysis,
    context: ComparativeContext,
) -> str:
    """Serializa todo o contexto para os agentes em uma string compacta."""
    return json.dumps(
        {
            "question": core.question,
            "intent": core.intent.model_dump(),
            "entities": core.entities.model_dump(),
            "retrieved": retrieved.model_dump(),
            "stat_analysis": stats.model_dump(),
            "comparative_context": context.model_dump(),
        },
        ensure_ascii=False,
    )


def _viz_task(agent, context_blob: str) -> Task:
    return Task(
        description=(
            "Receba o contexto consolidado abaixo e produza um VizSpec "
            "(JSON) com chart_type, title, plotly_figure, sources, notes. "
            "Siga as regras do seu system prompt para escolher o chart "
            "type apropriado.\n\n"
            f"CONTEXTO:\n{context_blob}"
        ),
        expected_output="JSON VizSpec",
        output_pydantic=VizSpec,
        agent=agent,
    )


def _synth_task(agent, context_blob: str) -> Task:
    return Task(
        description=(
            "Receba o contexto consolidado abaixo (incluindo a VizSpec ja "
            "gerada) e produza um FinalAnswer (JSON) com markdown adaptado "
            "ao perfil. Siga estritamente o template e as regras do seu "
            "system prompt.\n\n"
            f"CONTEXTO:\n{context_blob}"
        ),
        expected_output="JSON FinalAnswer",
        output_pydantic=FinalAnswer,
        agent=agent,
    )


def build_synthesis_crew(
    core: CoreFlowOutput,
    retrieved: RetrievedData,
    stats: StatAnalysis,
    context: ComparativeContext,
) -> Crew:
    """Monta a Synthesis Crew (Visualizer -> Synthesizer)."""
    visualizer = build_visualizer()
    synthesizer = build_synthesizer()
    context_blob = _build_context(core, retrieved, stats, context)
    return Crew(
        agents=[visualizer, synthesizer],
        tasks=[
            _viz_task(visualizer, context_blob),
            _synth_task(synthesizer, context_blob),
        ],
        process=Process.sequential,
        verbose=False,
    )


def _coerce(model_cls, raw: object):
    if isinstance(raw, model_cls):
        return raw
    if isinstance(raw, dict):
        return model_cls.model_validate(raw)
    if isinstance(raw, str):
        return model_cls.model_validate(json.loads(raw))
    raise TypeError(f"Saida inesperada: {type(raw).__name__}")


def run_synthesis_flow(
    core: CoreFlowOutput,
    retrieved: RetrievedData,
    stats: StatAnalysis,
    context: ComparativeContext,
) -> tuple[VizSpec, FinalAnswer]:
    """Executa a Synthesis Crew e devolve outputs tipados."""
    log.info(
        "agents.synthesis_crew.start",
        question=core.question[:120],
        flow=core.intent.flow,
        profile=core.intent.profile,
    )
    crew = build_synthesis_crew(core, retrieved, stats, context)
    crew.kickoff()
    viz_raw = crew.tasks[0].output.pydantic or crew.tasks[0].output.raw
    final_raw = crew.tasks[1].output.pydantic or crew.tasks[1].output.raw
    viz = _coerce(VizSpec, viz_raw)
    final = _coerce(FinalAnswer, final_raw)
    log.info(
        "agents.synthesis_crew.done",
        chart_type=viz.chart_type,
        markdown_len=len(final.markdown),
        sources=final.sources_cited,
    )
    return viz, final


def regenerate_final_after_fact_check(
    core: CoreFlowOutput,
    retrieved: RetrievedData,
    stats: StatAnalysis,
    context: ComparativeContext,
    *,
    divergences: list[float],
    previous_markdown: str,
) -> FinalAnswer:
    """Regenera APENAS o `FinalAnswer` apos fact-check detectar divergencias.

    Roda so o Synthesizer (sem Visualizer, ja temos VizSpec) com uma
    instrucao explicita listando os numeros divergentes e os valores
    canonicos esperados. Implementa o caminho de retry do MP4.

    A viz nao precisa ser regerada — o frontend ja recebe o
    `plotly_figure` do primeiro run. Aqui foco apenas no markdown.
    """
    synthesizer = build_synthesizer()
    context_blob = _build_context(core, retrieved, stats, context)

    # Lista os primeiros 10 valores REAIS para o LLM consultar
    primary_vals = [
        f"{r.get('country_iso3', '?')}={r.get('value')}"
        for r in (retrieved.primary_data or [])[:10]
        if r.get("value") is not None
    ]
    primary_meta = retrieved.primary_meta or {}
    meta_vals = [
        f"{k}={primary_meta[k]}"
        for k in (
            "zscore_in_oecd",
            "percentile_in_oecd",
            "gap_to_oecd_mean",
            "trend_slope",
        )
        if k in primary_meta and primary_meta[k] is not None
    ]

    divergences_str = ", ".join(f"{n:g}" for n in divergences[:10])
    retry_task = Task(
        description=(
            "REGENERACAO POS FACT-CHECK.\n\n"
            "A versao anterior do markdown continha numeros que NAO existem "
            "no contexto. Voce DEVE produzir uma nova versao usando APENAS "
            "numeros da lista canonica abaixo.\n\n"
            f"NUMEROS DIVERGENTES (NAO usar): {divergences_str}\n\n"
            f"NUMEROS CANONICOS (USE estes): {', '.join(primary_vals + meta_vals)}\n\n"
            "REGRA ABSOLUTA: cada numero no markdown deve aparecer na lista "
            "de NUMEROS CANONICOS. Se nao puder afirmar quantitativamente "
            "algo, use linguagem qualitativa ('acima da media', sem citar "
            "o valor).\n\n"
            f"MARKDOWN ANTERIOR (para referencia, NAO copie numeros dele):\n"
            f"{previous_markdown[:1500]}\n\n"
            f"CONTEXTO COMPLETO:\n{context_blob}"
        ),
        expected_output="JSON FinalAnswer revisado",
        output_pydantic=FinalAnswer,
        agent=synthesizer,
    )
    crew = Crew(
        agents=[synthesizer],
        tasks=[retry_task],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    raw = retry_task.output.pydantic or retry_task.output.raw
    return _coerce(FinalAnswer, raw)


# Re-export de tipos uteis
__all__: list[str] = [
    "build_synthesis_crew",
    "run_synthesis_flow",
]
