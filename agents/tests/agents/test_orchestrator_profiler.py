"""Sprint 5.1 — Core Crew end-to-end (com LLM mockado).

Cobre o fluxo Orchestrator + Profiler executado pela `run_core_flow`,
sem custo Anthropic. As respostas mock retornam JSON valido conforme
schemas IntentDecision e EntityExtraction.
"""

from __future__ import annotations

import json

import pytest

from src.agents import build_orchestrator, build_profiler
from src.crews.core_crew import run_core_flow
from src.schemas import EntityExtraction, IntentDecision

ORCHESTRATOR_ROLE = "Orchestrator de roteamento educacional"
PROFILER_ROLE = "Extrator de entidades educacionais"


@pytest.fixture(autouse=True)
def _fake_anthropic_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-fake")


# ----------------------------------------------------------------------
# Build factories
# ----------------------------------------------------------------------


def test_build_orchestrator_loads_prompt():
    agent = build_orchestrator()
    assert agent.role == ORCHESTRATOR_ROLE
    # backstory deve ter conteudo carregado de prompts/orchestrator_system.txt
    assert "simple" in agent.backstory and "data" in agent.backstory
    assert agent.allow_delegation is False


def test_build_profiler_loads_prompt():
    agent = build_profiler()
    assert agent.role == PROFILER_ROLE
    assert "GASTO_EDU_PIB" in agent.backstory
    assert "ISO-3" in agent.backstory


# ----------------------------------------------------------------------
# Core flow happy paths — 3 perfis x 3 fluxos
# ----------------------------------------------------------------------


def test_core_flow_data_researcher(mock_llm_call):
    intent = IntentDecision(
        flow="data",
        profile="researcher",
        reasoning="Pergunta solicita comparacao numerica entre paises com referencia a metodologia.",
        confidence=0.92,
    )
    entities = EntityExtraction(
        indicator="GASTO_EDU_PIB",
        countries=["BRA", "FIN"],
        year=2022,
        reasoning="Indicador 'gasto educacional' -> GASTO_EDU_PIB; paises Brasil e Finlandia.",
    )
    mock_llm_call(
        by_role={
            ORCHESTRATOR_ROLE: intent.model_dump_json(),
            PROFILER_ROLE: entities.model_dump_json(),
        }
    )

    result = run_core_flow(
        "Como o Brasil se compara com a Finlandia em gasto educacional em 2022, "
        "controlando por intervalos de confianca?"
    )

    assert result.intent.flow == "data"
    assert result.intent.profile == "researcher"
    assert result.intent.confidence == pytest.approx(0.92)
    assert result.entities.indicator == "GASTO_EDU_PIB"
    assert result.entities.countries == ["BRA", "FIN"]
    assert result.entities.year == 2022


def test_core_flow_simple_student(mock_llm_call):
    intent = IntentDecision(
        flow="simple",
        profile="student",
        reasoning="Pergunta conceitual sem mencao a dados; linguagem informal.",
        confidence=0.88,
    )
    entities = EntityExtraction(
        indicator=None,
        countries=[],
        reasoning="Pergunta conceitual sem entidades quantitativas.",
    )
    mock_llm_call(
        by_role={
            ORCHESTRATOR_ROLE: intent.model_dump_json(),
            PROFILER_ROLE: entities.model_dump_json(),
        }
    )

    result = run_core_flow("O que eh ISCED, tipo, no geral?")

    assert result.intent.flow == "simple"
    assert result.intent.profile == "student"
    assert result.entities.indicator is None
    assert result.entities.countries == []


def test_core_flow_deep_policy(mock_llm_call):
    intent = IntentDecision(
        flow="deep",
        profile="policy",
        reasoning="Pergunta causal multifator de gestor; requer literatura.",
        confidence=0.81,
    )
    entities = EntityExtraction(
        indicator="GASTO_EDU_PIB",
        countries=["BRA"],
        grouping="oecd",
        year_start=2010,
        year_end=2022,
        reasoning="Indicador investimento -> GASTO_EDU_PIB; comparacao com OCDE; janela 2010-2022.",
    )
    mock_llm_call(
        by_role={
            ORCHESTRATOR_ROLE: intent.model_dump_json(),
            PROFILER_ROLE: entities.model_dump_json(),
        }
    )

    result = run_core_flow(
        "Por que o investimento educacional brasileiro nao se traduz em "
        "resultados comparaveis aos da OCDE entre 2010 e 2022?"
    )

    assert result.intent.flow == "deep"
    assert result.intent.profile == "policy"
    assert result.entities.grouping == "oecd"
    assert result.entities.year_start == 2010 and result.entities.year_end == 2022


# ----------------------------------------------------------------------
# Robustez — JSON em string deve ser parseado mesmo se output_pydantic falhar
# ----------------------------------------------------------------------


def test_core_flow_handles_raw_string_output(mock_llm_call, monkeypatch):
    """Mesmo se a CrewAI nao popular output.pydantic (caso de fallback),
    `run_core_flow` deve coalescer string JSON via _coerce_*.
    """
    intent_payload = json.dumps(
        {
            "flow": "data",
            "profile": "policy",
            "reasoning": "ok",
            "confidence": 0.7,
        }
    )
    entities_payload = json.dumps(
        {
            "indicator": "LITERACY_15M",
            "countries": ["BRA"],
            "grouping": "latam",
            "reasoning": "alfab + LATAM",
        }
    )
    mock_llm_call(
        by_role={
            ORCHESTRATOR_ROLE: intent_payload,
            PROFILER_ROLE: entities_payload,
        }
    )
    result = run_core_flow("Como esta a alfabetizacao do Brasil em LATAM?")
    assert result.intent.flow == "data"
    assert result.entities.indicator == "LITERACY_15M"
    assert result.entities.grouping == "latam"
