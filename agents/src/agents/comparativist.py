"""Comparative Education Agent — narrativa BR x Internacional.

LLM: Sonnet 4.5 (sintese contextual). Recebe RetrievedData +
StatAnalysis e produz ComparativeContext com narrativa, achados-chave,
contexto historico e ressalvas metodologicas.

Sprint 5.5: ganhou `RAGSearchTool` para fundamentar afirmacoes em
literatura cientifica. Continua produzindo apenas ComparativeContext
(sem DOIs no output) — citacao formal eh tarefa do Citation Agent.
"""

from __future__ import annotations

from crewai import Agent

from src.agents._prompt_loader import load_prompt
from src.llm import make_llm
from src.rag.client import RagClient
from src.tools.rag_tools import RAGSearchTool, build_rag_tools


def build_comparativist(client: RagClient | None = None) -> Agent:
    """Cria o Comparativist Agent.

    Acopla `RAGSearchTool` para o agente poder verificar afirmacoes na
    literatura. `CiteResolveTool` fica apenas com o Citation Agent —
    aqui evita inflar o tool set sem necessidade.
    """
    if client is not None:
        # Sincroniza override com a tool wrapper.
        RAGSearchTool._client_override = client
    rag_tools = [t for t in build_rag_tools(client=client) if isinstance(t, RAGSearchTool)]
    return Agent(
        role="Especialista em educacao comparada Brasil-Internacional",
        goal=(
            "Construir narrativa fundamentada nos dados sobre como o "
            "Brasil se posiciona em relacao a paises e grupos de "
            "referencia, com contexto historico (PNE, lacunas temporais) "
            "e ressalvas metodologicas explicitas, ancorada em literatura "
            "cientifica via RAG."
        ),
        backstory=load_prompt("comparativist_system"),
        llm=make_llm("smart"),
        tools=rag_tools,
        allow_delegation=False,
        verbose=False,
        max_iter=4,
    )
