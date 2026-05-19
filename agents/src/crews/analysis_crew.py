"""Analysis Crew — Retriever -> Statistician -> Comparativist -> Citation.

Em CrewAI 1.x preferimos rodar cada agente em sua propria Crew (1 task)
e encadear os outputs em Python — mais simples de testar (mock por
agente) e de logar (1 trace por etapa).

Para fluxo `simple` (perguntas conceituais), o master_flow PULA
Retriever e Statistician, criando placeholders vazios. Aqui assumimos
que se a funcao foi chamada, vamos rodar tudo.

Atualizado 2026-05-14 (#5 do DRY pass): boilerplate de `_kickoff_single`
+ `_coerce` agora vive em `_helpers.py` como
`run_single_agent_task`/`coerce_output`. Cada `_run_<etapa>` ficou com
~6 linhas em vez de ~20.
"""

from __future__ import annotations

import structlog

from src.agents import (
    build_citation,
    build_comparativist,
    build_retriever,
    build_statistician,
)
from src.api_client import EduGatewayClient
from src.crews._helpers import run_single_agent_task
from src.rag.client import RagClient
from src.schemas import (
    Citations,
    ComparativeContext,
    CoreFlowOutput,
    RetrievedData,
    StatAnalysis,
)
from src.tools.rag_tools import is_real_doi


log = structlog.get_logger(__name__)


# ----------------------------------------------------------------------
# Etapas individuais
# ----------------------------------------------------------------------


def _run_retriever(
    core: CoreFlowOutput,
    gateway_client: EduGatewayClient | None,
    *,
    no_guardrails: bool = False,
) -> RetrievedData:
    """Executa o Retriever; quando `no_guardrails=True` pula o auto-populate (ADR 0006).

    O auto-populate e um guardrail deterministico: re-executa a tool em
    Python quando o LLM esqueceu de copiar o array. Para o baseline da
    avaliacao (TIA), deixamos o comportamento "puro" do LLM passar.
    """
    retrieved = run_single_agent_task(
        build_retriever(client=gateway_client),
        description=(
            f"Pergunta: \"{core.question}\"\n\n"
            f"Recupere os dados necessarios via tools (data_catalog, "
            f"data_timeseries, data_compare, data_ranking). Retorne JSON "
            f"RetrievedData."
        ),
        output_schema=RetrievedData,
        payload={
            "intent": core.intent.model_dump(),
            "entities": core.entities.model_dump(),
        },
    )
    # Ajuste 6 (2026-05-16, ADR 0006): LLMs locais (qwen2.5:14b) chamam
    # a tool mas falham em copiar o array de rows para `primary_data`.
    # Replicamos a chamada deterministicamente — confiamos no `tool_calls`
    # do output do LLM (tool + arguments) e re-executamos via
    # EduGatewayClient. Custo: 1 HTTP extra (<100 ms vs ~1 min do LLM).
    # Quando `no_guardrails=True` (caminho baseline da avaliacao), pulamos.
    if not no_guardrails and not retrieved.primary_data and retrieved.tool_calls:
        retrieved = _autopopulate_primary_data(retrieved, gateway_client)
    return retrieved


def _autopopulate_primary_data(
    retrieved: RetrievedData,
    gateway_client: EduGatewayClient | None,
) -> RetrievedData:
    """Replica a primeira tool_call OK e popula primary_data/_meta.

    LLMs locais (qwen 14B) chamam a tool mas nao copiam o array de rows
    para `primary_data`. Aqui re-executamos a chamada deterministicamente
    usando `EduGatewayClient` direto, garantindo que os dados cheguem ao
    Statistician/Synthesizer.
    """
    from src.api_client import EduGatewayClient as _Client
    from src.schemas import CompareArgs, RankingArgs, TimeseriesArgs

    candidate = next(
        (
            tc for tc in retrieved.tool_calls
            if tc.status == "ok" and tc.tool in {
                "data_timeseries", "data_compare", "data_ranking", "data_catalog"
            }
        ),
        None,
    )
    if candidate is None:
        return retrieved

    client = gateway_client or _Client()
    args_for_tool = {
        "data_compare": CompareArgs,
        "data_timeseries": TimeseriesArgs,
        "data_ranking": RankingArgs,
    }
    try:
        if candidate.tool == "data_catalog":
            resp = client.catalog()
        else:
            schema_cls = args_for_tool[candidate.tool]
            args = schema_cls(**candidate.arguments)
            method = candidate.tool.replace("data_", "")  # compare/timeseries/ranking
            resp = getattr(client, method)(args)
    except Exception as exc:  # noqa: BLE001 — fallback gracioso
        log.warning(
            "agents.retriever.autopopulate_failed",
            tool=candidate.tool,
            error=str(exc)[:200],
        )
        return retrieved
    if hasattr(resp, "data") and hasattr(resp, "meta"):
        retrieved.primary_data = list(resp.data)
        retrieved.primary_meta = resp.meta.model_dump(exclude_none=True)
        log.info(
            "agents.retriever.autopopulated",
            tool=candidate.tool,
            rows=len(retrieved.primary_data),
            meta_keys=list(retrieved.primary_meta.keys())[:8],
        )
    return retrieved


def _run_statistician(
    core: CoreFlowOutput, retrieved: RetrievedData
) -> StatAnalysis:
    # QW5 do quality-assessment 2026-05-14: quando o mart Gold ja
    # precomputou zscore_in_oecd / percentile_in_oecd / gap_to_oecd_mean,
    # passamos esses campos EXPLICITAMENTE no payload para o LLM nao
    # precisar recalcular (e nao alucinar). O mart_br_vs_ocde__*
    # publica esses campos em `primary_meta` via Retriever.
    precomputed_metrics: dict[str, float] = {}
    meta = retrieved.primary_meta or {}
    for canonical_key in (
        "zscore_in_oecd",
        "percentile_in_oecd",
        "gap_to_oecd_mean",
        "trend_slope",
        "countries_in_oecd",
    ):
        if canonical_key in meta and meta[canonical_key] is not None:
            try:
                precomputed_metrics[canonical_key] = float(meta[canonical_key])
            except (TypeError, ValueError):
                continue

    return run_single_agent_task(
        build_statistician(),
        description=(
            "Receba o RetrievedData abaixo e produza um StatAnalysis. "
            "Se o indicador for PISA/TIMSS/PIRLS, retorne method="
            "plausible_values_pending.\n\n"
            "IMPORTANTE: quando `precomputed_metrics` esta populado (vem "
            "do mart Gold), INCLUA esses campos em `key_metrics` e em "
            "`focus_country_position` em vez de recalcular. Esses valores "
            "passaram por dbt tests e sao a verdade canonica."
        ),
        output_schema=StatAnalysis,
        payload={
            "question": core.question,
            "entities": core.entities.model_dump(),
            "retrieved": retrieved.model_dump(),
            "precomputed_metrics": precomputed_metrics,
        },
    )


def _run_comparativist(
    core: CoreFlowOutput,
    retrieved: RetrievedData,
    stats: StatAnalysis,
    rag_client: RagClient | None,
) -> ComparativeContext:
    return run_single_agent_task(
        build_comparativist(client=rag_client),
        description=(
            "Receba os dados, estatisticas e contexto da pergunta. Use a "
            "tool rag_search para fundamentar afirmacoes em literatura "
            "academica. Produza um ComparativeContext."
        ),
        output_schema=ComparativeContext,
        payload={
            "question": core.question,
            "intent": core.intent.model_dump(),
            "entities": core.entities.model_dump(),
            "retrieved_summary": retrieved.summary,
            "primary_data": retrieved.primary_data,
            "primary_meta": retrieved.primary_meta,
            "stat_analysis": stats.model_dump(),
        },
    )


def _run_citation(
    core: CoreFlowOutput,
    context: ComparativeContext,
    rag_client: RagClient | None,
    *,
    no_guardrails: bool = False,
) -> Citations:
    # QW4 do quality-assessment 2026-05-14: se o RAG local esta vazio,
    # devolver Citations vazio com nota honesta — em vez de deixar o LLM
    # alucinar DOIs. O Citation Agent custa ~1 chamada de LLM por
    # pergunta; pular quando nao ha como fundamentar elimina o risco.
    if rag_client is not None:
        try:
            n_docs = rag_client.count()
        except Exception:  # noqa: BLE001 — tolera client sem count()
            n_docs = -1
        if n_docs == 0:
            log.warning("agents.citation.rag_empty_skip")
            return Citations(
                items=[],
                query_used=core.question,
                notes=[
                    "RAG local vazio — citacoes nao disponiveis nesta sessao. "
                    "Para habilitar, popule data/chromadb/edu_literature/ "
                    "com referencias reais (MP1 do quality plan)."
                ],
            )

    citations = run_single_agent_task(
        build_citation(client=rag_client),
        description=(
            "Para a pergunta e narrativa abaixo, selecione 2-5 referencias "
            "REAIS via rag_search e cite_resolve. Retorne JSON Citations. "
            "PROIBIDO: DOIs com 'xxxx', 'yyyy', placeholder, abcd, 1234. "
            "Use SOMENTE DOIs retornados pelas tools rag_search/cite_resolve."
        ),
        output_schema=Citations,
        payload={
            "question": core.question,
            "narrative": context.narrative,
            "key_findings": context.key_findings,
            "country_groups_compared": context.country_groups_compared,
        },
    )

    # Pos-processamento: filtra DOIs placeholder (10.xxxx/..., 10.yyyy/...,
    # etc) que LLMs locais emitem quando nao tem certeza. `is_real_doi`
    # checa formato + lista negra de sufixos. Mantemos as citacoes SEM
    # DOI (titulo + autores podem ser uteis), mas zeramos o `doi`.
    # Quando `no_guardrails=True` (baseline), mantemos a saida pura do LLM.
    if no_guardrails:
        return citations
    filtered_items = []
    placeholders_removed = 0
    for cit in citations.items:
        if cit.doi and not is_real_doi(cit.doi):
            placeholders_removed += 1
            cit.doi = None
        filtered_items.append(cit)
    citations.items = filtered_items
    if placeholders_removed > 0:
        msg = (
            f"{placeholders_removed} cita(coes) tiveram DOI placeholder "
            "removido (formato 10.xxxx/...). Titulos/autores foram mantidos "
            "para inspecao mas trate como nao-validados."
        )
        log.warning("agents.citation.placeholders_filtered", count=placeholders_removed)
        citations.notes = list(citations.notes) + [msg]
    return citations


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
      - Trace por etapa em Langfuse (quando configurado).
      - Falha de um agente nao quebra o pipeline inteiro — a etapa
        seguinte recebe o erro como parte do contexto.
    """
    log.info(
        "agents.analysis_crew.start",
        question=core.question[:120],
        flow=core.intent.flow,
    )
    retrieved = _run_retriever(core, gateway_client)
    log.info(
        "agents.analysis_crew.retriever_done",
        calls=len(retrieved.tool_calls),
        primary_data_rows=len(retrieved.primary_data or []),
        primary_meta_keys=list((retrieved.primary_meta or {}).keys()),
    )

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
