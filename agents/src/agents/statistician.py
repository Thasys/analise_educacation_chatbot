"""Statistical Analyst Agent — produz StatAnalysis sobre RetrievedData.

LLM: Sonnet 4.5 (raciocinio metodologico). Recebe os dados crus
recuperados pelo Retriever e produz estatisticas descritivas +
posicionamento do pais foco + ressalvas metodologicas.

Tools opcionais: ComputeStatsTool para delegar aritmetica em casos com
muitos paises (>10).
"""

from __future__ import annotations

from crewai import Agent

from src.agents._prompt_loader import load_prompt
from src.llm import make_llm
from src.tools.stats_tools import ComputeStatsTool


def build_statistician() -> Agent:
    return Agent(
        role="Analista estatistico de educacao comparada",
        goal=(
            "Calcular estatisticas descritivas e posicionamento do pais "
            "foco em indicadores agregados (% PIB, % alfab), com ressalvas "
            "metodologicas explicitas quando dados ou comparabilidade sao "
            "limitados."
        ),
        backstory=load_prompt("statistician_system"),
        llm=make_llm("smart"),
        tools=[ComputeStatsTool()],
        allow_delegation=False,
        verbose=False,
        max_iter=4,
    )
