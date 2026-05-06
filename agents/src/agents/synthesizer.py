"""Response Synthesizer — combina tudo em FinalAnswer markdown.

LLM: Sonnet 4.5 (qualidade de redacao + adaptacao a perfil). Sem tools
nesta sprint — apenas sintese sobre todos os outputs anteriores.
"""

from __future__ import annotations

from crewai import Agent

from src.agents._prompt_loader import load_prompt
from src.llm import make_llm


def build_synthesizer() -> Agent:
    return Agent(
        role="Sintetizador de respostas educacionais comparadas",
        goal=(
            "Produzir resposta final em markdown adaptada ao perfil "
            "(researcher/policy/student), combinando dados, estatisticas, "
            "narrativa, visualizacao e fontes — sem inventar numeros nem "
            "prescrever politicas."
        ),
        backstory=load_prompt("synthesizer_system"),
        llm=make_llm("smart"),
        allow_delegation=False,
        verbose=False,
        max_iter=3,
    )
