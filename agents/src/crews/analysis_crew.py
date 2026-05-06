"""Analysis Crew — Retriever -> Statistician -> Comparativist -> Citation.

Em CrewAI 1.x preferimos rodar cada agente em sua propria Crew (1 task)
e encadear os outputs em Python — mais simples de testar (mock por
agente) e de logar (1 trace por etapa).

Para fluxo `simple` (perguntas conceituais), o master_flow PULA
Retriever e Statistician, criando placeholders vazios. Aqui assumimos
que se a funcao foi chamada, vamos rodar tudo.
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from crewai import Crew, Process, Task

from src.agents import (
    build_citation,
    build_comparativist,
    build_retriever,
    build_statistician,
)
from src.api_client import EduGatewayClient
from src.rag.client import RagClient
from src.schemas import (
    Citations,
    ComparativeContext,
    CoreFlowOutput,
    RetrievedData,
    StatAnalysis,
)


log = structlog.get_logger(__name__)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _coerce(model_cls, raw: object):
    if isinstance(raw, model_cls):
        return raw
    if isinstance(raw, dict):
        return model_cls.model_validate(raw)
    if isinstance(raw, str):
        return model_cls.model_validate(json.loads(raw))
    raise TypeError(f"Saida inesperada: {type(raw).__name__}")


def _kickoff_single(agent, task: Task) -> Any:
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    return task.output.pydantic or task.output.raw


# ----------------------------------------------------------------------
# Etapas individuais
# ----------------------------------------------------------------------


def _run_retriever(
    core: CoreFlowOutput, gateway_client: EduGatewayClient | None
) -> RetrievedData:
    agent = build_retriever(client=gateway_client)
    payload = json.dumps(
        {"intent": core.intent.model_dump(), "entities": core.entities.model_dump()},
        ensure_ascii=False,
    )
    task = Task(
        description=(
            f"Pergunta: \"{core.question}\"\n\n"
            f"Contexto extraido pela Core Crew:\n{payload}\n\n"
            f"Recupere os dados necessarios via tools (data_catalog, "
            f"data_timeseries, data_compare, data_ranking). Retorne JSON "
            f"RetrievedData."
        ),
        expected_output="JSON RetrievedData",
        output_pydantic=RetrievedData,
        agent=agent,
    )
    raw = _kickoff_single(agent, task)
    return _coerce(RetrievedData, raw)


def _run_statistician(
    core: CoreFlowOutput, retrieved: RetrievedData
) -> StatAnalysis:
    agent = build_statistician()
    payload = json.dumps(
        {
            "question": core.question,
            "entities": core.entities.model_dump(),
            "retrieved": retrieved.model_dump(),
        },
        ensure_ascii=False,
    )
    task = Task(
        description=(
            f"Receba o RetrievedData abaixo e produza um StatAnalysis. "
            f"Se o indicador for PISA/TIMSS/PIRLS, retorne method="
            f"plausible_values_pending.\n\nCONTEXTO:\n{payload}"
        ),
        expected_output="JSON StatAnalysis",
        output_pydantic=StatAnalysis,
        agent=agent,
    )
    raw = _kickoff_single(agent, task)
    return _coerce(StatAnalysis, raw)


def _run_comparativist(
    core: CoreFlowOutput,
    retrieved: RetrievedData,
    stats: StatAnalysis,
    rag_client: RagClient | None,
) -> ComparativeContext:
    agent = build_comparativist(client=rag_client)
    payload = json.dumps(
        {
            "question": core.question,
            "intent": core.intent.model_dump(),
            "entities": core.entities.model_dump(),
            "retrieved_summary": retrieved.summary,
            "primary_data": retrieved.primary_data,
            "primary_meta": retrieved.primary_meta,
            "stat_analysis": stats.model_dump(),
        },
        ensure_ascii=False,
    )
    task = Task(
        description=(
            f"Receba os dados, estatisticas e contexto da pergunta. Use a "
            f"tool rag_search para fundamentar afirmacoes em literatura "
            f"academica. Produza um ComparativeContext.\n\nCONTEXTO:\n{payload}"
        ),
        expected_output="JSON ComparativeContext",
        output_pydantic=ComparativeContext,
        agent=agent,
    )
    raw = _kickoff_single(agent, task)
    return _coerce(ComparativeContext, raw)


def _run_citation(
    core: CoreFlowOutput,
    context: ComparativeContext,
    rag_client: RagClient | None,
) -> Citations:
    agent = build_citation(client=rag_client)
    payload = json.dumps(
        {
            "question": core.question,
            "narrative": context.narrative,
            "key_findings": context.key_findings,
            "country_groups_compared": context.country_groups_compared,
        },
        ensure_ascii=False,
    )
    task = Task(
        description=(
            f"Para a pergunta e narrativa abaixo, selecione 2-5 referencias "
            f"REAIS via rag_search e cite_resolve. Retorne JSON Citations.\n\n"
            f"CONTEXTO:\n{payload}"
        ),
        expected_output="JSON Citations",
        output_pydantic=Citations,
        agent=agent,
    )
    raw = _kickoff_single(agent, task)
    return _coerce(Citations, raw)


# ----------------------------------------------------------------------
# Orquestrador da Analysis Crew
# ----------------------------------------------------------------------


def run_analysis_flow(
    core: CoreFlowOutput,
    *,
    gateway_client: EduGatewayClient | None = None,
    rag_client: RagClient | None = None,
) -> tuple[RetrievedData, StatAnalysis, ComparativeContext, Citations]:
    """Roda os 4 agentes da Analysis Crew sequencialmente.

    Cada agente roda em sua propria Crew (1 task). Vantagens:
      - Mock por agente nos testes (via mock_llm_call by_role).
      - Trace por etapa em Langfuse (Sprint 5.6+ se configurado).
      - Falha de um agente nao quebra o pipeline inteiro — a etapa
        seguinte recebe o erro como parte do contexto.
    """
    log.info(
        "agents.analysis_crew.start",
        question=core.question[:120],
        flow=core.intent.flow,
    )
    retrieved = _run_retriever(core, gateway_client)
    log.info("agents.analysis_crew.retriever_done", calls=len(retrieved.tool_calls))

    stats = _run_statistician(core, retrieved)
    log.info("agents.analysis_crew.stats_done", method=stats.method, n=stats.sample_size)

    context = _run_comparativist(core, retrieved, stats, rag_client)
    log.info(
        "agents.analysis_crew.context_done",
        findings=len(context.key_findings),
    )

    citations = _run_citation(core, context, rag_client)
    log.info("agents.analysis_crew.citation_done", items=len(citations.items))

    return retrieved, stats, context, citations
