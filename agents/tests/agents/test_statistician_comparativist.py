"""Sprint 5.3 — testes Statistician + Comparativist (LLM mockado)."""

from __future__ import annotations

import pytest
from crewai import Crew, Process, Task

from src.agents import build_comparativist, build_statistician
from src.schemas import (
    ComparativeContext,
    CountryPosition,
    StatAnalysis,
)


STATISTICIAN_ROLE = "Analista estatistico de educacao comparada"
COMPARATIVIST_ROLE = (
    "Especialista em educacao comparada Brasil-Internacional"
)


@pytest.fixture(autouse=True)
def _fake_anthropic_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-fake")


# ----------------------------------------------------------------------
# Build factories
# ----------------------------------------------------------------------


def test_build_statistician_loads_prompt_and_tool():
    agent = build_statistician()
    assert agent.role == STATISTICIAN_ROLE
    assert "Plausible Values" in agent.backstory
    assert "z-score" in agent.backstory
    tool_names = [t.name for t in agent.tools]
    assert "compute_stats" in tool_names


def test_build_comparativist_loads_prompt_with_rag_tool():
    """Sprint 5.5 acoplou RAGSearchTool ao Comparativist."""
    agent = build_comparativist()
    assert agent.role == COMPARATIVIST_ROLE
    assert "PNE" in agent.backstory or "Plano Nacional" in agent.backstory
    assert "PIAAC" in agent.backstory  # menciona alertas metodologicos
    tool_names = [t.name for t in agent.tools]
    assert "rag_search" in tool_names
    # CiteResolveTool fica APENAS com Citation Agent
    assert "cite_resolve" not in tool_names


# ----------------------------------------------------------------------
# Statistician — caixa preta
# ----------------------------------------------------------------------


def _stat_task(agent, retrieved_summary: str) -> Task:
    return Task(
        description=(
            f"Recebeu RetrievedData com 4 paises em GASTO_EDU_PIB 2020. "
            f"{retrieved_summary} Produza um StatAnalysis."
        ),
        expected_output="JSON StatAnalysis",
        output_pydantic=StatAnalysis,
        agent=agent,
    )


def test_statistician_returns_stat_analysis(mock_llm_call):
    agent = build_statistician()
    expected = StatAnalysis(
        method="agregados",
        indicator="GASTO_EDU_PIB",
        period="2020",
        sample_size=4,
        key_metrics={
            "mean": 5.75,
            "median": 5.91,
            "stddev": 0.81,
            "min": 4.50,
            "max": 6.68,
            "cv": 0.14,
        },
        focus_country_position=CountryPosition(
            country_iso3="BRA",
            value=5.77,
            zscore=0.025,
            percentile=0.5,
            gap_to_mean=0.02,
            rank=2,
        ),
        other_positions=[
            CountryPosition(country_iso3="FIN", value=6.68, rank=1),
            CountryPosition(country_iso3="USA", value=6.05, rank=3),
            CountryPosition(country_iso3="MEX", value=4.50, rank=4),
        ],
        warnings=[],
        confidence_note=(
            "Comparacao agregada com N=4 paises (BR + 3 OCDE), "
            "fonte World Bank 2020."
        ),
    )
    mock_llm_call(by_role={STATISTICIAN_ROLE: expected.model_dump_json()})

    crew = Crew(
        agents=[agent],
        tasks=[_stat_task(agent, "BR=5.77, FIN=6.68, USA=6.05, MEX=4.50.")],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    output = crew.tasks[0].output.pydantic
    assert isinstance(output, StatAnalysis)
    assert output.sample_size == 4
    assert output.focus_country_position.country_iso3 == "BRA"
    assert output.method == "agregados"


def test_statistician_refuses_pisa_without_pv(mock_llm_call):
    """Pergunta sobre PISA: agente deve retornar method=plausible_values_pending."""
    agent = build_statistician()
    expected = StatAnalysis(
        method="plausible_values_pending",
        indicator=None,
        sample_size=0,
        warnings=[
            "PISA requer Plausible Values + BRR/Jackknife — metodologia "
            "ainda nao implementada no sistema."
        ],
        confidence_note=(
            "Analise nao executada: aguardando implementacao de Plausible "
            "Values para microdados PISA/TIMSS/PIRLS."
        ),
    )
    mock_llm_call(by_role={STATISTICIAN_ROLE: expected.model_dump_json()})

    crew = Crew(
        agents=[agent],
        tasks=[_stat_task(agent, "Pergunta sobre ranking PISA 2022.")],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    output = crew.tasks[0].output.pydantic
    assert output.method == "plausible_values_pending"
    assert output.sample_size == 0
    assert any("Plausible Values" in w for w in output.warnings)


# ----------------------------------------------------------------------
# Comparativist — caixa preta
# ----------------------------------------------------------------------


def _comp_task(agent, hint: str) -> Task:
    return Task(
        description=(
            f"Recebeu StatAnalysis e RetrievedData. {hint} Produza um "
            f"ComparativeContext com narrativa, key_findings, "
            f"historical_context e methodological_caveats."
        ),
        expected_output="JSON ComparativeContext",
        output_pydantic=ComparativeContext,
        agent=agent,
    )


def test_comparativist_returns_narrative(mock_llm_call):
    agent = build_comparativist()
    expected = ComparativeContext(
        narrative=(
            "No periodo de 2020, o Brasil aplicou 5.77% do PIB em educacao "
            "(World Bank), valor bastante proximo da media OCDE de 5.75%. "
            "Em comparacao com pais de referencia em performance educacional "
            "como a Finlandia (6.68%), o Brasil fica 0.91 ponto percentual "
            "atras. Mexico (4.50%) e EUA (6.05%) compoem o universo de "
            "comparacao."
        ),
        key_findings=[
            "BR investe 5.77% PIB em educacao, +0.02pp acima da media de N=4 paises (2020).",
            "FIN lidera com 6.68% — gap de 0.91pp em relacao ao BR.",
            "MEX com 4.50% e o menor entre os comparados.",
        ],
        historical_context=(
            "PNE (Lei 13.005/2014) meta 20: alcancar gasto >= 7% PIB ate 2024. "
            "Meta nao atingida — patamar do BR oscila entre 5-6% PIB nos "
            "anos recentes."
        ),
        methodological_caveats=[
            "Comparacao com N=4 paises e ilustrativa, nao representa OCDE como um todo.",
            "Diferenca sistematica entre WB e OECD (~1pp) — usar fonte unica para tendencia.",
        ],
        country_groups_compared=["BRA", "FIN", "USA", "MEX"],
    )
    mock_llm_call(by_role={COMPARATIVIST_ROLE: expected.model_dump_json()})

    crew = Crew(
        agents=[agent],
        tasks=[_comp_task(agent, "BR esta na media de N=4 paises (gasto 2020).")],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    output = crew.tasks[0].output.pydantic
    assert isinstance(output, ComparativeContext)
    assert "PNE" in output.historical_context
    assert len(output.key_findings) >= 3
    assert "BRA" in output.country_groups_compared


def test_comparativist_includes_methodological_caveat_for_pisa(mock_llm_call):
    """Quando StatAnalysis veio com plausible_values_pending, o
    Comparativist deve refletir isso na narrativa e nos caveats."""
    agent = build_comparativist()
    expected = ComparativeContext(
        narrative=(
            "Nao ha analise estatistica disponivel para PISA neste momento, "
            "pois o sistema ainda nao implementa Plausible Values + BRR/"
            "Jackknife — metodologia obrigatoria para microdados PISA, "
            "TIMSS e PIRLS."
        ),
        key_findings=[
            "Sistema atual cobre apenas indicadores agregados (GASTO_EDU_PIB, LITERACY_15M).",
            "Resultados PISA ficam pendentes ate Sprint 5+ implementar metodologia adequada.",
        ],
        historical_context=(
            "BR participa do PISA desde 2000. Comparacoes longitudinais "
            "exigem ressalvas sobre mudancas de framework do programa OCDE."
        ),
        methodological_caveats=[
            "Microdados PISA/TIMSS/PIRLS exigem Plausible Values (10 PVs + BRR/Jackknife).",
            "BR nao participa de PIAAC nem ICILS — usar INAF e TIC Educacao como analogos.",
        ],
        country_groups_compared=["BRA"],
    )
    mock_llm_call(by_role={COMPARATIVIST_ROLE: expected.model_dump_json()})

    crew = Crew(
        agents=[agent],
        tasks=[_comp_task(agent, "Statistician retornou plausible_values_pending.")],
        process=Process.sequential,
        verbose=False,
    )
    crew.kickoff()
    output = crew.tasks[0].output.pydantic
    assert any("Plausible Values" in c for c in output.methodological_caveats)
    assert any("PIAAC" in c for c in output.methodological_caveats)
