"""Response Synthesizer — combina tudo em FinalAnswer markdown.

LLM: Sonnet 4.5 (qualidade de redacao + adaptacao a perfil). Sem tools
nesta sprint — apenas sintese sobre todos os outputs anteriores.
"""

from __future__ import annotations

from crewai import Agent

from src.agents._builder import make_agent


def build_synthesizer() -> Agent:
    return make_agent(
        role="Sintetizador de respostas educacionais comparadas",
        goal=(
            "Produzir resposta final em markdown adaptada ao perfil "
            "(researcher/policy/student), combinando dados, estatisticas, "
            "narrativa, visualizacao e fontes — sem inventar numeros nem "
            "prescrever politicas."
        ),
        prompt_name="synthesizer_system",
        llm_kind="smart",
        max_iter=3,
    )
