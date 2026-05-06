"""Sprint 5.5 — Citation Agent (caixa-preta com mock LLM)."""

from __future__ import annotations

import pytest
from crewai import Crew, Process, Task

from src.agents import build_citation, build_comparativist
from src.schemas import Citation, Citations


CITATION_ROLE = "Curador de evidencias academicas em educacao comparada"
COMPARATIVIST_ROLE = (
    "Especialista em educacao comparada Brasil-Internacional"
)


@pytest.fixture(autouse=True)
def _fake_anthropic_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-fake")


# ----------------------------------------------------------------------
# Build factories
# ----------------------------------------------------------------------


def test_build_citation_loads_prompt_and_tools(rag_client_in_memory):
    agent = build_citation(client=rag_client_in_memory)
    assert agent.role == CITATION_ROLE
    assert "rag_search" in agent.backstory
    assert "DOI" in agent.backstory
    tool_names = sorted(t.name for t in agent.tools)
    assert tool_names == ["cite_resolve", "rag_search"]


def test_build_comparativist_now_has_rag_tool(rag_client_in_memory):
    """Sprint 5.5 atualizou Comparativist para acoplar RAGSearchTool."""
    agent = build_comparativist(client=rag_client_in_memory)
    tool_names = [t.name for t in agent.tools]
    assert "rag_search" in tool_names
    # CiteResolveTool fica APENAS com Citation Agent
    assert "cite_resolve" not in tool_names


# ----------------------------------------------------------------------
# Citation flow caixa-preta
# ----------------------------------------------------------------------


def _citation_task(agent, hint: str) -> Task:
    return Task(
        description=(
            f"Pergunta original: 'Como o Brasil se compara com a OCDE em "
            f"gasto educacional?'. Contexto: {hint}. Use rag_search e "
            f"cite_resolve para selecionar 2-3 referencias REAIS do RAG. "
            f"Retorne JSON Citations."
        ),
        expected_output="JSON Citations com items (DOIs reais), query_used.",
        output_pydantic=Citations,
        agent=agent,
    )


def test_citation_returns_real_dois_from_rag(mock_llm_call, rag_client_in_memory):
    agent = build_citation(client=rag_client_in_memory)

    expected = Citations(
        items=[
            Citation(
                doi="10.1162/REST_a_00081",
                title="The Economics of International Differences in Educational Achievement",
                authors=["Hanushek, Eric A.", "Woessmann, Ludger"],
                year=2011,
                journal="Economic Policy",
                snippet=(
                    "Diferencas em desempenho educacional internacional "
                    "explicam crescimento de longo prazo; aumentos de gasto "
                    "sem reformas raramente convertem em ganhos."
                ),
                relevance_score=0.85,
                source="nber",
            ),
            Citation(
                doi="10.1787/c00cad36-en",
                title="Education at a Glance 2024 — OECD Indicators",
                authors=["OECD"],
                year=2024,
                journal="OECD Publishing",
                snippet=(
                    "Compendio anual de indicadores comparativos OCDE: "
                    "gasto, acesso ISCED, desempenho. Brasil como pais parceiro."
                ),
                relevance_score=0.78,
                source="oecd",
            ),
        ],
        query_used="Brazil education spending OECD comparison",
        notes=[],
    )
    mock_llm_call(by_role={CITATION_ROLE: expected.model_dump_json()})

    crew = Crew(
        agents=[agent],
        tasks=[_citation_task(agent, "BR investe ~5.6% PIB, OCDE media ~5.0%.")],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    output = crew.tasks[0].output.pydantic
    assert isinstance(output, Citations)
    assert len(output.items) == 2
    dois = [c.doi for c in output.items]
    assert "10.1162/REST_a_00081" in dois  # Hanushek-Woessmann
    assert "10.1787/c00cad36-en" in dois  # OECD EAG 2024


def test_citation_empty_when_no_relevant_papers(mock_llm_call, rag_client_in_memory):
    """Pergunta exotica: agente devolve items=[] com nota explicativa."""
    agent = build_citation(client=rag_client_in_memory)
    expected = Citations(
        items=[],
        query_used="quantum computing primary school Brazil",
        notes=[
            "Nenhum paper na colecao seed cobre o tema; sugerir expansao do "
            "manifest YAML."
        ],
    )
    mock_llm_call(by_role={CITATION_ROLE: expected.model_dump_json()})

    crew = Crew(
        agents=[agent],
        tasks=[_citation_task(agent, "tema fora da cobertura do RAG.")],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    output = crew.tasks[0].output.pydantic
    assert output.items == []
    assert output.notes
