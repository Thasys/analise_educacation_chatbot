"""Master flow — orquestrador unico Core -> Analysis -> Synthesis.

Roteia por `IntentDecision.flow`:

- `simple`: Core -> Comparativist (com RAG) -> Citation -> Synthesis
  (pula Retriever/Statistician — perguntas conceituais).
- `data`:   Core -> Analysis completo -> Synthesis (caminho default).
- `deep`:   idem `data`, com `max_iter` maior nos agentes (planejado);
  hoje tratado igual a `data`.

Saida final: `FinalAnswer` com `citations` populadas a partir das
Citations do Citation Agent + Fact Checker (ADR 0007).

Callback `on_event` opcional emite progresso em tempo real (cada
agente vira um par `agent_started`/`agent_done`). Consumido pelo
endpoint /api/chat/stream do gateway (SSE).
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
from src.crews._helpers import run_fact_check
from src.crews.core_crew import run_core_flow
from src.crews.synthesis_crew import (
    regenerate_final_after_fact_check,
    run_synthesis_flow,
)
from src.rag.client import RagClient
from src.schemas import (
    CoreFlowOutput,
    FinalAnswer,
    RetrievedData,
    StatAnalysis,
)


log = structlog.get_logger(__name__)


# Tipo do callback de evento. Cada evento e um dict serializavel JSON
# com pelo menos `type` e `ts`. Consumido pelo SSE no agents-server.
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
    no_guardrails: bool = False,
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
            dependem do tipo. Usado pelo endpoint /api/chat/stream.
        no_guardrails: quando True, executa o pipeline como **baseline
            RAG puro** (Secao 5.1 do plano de avaliacao). Especifica-
            mente desativa:
              * Retriever auto-populate determinístico (ADR 0006).
              * Filtro de DOIs placeholder no Citation Agent.
              * Fact Checker pos-Synthesizer + retry (ADR 0007).
            Usado APENAS pela bateria de testes para gerar o denomi-
            nador da TIA. Em producao, sempre False.

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
        citations = _run_citation(
            core, context, rag_client, no_guardrails=no_guardrails
        )
        _emit(
            on_event,
            {"type": "agent_done", "agent": "Citation", "items": len(citations.items)},
        )
    else:
        # data ou deep — Analysis completo (4 etapas, evento por etapa)
        _emit(on_event, {"type": "agent_started", "agent": "Retriever"})
        retrieved = _run_retriever(
            core, gateway_client, no_guardrails=no_guardrails
        )
        _emit(
            on_event,
            {
                "type": "agent_done",
                "agent": "Retriever",
                "tool_calls": len(retrieved.tool_calls),
                "primary_data_rows": len(retrieved.primary_data or []),
                "primary_meta_keys": list((retrieved.primary_meta or {}).keys())[:8],
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
        citations = _run_citation(
            core, context, rag_client, no_guardrails=no_guardrails
        )
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

    # 4. Fact-check (MP4 do quality-assessment 2026-05-14, ADR 0007).
    # Validacao deterministica: extrai numeros do markdown e cruza com
    # `retrieved.primary_data` + `primary_meta`. Se >20% divergentes,
    # regenera o Synthesizer 1x com lista de divergencias. Se ainda
    # falhar, marca warning visivel.
    # Quando `no_guardrails=True` (baseline da avaliacao), pulamos.
    if no_guardrails:
        _emit(
            on_event,
            {"type": "agent_skipped", "agent": "Fact Checker", "reason": "no_guardrails"},
        )
        final.citations = citations.items
        elapsed_s = time.perf_counter() - started
        log.info(
            "agents.master_flow.done",
            elapsed_s=round(elapsed_s, 2),
            flow=core.intent.flow,
            markdown_len=len(final.markdown),
            n_citations=len(final.citations),
            chart_type=viz.chart_type,
            mode="baseline_no_guardrails",
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

    _emit(on_event, {"type": "agent_started", "agent": "Fact Checker"})
    is_consistent, divergences = run_fact_check(final.markdown, retrieved)
    if not is_consistent and divergences:
        log.warning(
            "agents.master_flow.fact_check_failed",
            divergences=divergences[:10],
            attempt=1,
        )
        _emit(
            on_event,
            {
                "type": "agent_done",
                "agent": "Fact Checker",
                "is_consistent": False,
                "divergences": divergences[:10],
                "action": "retry_synthesizer",
            },
        )
        # Retry: regenera apenas o Synthesizer com divergencias no prompt.
        _emit(on_event, {"type": "agent_started", "agent": "Synthesizer (retry)"})
        try:
            final = regenerate_final_after_fact_check(
                core, retrieved, stats, context,
                divergences=divergences,
                previous_markdown=final.markdown,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("agents.master_flow.synth_retry_failed")
            _emit(
                on_event,
                {"type": "agent_done", "agent": "Synthesizer (retry)", "error": str(exc)},
            )
        else:
            _emit(on_event, {"type": "agent_done", "agent": "Synthesizer (retry)"})
            # Recheck — se ainda inconsistente, adiciona warning.
            is_consistent, divergences = run_fact_check(final.markdown, retrieved)
            if not is_consistent and divergences:
                final.warnings = list(final.warnings) + [
                    f"Fact-check: {len(divergences)} valores no markdown nao "
                    f"correspondem ao dado real (tolerancia 5%). "
                    f"Divergentes: {', '.join(f'{n:g}' for n in divergences[:5])}. "
                    "Trate como ilustrativo, nao final."
                ]
                log.warning(
                    "agents.master_flow.fact_check_failed_after_retry",
                    divergences=divergences[:10],
                )
    else:
        _emit(
            on_event,
            {
                "type": "agent_done",
                "agent": "Fact Checker",
                "is_consistent": True,
                "divergences": [],
            },
        )

    # 5. Acoplar citations no FinalAnswer
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
