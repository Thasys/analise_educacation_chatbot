"""Master flow — orquestrador unico Core -> Analysis -> Synthesis.

Roteia por `IntentDecision.flow`:

- simple: Core -> Comparativist (com RAG) -> Citation -> Synthesis
  (pula Retriever/Statistician — perguntas conceituais).
- data:   Core -> Analysis completo -> Synthesis (caminho default).
- deep:   idem data, com max_iter maior nos agentes (futuro);
  Sprint 5.6 trata como `data`.

Saida final: `FinalAnswer` com `citations` populadas a partir das
Citations do Citation Agent.

Sprint 6.1: aceita callback opcional `on_event` para emitir progresso
em tempo real (consumido pelo endpoint /api/chat/stream do gateway).
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import structlog

from src.api_client import EduGatewayClient
from src.crews.analysis_crew import (
    _run_citation,
    _run_comparativist,
    _run_retriever,
    _run_statistician,
)
from src.crews.core_crew import run_core_flow
from src.crews.synthesis_crew import run_synthesis_flow
from src.rag.client import RagClient
from src.schemas import (
    CoreFlowOutput,
    FinalAnswer,
    RetrievedData,
    StatAnalysis,
)


log = structlog.get_logger(__name__)


# Tipo do callback de evento (Sprint 6.1).
# Cada evento e um dict serializavel JSON com pelo menos `type` e `ts`.
EventCallback = Callable[[dict[str, Any]], None]


def _disable_crewai_telemetry_if_default() -> None:
    """Desabilita telemetria CrewAI (PostHog) se o usuario nao definiu.

    Evita trafego de saida nao intencional em sistema academico.
    Pode ser sobrescrito via OTEL_SDK_DISABLED=false no .env.
    """
    os.environ.setdefault("OTEL_SDK_DISABLED", "true")
    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")


def _empty_retrieved() -> RetrievedData:
    return RetrievedData(
        summary="Pergunta conceitual — nao foram chamadas tools de dados.",
    )


def _empty_stats() -> StatAnalysis:
    return StatAnalysis(
        method="agregados",
        sample_size=0,
        confidence_note=(
            "Pergunta conceitual sem dados quantitativos para analise."
        ),
    )


def _emit(on_event: EventCallback | None, event: dict[str, Any]) -> None:
    """Emite evento se callback presente; ignora exceções do consumidor.

    Adiciona `ts` automaticamente se ausente. Falha do consumidor
    (ex.: queue cheia, conexao SSE caiu) NUNCA quebra o pipeline.
    """
    if on_event is None:
        return
    if "ts" not in event:
        event["ts"] = time.time()
    try:
        on_event(event)
    except Exception as exc:  # noqa: BLE001
        log.warning("agents.master_flow.event_emit_failed", error=str(exc))


def run_master(
    question: str,
    *,
    gateway_client: EduGatewayClient | None = None,
    rag_client: RagClient | None = None,
    on_event: EventCallback | None = None,
) -> FinalAnswer:
    """Orquestra Core -> Analysis -> Synthesis e devolve FinalAnswer.

    Args:
        question: pergunta do usuario em linguagem natural.
        gateway_client: cliente HTTP para o gateway. None -> defaults
            (settings.gateway_base_url).
        rag_client: cliente RAG ChromaDB. None -> singleton em
            data/chromadb/edu_literature/.
        on_event: callback opcional invocado a cada etapa do pipeline.
            Cada evento e um dict com `type` (agent_started, agent_done,
            final_answer, error) e `ts` (epoch float). Outros campos
            dependem do tipo. Sprint 6.1 usa para emitir SSE.

    Returns:
        FinalAnswer com markdown + visualizations + citations + warnings.
    """
    _disable_crewai_telemetry_if_default()
    started = time.perf_counter()
    log.info("agents.master_flow.start", question=question[:160])
    _emit(on_event, {"type": "flow_started", "question": question[:160]})

    # 1. Core Crew (sempre roda)
    _emit(on_event, {"type": "agent_started", "agent": "Core (Orchestrator + Profiler)"})
    core = run_core_flow(question)
    _emit(
        on_event,
        {
            "type": "agent_done",
            "agent": "Core (Orchestrator + Profiler)",
            "result": {
                "flow": core.intent.flow,
                "profile": core.intent.profile,
                "confidence": core.intent.confidence,
                "indicator": core.entities.indicator,
                "countries": core.entities.countries,
            },
        },
    )
    log.info(
        "agents.master_flow.core_done",
        flow=core.intent.flow,
        profile=core.intent.profile,
        confidence=core.intent.confidence,
    )

    # 2. Roteamento por fluxo
    if core.intent.flow == "simple":
        retrieved = _empty_retrieved()
        stats = _empty_stats()

        _emit(on_event, {"type": "agent_started", "agent": "Comparativist"})
        context = _run_comparativist(core, retrieved, stats, rag_client)
        _emit(on_event, {"type": "agent_done", "agent": "Comparativist"})

        _emit(on_event, {"type": "agent_started", "agent": "Citation"})
        citations = _run_citation(core, context, rag_client)
        _emit(
            on_event,
            {"type": "agent_done", "agent": "Citation", "items": len(citations.items)},
        )
    else:
        # data ou deep — Analysis completo (4 etapas, evento por etapa)
        _emit(on_event, {"type": "agent_started", "agent": "Retriever"})
        retrieved = _run_retriever(core, gateway_client)
        _emit(
            on_event,
            {
                "type": "agent_done",
                "agent": "Retriever",
                "tool_calls": len(retrieved.tool_calls),
            },
        )

        _emit(on_event, {"type": "agent_started", "agent": "Statistician"})
        stats = _run_statistician(core, retrieved)
        _emit(
            on_event,
            {
                "type": "agent_done",
                "agent": "Statistician",
                "method": stats.method,
                "sample_size": stats.sample_size,
            },
        )

        _emit(on_event, {"type": "agent_started", "agent": "Comparativist"})
        context = _run_comparativist(core, retrieved, stats, rag_client)
        _emit(on_event, {"type": "agent_done", "agent": "Comparativist"})

        _emit(on_event, {"type": "agent_started", "agent": "Citation"})
        citations = _run_citation(core, context, rag_client)
        _emit(
            on_event,
            {"type": "agent_done", "agent": "Citation", "items": len(citations.items)},
        )

    # 3. Synthesis (Visualizer + Synthesizer)
    _emit(on_event, {"type": "agent_started", "agent": "Synthesis (Visualizer + Synthesizer)"})
    viz, final = run_synthesis_flow(core, retrieved, stats, context)
    _emit(
        on_event,
        {
            "type": "agent_done",
            "agent": "Synthesis (Visualizer + Synthesizer)",
            "chart_type": viz.chart_type,
        },
    )

    # 4. Acoplar citations no FinalAnswer
    final.citations = citations.items

    elapsed_s = time.perf_counter() - started
    log.info(
        "agents.master_flow.done",
        elapsed_s=round(elapsed_s, 2),
        flow=core.intent.flow,
        markdown_len=len(final.markdown),
        n_citations=len(final.citations),
        chart_type=viz.chart_type,
    )
    _emit(
        on_event,
        {
            "type": "final_answer",
            "elapsed_s": round(elapsed_s, 2),
            "payload": final.model_dump(),
        },
    )
    return final


__all__ = ["run_master", "EventCallback"]
