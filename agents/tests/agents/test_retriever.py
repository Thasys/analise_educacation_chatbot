"""Sprint 5.2 — testes do Data Retrieval Agent.

Cobre:
1. build_retriever() acopla as 4 tools.
2. Tools usam o client injetado (mock).
3. Execucao via Crew com LLM mockado retornando RetrievedData direto
   (estrategia "agente como caixa-preta" — testes de tool-call loop
   ficam para suite live em Sprint 5.6).
"""

from __future__ import annotations

import pytest
from crewai import Crew, Process, Task

from src.agents.retriever import build_retriever
from src.api_client import EduGatewayClient
from src.schemas import RetrievedData, ToolCallRecord


RETRIEVER_ROLE = "Recuperador de dados educacionais comparados"


@pytest.fixture(autouse=True)
def _fake_anthropic_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-fake")


# ----------------------------------------------------------------------
# build_retriever
# ----------------------------------------------------------------------


def test_build_retriever_has_4_tools(gateway_handler_factory):
    transport = gateway_handler_factory({})
    client = EduGatewayClient(transport=transport)
    agent = build_retriever(client=client)
    assert agent.role == RETRIEVER_ROLE
    tool_names = sorted(t.name for t in agent.tools)
    assert tool_names == [
        "data_catalog",
        "data_compare",
        "data_ranking",
        "data_timeseries",
    ]


def test_build_retriever_loads_prompt(gateway_handler_factory):
    transport = gateway_handler_factory({})
    client = EduGatewayClient(transport=transport)
    agent = build_retriever(client=client)
    # Backstory veio de prompts/retriever_system.txt
    assert "data_compare" in agent.backstory
    assert "data_timeseries" in agent.backstory
    assert "GASTO_EDU_PIB" in agent.backstory


# ----------------------------------------------------------------------
# Crew execution com LLM mockado
# ----------------------------------------------------------------------


def _retriever_task(agent, question: str) -> Task:
    return Task(
        description=(
            f"Pergunta do usuario: \"{question}\". Recupere os dados "
            f"necessarios chamando as tools apropriadas. Retorne um JSON "
            f"conforme o schema RetrievedData."
        ),
        expected_output="JSON RetrievedData (summary, tool_calls, primary_data, primary_meta, warnings).",
        output_pydantic=RetrievedData,
        agent=agent,
    )


def test_retriever_returns_compare_result(
    mock_llm_call, gateway_handler_factory, sample_compare_payload
):
    transport = gateway_handler_factory(
        {("POST", "/api/data/compare"): {"status": 200, "json": sample_compare_payload}}
    )
    client = EduGatewayClient(transport=transport)
    agent = build_retriever(client=client)

    expected = RetrievedData(
        summary="Comparacao Brasil vs Finlandia em gasto educacional 2020 (4 paises).",
        tool_calls=[
            ToolCallRecord(
                tool="data_compare",
                arguments={
                    "indicator": "GASTO_EDU_PIB",
                    "countries": ["BRA", "FIN", "USA", "MEX"],
                    "year": 2020,
                },
                status="ok",
                rows_returned=4,
                sources=["worldbank"],
            )
        ],
        primary_data=sample_compare_payload["data"],
        primary_meta=sample_compare_payload["meta"],
    )

    mock_llm_call(by_role={RETRIEVER_ROLE: expected.model_dump_json()})

    crew = Crew(
        agents=[agent],
        tasks=[_retriever_task(agent, "BR vs FIN em gasto educacional 2020")],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    output = crew.tasks[0].output.pydantic
    assert isinstance(output, RetrievedData)
    assert output.tool_calls[0].tool == "data_compare"
    assert output.tool_calls[0].rows_returned == 4
    assert output.primary_data[0]["country_iso3"] == "BRA"


def test_retriever_handles_unknown_indicator(mock_llm_call, gateway_handler_factory):
    """Pergunta sobre PISA (indicador nao publicado): agente devolve
    summary explicativo SEM chamar tools."""
    transport = gateway_handler_factory({})
    client = EduGatewayClient(transport=transport)
    agent = build_retriever(client=client)

    expected = RetrievedData(
        summary=(
            "Indicador PISA ainda nao publicado na Silver. Nenhuma tool "
            "foi invocada — o sistema atual cobre GASTO_EDU_PIB e "
            "LITERACY_15M."
        ),
        tool_calls=[],
        primary_data=[],
        primary_meta={},
        warnings=["indicador_nao_publicado:PISA"],
    )
    mock_llm_call(by_role={RETRIEVER_ROLE: expected.model_dump_json()})

    crew = Crew(
        agents=[agent],
        tasks=[_retriever_task(agent, "Onde o BR aparece no PISA 2022?")],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    output = crew.tasks[0].output.pydantic
    assert output.tool_calls == []
    assert "indicador_nao_publicado:PISA" in output.warnings


def test_retriever_chains_two_tool_calls(
    mock_llm_call, gateway_handler_factory, sample_timeseries_payload
):
    """Pergunta com 2 cortes: agente registra 2 tool_calls."""
    transport = gateway_handler_factory(
        {
            ("POST", "/api/data/timeseries"): {
                "status": 200,
                "json": sample_timeseries_payload,
            }
        }
    )
    client = EduGatewayClient(transport=transport)
    agent = build_retriever(client=client)

    expected = RetrievedData(
        summary="Evolucao BRA gasto + ranking OCDE.",
        tool_calls=[
            ToolCallRecord(
                tool="data_timeseries",
                arguments={
                    "indicator": "GASTO_EDU_PIB",
                    "country_iso3": "BRA",
                    "year_start": 2018,
                    "year_end": 2022,
                },
                status="ok",
                rows_returned=5,
                sources=["worldbank"],
            ),
            ToolCallRecord(
                tool="data_ranking",
                arguments={
                    "indicator": "GASTO_EDU_PIB",
                    "grouping": "oecd",
                    "limit": 10,
                },
                status="ok",
                rows_returned=10,
                sources=["worldbank"],
            ),
        ],
        primary_data=sample_timeseries_payload["data"],
        primary_meta=sample_timeseries_payload["meta"],
    )
    mock_llm_call(by_role={RETRIEVER_ROLE: expected.model_dump_json()})

    crew = Crew(
        agents=[agent],
        tasks=[_retriever_task(agent, "BR gasto entre 2018-2022 e top 10 OCDE")],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    output = crew.tasks[0].output.pydantic
    assert len(output.tool_calls) == 2
    assert output.tool_calls[0].tool == "data_timeseries"
    assert output.tool_calls[1].tool == "data_ranking"
