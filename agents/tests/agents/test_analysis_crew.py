"""Sprint 5.6 — Analysis Crew (4 agentes encadeados, mock LLM)."""

from __future__ import annotations

import pytest

from src.api_client import EduGatewayClient
from src.crews import run_analysis_flow
from src.schemas import (
    Citation,
    Citations,
    ComparativeContext,
    CoreFlowOutput,
    CountryPosition,
    EntityExtraction,
    IntentDecision,
    RetrievedData,
    StatAnalysis,
    ToolCallRecord,
)


RETRIEVER_ROLE = "Recuperador de dados educacionais comparados"
STATISTICIAN_ROLE = "Analista estatistico de educacao comparada"
COMPARATIVIST_ROLE = (
    "Especialista em educacao comparada Brasil-Internacional"
)
CITATION_ROLE = "Curador de evidencias academicas em educacao comparada"


@pytest.fixture(autouse=True)
def _fake_anthropic_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-fake")


def test_run_analysis_flow_chains_4_agents(
    mock_llm_call,
    gateway_handler_factory,
    sample_compare_payload,
    rag_client_in_memory,
):
    """Cobre o caminho completo Retriever -> Stat -> Comparativist -> Citation."""
    transport = gateway_handler_factory(
        {("POST", "/api/data/compare"): {"status": 200, "json": sample_compare_payload}}
    )
    gateway_client = EduGatewayClient(transport=transport)

    core = CoreFlowOutput(
        question="Compare BR e FIN em gasto educacional 2020.",
        intent=IntentDecision(
            flow="data", profile="researcher", reasoning="ok", confidence=0.9
        ),
        entities=EntityExtraction(
            indicator="GASTO_EDU_PIB",
            countries=["BRA", "FIN"],
            year=2020,
            reasoning="ok",
        ),
    )

    retrieved = RetrievedData(
        summary="Comparacao BR vs FIN em gasto 2020 (4 paises).",
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
            country_iso3="BRA", value=5.77, zscore=0.025, percentile=0.5,
            gap_to_mean=0.02, rank=2,
        ),
        confidence_note="N=4 paises, fonte WB 2020.",
    )

    context = ComparativeContext(
        narrative="BR investiu 5.77% PIB em educacao em 2020, na media de N=4 paises.",
        key_findings=[
            "BR 5.77% PIB",
            "FIN lider com 6.68% PIB",
            "Gap BR-FIN: 0.91 pp",
        ],
        country_groups_compared=["BRA", "FIN", "USA", "MEX"],
    )

    citations = Citations(
        items=[
            Citation(
                doi="10.1162/REST_a_00081",
                title="The Economics of International Differences in Educational Achievement",
                authors=["Hanushek, Eric A.", "Woessmann, Ludger"],
                year=2011,
                journal="Economic Policy",
                snippet="Diferencas internacionais em desempenho explicam crescimento.",
                relevance_score=0.85,
                source="nber",
            )
        ],
        query_used="Brazil OECD education spending",
    )

    mock_llm_call(
        by_role={
            RETRIEVER_ROLE: retrieved.model_dump_json(),
            STATISTICIAN_ROLE: stats.model_dump_json(),
            COMPARATIVIST_ROLE: context.model_dump_json(),
            CITATION_ROLE: citations.model_dump_json(),
        }
    )

    out_retrieved, out_stats, out_context, out_citations = run_analysis_flow(
        core, gateway_client=gateway_client, rag_client=rag_client_in_memory
    )

    assert out_retrieved.tool_calls[0].tool == "data_compare"
    assert out_stats.method == "agregados"
    assert out_stats.focus_country_position.country_iso3 == "BRA"
    assert "5.77" in out_context.narrative
    assert len(out_citations.items) == 1
    assert out_citations.items[0].doi == "10.1162/REST_a_00081"


def test_run_analysis_flow_handles_pisa_pending(
    mock_llm_call,
    gateway_handler_factory,
    rag_client_in_memory,
):
    """Quando indicador eh PISA: Statistician retorna plausible_values_pending."""
    transport = gateway_handler_factory({})
    gateway_client = EduGatewayClient(transport=transport)

    core = CoreFlowOutput(
        question="Onde BR aparece no PISA 2022?",
        intent=IntentDecision(
            flow="data", profile="researcher", reasoning="ok", confidence=0.85
        ),
        entities=EntityExtraction(
            indicator=None, countries=["BRA"], year=2022,
            reasoning="indicador PISA nao mapeado ao set publicado",
        ),
    )

    retrieved = RetrievedData(
        summary="PISA nao publicado na Silver — sem chamada de tool.",
        warnings=["indicador_nao_publicado:PISA"],
    )
    stats = StatAnalysis(
        method="plausible_values_pending",
        sample_size=0,
        warnings=["PISA requer Plausible Values + BRR/Jackknife — nao implementado."],
    )
    context = ComparativeContext(
        narrative="Sistema atual nao cobre PISA. Use INAF como analogo.",
        country_groups_compared=["BRA"],
        methodological_caveats=[
            "PISA exige Plausible Values + BRR/Jackknife.",
            "BR nao participa de PIAAC nem ICILS.",
        ],
    )
    citations = Citations(items=[], query_used="PISA Brazil methodology")

    mock_llm_call(
        by_role={
            RETRIEVER_ROLE: retrieved.model_dump_json(),
            STATISTICIAN_ROLE: stats.model_dump_json(),
            COMPARATIVIST_ROLE: context.model_dump_json(),
            CITATION_ROLE: citations.model_dump_json(),
        }
    )

    out_retrieved, out_stats, out_context, out_citations = run_analysis_flow(
        core, gateway_client=gateway_client, rag_client=rag_client_in_memory
    )
    assert out_stats.method == "plausible_values_pending"
    assert "Plausible Values" in out_context.methodological_caveats[0]
    assert out_citations.items == []
