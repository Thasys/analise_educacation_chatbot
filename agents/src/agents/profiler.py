"""Profile & Intent Agent — extrai entidades da pergunta.

LLM: Haiku 4.5. Saida estruturada `EntityExtraction` (indicador, paises,
grouping, ano, janela temporal).
"""

from __future__ import annotations

from crewai import Agent

from src.agents._prompt_loader import load_prompt
from src.llm import make_llm


def build_profiler() -> Agent:
    """Cria o Profile & Intent Agent ja com LLM e backstory carregados."""
    return Agent(
        role="Extrator de entidades educacionais",
        goal=(
            "Extrair indicador canonico, paises (ISO-3), grouping, ano e "
            "janela temporal mencionados na pergunta do usuario."
        ),
        backstory=load_prompt("profiler_system"),
        llm=make_llm("fast"),
        allow_delegation=False,
        verbose=False,
        max_iter=2,
    )
