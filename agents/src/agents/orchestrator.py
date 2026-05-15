"""Orchestrator Agent — classifica fluxo + perfil.

LLM: Haiku 4.5 (rapido, baixo custo). Tarefa de classificacao curta com
saida estruturada `IntentDecision`.
"""

from __future__ import annotations

from crewai import Agent

from src.agents._builder import make_agent


def build_orchestrator() -> Agent:
    """Cria o Orchestrator Agent ja com LLM e backstory carregados."""
    return make_agent(
        role="Orchestrator de roteamento educacional",
        goal=(
            "Classificar a pergunta do usuario em um dos tres fluxos "
            "(simple/data/deep) e detectar o perfil (researcher/policy/student)."
        ),
        prompt_name="orchestrator_system",
        llm_kind="fast",
        max_iter=2,
    )
