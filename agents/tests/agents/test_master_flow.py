"""Sprint 5.6 — Master Flow (Core -> Analysis -> Synthesis)."""

from __future__ import annotations

import pytest

from src.api_client import EduGatewayClient
from src.crews import run_master
from src.schemas import (
    Citation,
    Citations,
    ComparativeContext,
    CountryPosition,
    EntityExtraction,
    FinalAnswer,
    IntentDecision,
    RetrievedData,
    StatAnalysis,
    ToolCallRecord,
    VizSpec,
)


ORCHESTRATOR_ROLE = "Orchestrator de roteamento educacional"
PROFILER_ROLE = "Extrator de entidades educacionais"
RETRIEVER_ROLE = "Recuperador de dados educacionais comparados"
STATISTICIAN_ROLE = "Analista estatistico de educacao comparada"
COMPARATIVIST_ROLE = (
    "Especialista em educacao comparada Brasil-Internacional"
)
CITATION_ROLE = "Curador de evidencias academicas em educacao comparada"
VIZ_ROLE = "Especialista em visualizacao de dados educacionais"
SYNTH_ROLE = "Sintetizador de respostas educacionais comparadas"


@pytest.fixture(autouse=True)
def _fake_anthropic_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-fake")


# ----------------------------------------------------------------------
# Fluxo `data` — caminho default mais comum
# ----------------------------------------------------------------------


def test_run_master_data_flow_full_pipeline(
    mock_llm_call,
    gateway_handler_factory,
    sample_compare_payload,
    rag_client_in_memory,
):
    transport = gateway_handler_factory(
        {("POST", "/api/data/compare"): {"status": 200, "json": sample_compare_payload}}
    )
    gateway_client = EduGatewayClient(transport=transport)

    intent = IntentDecision(
        flow="data", profile="researcher",
        reasoning="comparacao numerica", confidence=0.9,
    )
    entities = EntityExtraction(
        indicator="GASTO_EDU_PIB",
        countries=["BRA", "FIN", "USA", "MEX"],
        year=2020,
        reasoning="ok",
    )
    retrieved = RetrievedData(
        summary="Comparacao 4 paises gasto 2020.",
        tool_calls=[
            ToolCallRecord(
                tool="data_compare",
                arguments={"indicator": "GASTO_EDU_PIB",
                           "countries": ["BRA", "FIN", "USA", "MEX"], "year": 2020},
                status="ok",
                rows_returned=4,
                sources=["worldbank"],
            )
        ],
        primary_data=sample_compare_payload["data"],
        primary_meta=sample_compare_payload["meta"],
    )
    stats = StatAnalysis(
        method="agregados",
        indicator="GASTO_EDU_PIB",
        period="2020",
        sample_size=4,
        key_metrics={"mean": 5.75, "median": 5.91, "stddev": 0.81,
                     "min": 4.50, "max": 6.68, "cv": 0.14},
        focus_country_position=CountryPosition(
            country_iso3="BRA", value=5.77, zscore=0.025,
            percentile=0.5, gap_to_mean=0.02, rank=2,
        ),
        confidence_note="N=4 paises (BR + 3 OCDE), WB 2020.",
    )
    context = ComparativeContext(
        narrative="BR investe 5.77% PIB em 2020, na media do conjunto.",
        key_findings=["BR 5.77%", "FIN 6.68%", "Gap -0.91pp"],
        country_groups_compared=["BRA", "FIN", "USA", "MEX"],
    )
    citations = Citations(
        items=[
            Citation(
                doi="10.1162/REST_a_00081",
                title="The Economics of International Differences in Educational Achievement",
                authors=["Hanushek, Eric A.", "Woessmann, Ludger"],
                year=2011, journal="Economic Policy",
                snippet="Diferencas internacionais explicam crescimento.",
                relevance_score=0.85, source="nber",
            )
        ],
        query_used="Brazil OECD education spending",
    )
    viz = VizSpec(
        chart_type="bar_vertical",
        title="Gasto publico em educacao (% PIB) — 2020",
        plotly_figure={"data": [{"type": "bar", "x": ["BRA", "FIN", "USA", "MEX"],
                                  "y": [5.77, 6.68, 6.05, 4.50]}],
                       "layout": {"title": {"text": "Gasto 2020"}}},
        sources=["worldbank"],
    )
    final = FinalAnswer(
        markdown=(
            "# Gasto educacional 2020 — Brasil vs comparados\n\n"
            "BR aplicou **5.77% do PIB** em educacao (World Bank), na media "
            "de 4 paises avaliados. FIN lidera com 6.68%."
        ),
        profile_used="researcher",
        flow_used="data",
        sources_cited=["worldbank"],
        visualizations=[viz],
        # citations vazias aqui — master_flow popula via Citation Agent
    )

    mock_llm_call(
        by_role={
            ORCHESTRATOR_ROLE: intent.model_dump_json(),
            PROFILER_ROLE: entities.model_dump_json(),
            RETRIEVER_ROLE: retrieved.model_dump_json(),
            STATISTICIAN_ROLE: stats.model_dump_json(),
            COMPARATIVIST_ROLE: context.model_dump_json(),
            CITATION_ROLE: citations.model_dump_json(),
            VIZ_ROLE: viz.model_dump_json(),
            SYNTH_ROLE: final.model_dump_json(),
        }
    )

    out = run_master(
        "Compare BR e FIN em gasto educacional 2020.",
        gateway_client=gateway_client,
        rag_client=rag_client_in_memory,
    )
    assert isinstance(out, FinalAnswer)
    assert out.flow_used == "data"
    assert out.profile_used == "researcher"
    assert "World Bank" in out.markdown
    # citations foram populadas pelo master_flow a partir do Citation Agent
    assert len(out.citations) == 1
    assert out.citations[0].doi == "10.1162/REST_a_00081"
    assert len(out.visualizations) == 1
    assert out.visualizations[0].chart_type == "bar_vertical"


# ----------------------------------------------------------------------
# Fluxo `simple` — pula Retriever/Statistician
# ----------------------------------------------------------------------


def test_run_master_simple_flow_skips_data_agents(
    mock_llm_call, rag_client_in_memory
):
    """Para fluxo `simple`, master_flow NAO chama Retriever/Statistician.

    Validamos isso via mock_llm_call: nao configuramos esses roles, e se
    forem chamados, o mock levanta AssertionError.
    """
    intent = IntentDecision(
        flow="simple", profile="student", reasoning="conceitual", confidence=0.92
    )
    entities = EntityExtraction(reasoning="sem entidades quantitativas")
    context = ComparativeContext(
        narrative="ISCED 2011 eh padrao da UNESCO para classificar niveis educacionais.",
        country_groups_compared=[],
    )
    citations = Citations(items=[], query_used="ISCED 2011 standard UNESCO")
    viz = VizSpec(
        chart_type="none",
        title="Pergunta conceitual",
        plotly_figure={"data": [], "layout": {}},
        sources=[],
    )
    final = FinalAnswer(
        markdown="# ISCED 2011\n\nClassificacao internacional...",
        profile_used="student",
        flow_used="simple",
        sources_cited=["UNESCO"],
        visualizations=[viz],
    )

    mock_llm_call(
        by_role={
            ORCHESTRATOR_ROLE: intent.model_dump_json(),
            PROFILER_ROLE: entities.model_dump_json(),
            COMPARATIVIST_ROLE: context.model_dump_json(),
            CITATION_ROLE: citations.model_dump_json(),
            VIZ_ROLE: viz.model_dump_json(),
            SYNTH_ROLE: final.model_dump_json(),
        }
    )

    out = run_master(
        "O que e ISCED 2011?",
        rag_client=rag_client_in_memory,
    )
    assert out.flow_used == "simple"
    assert out.profile_used == "student"
    assert out.visualizations[0].chart_type == "none"


# ----------------------------------------------------------------------
# Citations em FinalAnswer sao SEMPRE populadas pelo Citation Agent
# (nao pelo Synthesizer, mesmo se Synthesizer enviar citations no JSON)
# ----------------------------------------------------------------------


def test_master_flow_emits_events_via_on_event_callback(
    mock_llm_call, rag_client_in_memory
):
    """Sprint 6.1: callback `on_event` recebe eventos por etapa."""
    intent = IntentDecision(
        flow="simple", profile="student", reasoning="conceitual", confidence=0.9
    )
    entities = EntityExtraction(reasoning="ok")
    context = ComparativeContext(narrative="x", country_groups_compared=[])
    citations = Citations(items=[], query_used="q")
    viz = VizSpec(
        chart_type="none", title="x",
        plotly_figure={"data": [], "layout": {}}, sources=[],
    )
    final = FinalAnswer(
        markdown="x", profile_used="student", flow_used="simple",
        sources_cited=[], visualizations=[viz],
    )
    mock_llm_call(
        by_role={
            ORCHESTRATOR_ROLE: intent.model_dump_json(),
            PROFILER_ROLE: entities.model_dump_json(),
            COMPARATIVIST_ROLE: context.model_dump_json(),
            CITATION_ROLE: citations.model_dump_json(),
            VIZ_ROLE: viz.model_dump_json(),
            SYNTH_ROLE: final.model_dump_json(),
        }
    )

    captured: list[dict] = []
    out = run_master(
        "Pergunta conceitual.",
        rag_client=rag_client_in_memory,
        on_event=lambda ev: captured.append(ev),
    )

    assert out.flow_used == "simple"
    types = [ev["type"] for ev in captured]
    # Esperamos pelo menos: flow_started, agent_started/done para Core,
    # Comparativist, Citation, Synthesis, e final_answer no fim.
    assert types[0] == "flow_started"
    assert types[-1] == "final_answer"
    assert "agent_started" in types and "agent_done" in types
    # Final event carrega payload com FinalAnswer serializado
    final_event = captured[-1]
    assert "payload" in final_event
    assert final_event["payload"]["flow_used"] == "simple"
    # Cada evento tem timestamp
    assert all("ts" in ev for ev in captured)


def test_master_flow_callback_exception_does_not_break_pipeline(
    mock_llm_call, rag_client_in_memory
):
    """Falha do consumidor (ex.: SSE conn caiu) NUNCA deve quebrar o pipeline."""
    intent = IntentDecision(
        flow="simple", profile="student", reasoning="ok", confidence=0.9
    )
    entities = EntityExtraction(reasoning="ok")
    context = ComparativeContext(narrative="x", country_groups_compared=[])
    citations = Citations(items=[], query_used="q")
    viz = VizSpec(
        chart_type="none", title="x",
        plotly_figure={"data": [], "layout": {}}, sources=[],
    )
    final = FinalAnswer(
        markdown="x", profile_used="student", flow_used="simple",
        sources_cited=[], visualizations=[viz],
    )
    mock_llm_call(
        by_role={
            ORCHESTRATOR_ROLE: intent.model_dump_json(),
            PROFILER_ROLE: entities.model_dump_json(),
            COMPARATIVIST_ROLE: context.model_dump_json(),
            CITATION_ROLE: citations.model_dump_json(),
            VIZ_ROLE: viz.model_dump_json(),
            SYNTH_ROLE: final.model_dump_json(),
        }
    )

    def _crash(_ev):
        raise RuntimeError("simulated consumer crash")

    out = run_master(
        "Pergunta.",
        rag_client=rag_client_in_memory,
        on_event=_crash,
    )
    # Pipeline atravessou apesar do callback explodir
    assert out.flow_used == "simple"


def test_master_flow_citations_come_from_citation_agent(
    mock_llm_call, rag_client_in_memory
):
    """Mesmo se o Synthesizer mockar citations=[fake], master sobrescreve
    com a saida real do Citation Agent."""
    intent = IntentDecision(flow="simple", profile="policy", reasoning="ok", confidence=0.8)
    entities = EntityExtraction(reasoning="ok")
    context = ComparativeContext(narrative="x", country_groups_compared=[])
    real_citations = Citations(
        items=[
            Citation(
                doi="10.1234/real",
                title="Real Paper",
                authors=["Real, Author"],
                year=2024,
                source="oecd",
            )
        ],
        query_used="real query",
    )
    fake_in_synth = [
        Citation(
            doi="10.1234/fake-injected-by-synth",
            title="Fake — should be overwritten",
            authors=["Fake"],
            year=2025,
        )
    ]
    viz = VizSpec(chart_type="none", title="x",
                   plotly_figure={"data": [], "layout": {}}, sources=[])
    synth_final = FinalAnswer(
        markdown="x",
        profile_used="policy",
        flow_used="simple",
        sources_cited=[],
        visualizations=[viz],
        citations=fake_in_synth,  # injetadas pelo Synthesizer
    )

    mock_llm_call(
        by_role={
            ORCHESTRATOR_ROLE: intent.model_dump_json(),
            PROFILER_ROLE: entities.model_dump_json(),
            COMPARATIVIST_ROLE: context.model_dump_json(),
            CITATION_ROLE: real_citations.model_dump_json(),
            VIZ_ROLE: viz.model_dump_json(),
            SYNTH_ROLE: synth_final.model_dump_json(),
        }
    )

    out = run_master("Pergunta conceitual.", rag_client=rag_client_in_memory)
    assert len(out.citations) == 1
    assert out.citations[0].doi == "10.1234/real"  # nao a fake
