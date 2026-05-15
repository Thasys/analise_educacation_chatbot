"""Profile & Intent Agent — extrai entidades da pergunta.

LLM: Haiku 4.5. Saida estruturada `EntityExtraction` (indicador, paises,
grouping, ano, janela temporal).
"""

from __future__ import annotations

from crewai import Agent

from src.agents._builder import make_agent


def build_profiler() -> Agent:
    """Cria o Profile & Intent Agent ja com LLM e backstory carregados."""
    return make_agent(
        role="Extrator de entidades educacionais",
        goal=(
            "Extrair indicador canonico, paises (ISO-3), grouping, ano e "
            "janela temporal mencionados na pergunta do usuario."
        ),
        prompt_name="profiler_system",
        llm_kind="fast",
        max_iter=2,
    )
