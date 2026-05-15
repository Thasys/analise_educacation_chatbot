"""Helper compartilhado para construir agentes CrewAI.

Centraliza os invariantes do projeto (`allow_delegation=False`,
`verbose=False`) num unico lugar — qualquer mudanca arquitetural sobre
delegacao/verbosidade vira uma edicao aqui em vez de 8 edicoes.

Tambem e o ponto unico onde a escolha de LLM passa: util para LP1
(provider Anthropic opcional para Synthesizer) e LP3 (JSON Schema strict
via Ollama `format=`) do quality-assessment.
"""

from __future__ import annotations

from typing import Literal

from crewai import Agent
from crewai.tools import BaseTool

from src.agents._prompt_loader import load_prompt
from src.llm import make_llm

LLMKind = Literal["fast", "smart"]


def make_agent(
    *,
    role: str,
    goal: str,
    prompt_name: str,
    llm_kind: LLMKind = "fast",
    tools: list[BaseTool] | None = None,
    max_iter: int = 3,
) -> Agent:
    """Constroi um Agent CrewAI com os invariantes do projeto aplicados.

    Args:
        role: rotulo curto do papel (ex.: "Orchestrator de roteamento").
        goal: objetivo da tarefa (1-2 frases).
        prompt_name: nome do arquivo em `src/prompts/<name>.txt` (sem extensao).
        llm_kind: "fast" (Haiku/mistral pequeno) ou "smart" (Sonnet/maior).
        tools: lista de tools opcional; default e vazio.
        max_iter: limite de iteracoes do loop CrewAI por agente.

    Invariantes aplicados:
        - `allow_delegation=False`: agentes NUNCA delegam — fluxo e fixo.
        - `verbose=False`: log estruturado e responsabilidade do master_flow.
    """
    return Agent(
        role=role,
        goal=goal,
        backstory=load_prompt(prompt_name),
        llm=make_llm(llm_kind),
        allow_delegation=False,
        verbose=False,
        max_iter=max_iter,
        tools=tools or [],
    )
