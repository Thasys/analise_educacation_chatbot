"""Visualization Agent — gera VizSpec (Plotly figure dict).

LLM: Haiku 4.5 (decisao de chart type + parametros). A geracao do
figure dict e delegada a `MakePlotlySpecTool` ou inferida diretamente
pelo agente seguindo o schema Plotly.js.
"""

from __future__ import annotations

from crewai import Agent

from src.agents._prompt_loader import load_prompt
from src.llm import make_llm
from src.tools.viz_tools import MakePlotlySpecTool


def build_visualizer() -> Agent:
    return Agent(
        role="Especialista em visualizacao de dados educacionais",
        goal=(
            "Gerar especificacao Plotly (chart_type + figure dict + "
            "metadados) coerente com o tipo de pergunta, destacando o "
            "Brasil quando aplicavel."
        ),
        backstory=load_prompt("visualizer_system"),
        llm=make_llm("fast"),
        tools=[MakePlotlySpecTool()],
        allow_delegation=False,
        verbose=False,
        max_iter=3,
    )
