"""Sprint 5.4 — testes Visualizer + Synthesizer + synthesis_crew."""

from __future__ import annotations

import pytest

from src.agents import build_synthesizer, build_visualizer
from src.crews import run_synthesis_flow
from src.schemas import (
    ComparativeContext,
    CoreFlowOutput,
    EntityExtraction,
    FinalAnswer,
    IntentDecision,
    RetrievedData,
    StatAnalysis,
    VizSpec,
)


VIZ_ROLE = "Especialista em visualizacao de dados educacionais"
SYNTH_ROLE = "Sintetizador de respostas educacionais comparadas"


@pytest.fixture(autouse=True)
def _fake_anthropic_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-fake")


# ----------------------------------------------------------------------
# Build factories
# ----------------------------------------------------------------------


def test_build_visualizer_loads_prompt_and_tool():
    agent = build_visualizer()
    assert agent.role == VIZ_ROLE
    assert "bar_horizontal" in agent.backstory
    assert "line_multi" in agent.backstory
    tool_names = [t.name for t in agent.tools]
    assert "make_plotly_spec" in tool_names


def test_build_synthesizer_loads_prompt_no_tools():
    agent = build_synthesizer()
    assert agent.role == SYNTH_ROLE
    assert "researcher" in agent.backstory
    assert "policy" in agent.backstory
    assert "student" in agent.backstory
    assert agent.tools == []


# ----------------------------------------------------------------------
# Helpers para tests
# ----------------------------------------------------------------------


def _build_inputs():
    core = CoreFlowOutput(
        question="Como BR se compara com FIN em gasto educacional 2020?",
        intent=IntentDecision(
            flow="data",
            profile="researcher",
            reasoning="Pergunta com dados, linguagem tecnica.",
            confidence=0.9,
        ),
        entities=EntityExtraction(
            indicator="GASTO_EDU_PIB",
            countries=["BRA", "FIN"],
            year=2020,
            reasoning="ok",
        ),
    )
    retrieved = RetrievedData(
        summary="Comparacao BR vs FIN em gasto 2020.",
        primary_data=[
            {"country_iso3": "BRA", "value": 5.77},
            {"country_iso3": "FIN", "value": 6.68},
        ],
        primary_meta={"sources": ["worldbank"], "total_rows": 2},
    )
    stats = StatAnalysis(
        method="agregados",
        indicator="GASTO_EDU_PIB",
        period="2020",
        sample_size=2,
        key_metrics={"mean": 6.225, "median": 6.225, "stddev": 0.64,
                     "min": 5.77, "max": 6.68, "cv": 0.103},
        confidence_note="Comparacao bilateral (N=2), fonte WB 2020.",
    )
    context = ComparativeContext(
        narrative="No periodo de 2020, o Brasil aplicou 5.77% PIB em educacao...",
        key_findings=["BR 5.77% PIB", "FIN 6.68% PIB", "gap -0.91pp"],
        country_groups_compared=["BRA", "FIN"],
    )
    return core, retrieved, stats, context


# ----------------------------------------------------------------------
# run_synthesis_flow E2E (com mock LLM)
# ----------------------------------------------------------------------


def test_synthesis_flow_produces_viz_and_final(mock_llm_call):
    core, retrieved, stats, context = _build_inputs()

    viz = VizSpec(
        chart_type="bar_vertical",
        title="Gasto publico em educacao (% PIB) — Brasil vs Finlandia, 2020",
        plotly_figure={
            "data": [
                {
                    "type": "bar",
                    "x": ["BRA", "FIN"],
                    "y": [5.77, 6.68],
                    "marker": {"color": ["#c0392b", "#2c3e50"]},
                }
            ],
            "layout": {"title": {"text": "Gasto 2020"}},
        },
        sources=["worldbank"],
        notes=["Cobertura: BR + FIN. Fonte: World Bank 2020."],
    )

    final = FinalAnswer(
        markdown=(
            "# Gasto educacional Brasil x Finlandia (2020)\n\n"
            "Em 2020 o Brasil aplicou **5.77% do PIB** em educacao "
            "(World Bank), 0.91 pp abaixo da Finlandia (6.68%).\n\n"
            "## Achados-chave\n"
            "- BR: 5.77% PIB\n- FIN: 6.68% PIB\n- Gap: -0.91 pp\n\n"
            "## Fontes\n- World Bank (2020)"
        ),
        profile_used="researcher",
        flow_used="data",
        sources_cited=["worldbank"],
        visualizations=[viz],
        warnings=[],
        follow_up_suggestions=[
            "Como evoluiu o gasto BR entre 2010 e 2022?",
            "BR vs media OCDE no mesmo ano?",
        ],
    )

    mock_llm_call(
        by_role={
            VIZ_ROLE: viz.model_dump_json(),
            SYNTH_ROLE: final.model_dump_json(),
        }
    )

    out_viz, out_final = run_synthesis_flow(core, retrieved, stats, context)

    assert isinstance(out_viz, VizSpec)
    assert out_viz.chart_type == "bar_vertical"
    assert isinstance(out_final, FinalAnswer)
    assert out_final.profile_used == "researcher"
    assert "Brasil" in out_final.markdown
    assert "World Bank" in out_final.markdown
    assert len(out_final.visualizations) == 1
    assert out_final.visualizations[0].chart_type == "bar_vertical"


def test_synthesis_flow_simple_no_viz(mock_llm_call):
    """Fluxo simple: pergunta conceitual, VizSpec=none, sem tabela."""
    core = CoreFlowOutput(
        question="O que significa ISCED 2011 nivel 2?",
        intent=IntentDecision(
            flow="simple", profile="student", reasoning="conceitual", confidence=0.9
        ),
        entities=EntityExtraction(reasoning="sem entidades"),
    )
    retrieved = RetrievedData(summary="Pergunta conceitual sem dados.")
    stats = StatAnalysis(method="agregados", sample_size=0)
    context = ComparativeContext(
        narrative="ISCED eh padrao da UNESCO; nivel 2 corresponde aos anos finais...",
        country_groups_compared=[],
    )

    viz = VizSpec(
        chart_type="none",
        title="Pergunta conceitual sem visualizacao",
        plotly_figure={"data": [], "layout": {"title": {"text": "Sem dados"}}},
        sources=[],
        notes=[],
    )
    final = FinalAnswer(
        markdown=(
            "# ISCED 2011 nivel 2\n\nA classificacao ISCED da UNESCO define "
            "**nivel 2** como ensino fundamental anos finais (6o ao 9o ano "
            "no Brasil). Eh o padrao internacional para harmonizar "
            "comparacoes entre sistemas educacionais."
        ),
        profile_used="student",
        flow_used="simple",
        sources_cited=["UNESCO ISCED 2011"],
        visualizations=[viz],
    )
    mock_llm_call(
        by_role={
            VIZ_ROLE: viz.model_dump_json(),
            SYNTH_ROLE: final.model_dump_json(),
        }
    )

    out_viz, out_final = run_synthesis_flow(core, retrieved, stats, context)
    assert out_viz.chart_type == "none"
    assert out_final.flow_used == "simple"
    assert out_final.profile_used == "student"


def test_synthesis_flow_policy_profile_mentions_pne(mock_llm_call):
    """Perfil policy: markdown deve referenciar PNE."""
    core, retrieved, stats, context = _build_inputs()
    core = core.model_copy(update={
        "intent": IntentDecision(
            flow="data", profile="policy",
            reasoning="gestor publico", confidence=0.85,
        )
    })
    viz = VizSpec(
        chart_type="bar_vertical",
        title="BR x FIN gasto 2020",
        plotly_figure={"data": [], "layout": {}},
        sources=["worldbank"],
    )
    final = FinalAnswer(
        markdown=(
            "# Gasto educacional 2020\n\nO Brasil investiu **5.8% do PIB** em "
            "educacao (WB), abaixo da meta 20 do **PNE (Lei 13.005/2014)** "
            "que fixava 7% ate 2024."
        ),
        profile_used="policy",
        flow_used="data",
        sources_cited=["worldbank"],
        visualizations=[viz],
    )
    mock_llm_call(
        by_role={
            VIZ_ROLE: viz.model_dump_json(),
            SYNTH_ROLE: final.model_dump_json(),
        }
    )
    _, out_final = run_synthesis_flow(core, retrieved, stats, context)
    assert out_final.profile_used == "policy"
    assert "PNE" in out_final.markdown
