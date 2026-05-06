"""Orchestrator Agent — classifica fluxo + perfil.

LLM: Haiku 4.5 (rapido, baixo custo). Tarefa de classificacao curta com
saida estruturada `IntentDecision`.
"""

from __future__ import annotations

from crewai import Agent

from src.agents._prompt_loader import load_prompt
from src.llm import make_llm


def build_orchestrator() -> Agent:
    """Cria o Orchestrator Agent ja com LLM e backstory carregados."""
    return Agent(
        role="Orchestrator de roteamento educacional",
        goal=(
            "Classificar a pergunta do usuario em um dos tres fluxos "
            "(simple/data/deep) e detectar o perfil (researcher/policy/student)."
        ),
        backstory=load_prompt("orchestrator_system"),
        llm=make_llm("fast"),
        allow_delegation=False,
        verbose=False,
        max_iter=2,
    )
