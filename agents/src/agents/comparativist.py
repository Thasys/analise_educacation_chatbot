"""Agente que produz narrativa BR x Internacional fundamentada.

Recebe `RetrievedData` + `StatAnalysis` e produz `ComparativeContext`
(narrativa, achados-chave, contexto historico, caveats metodologicos).

Por que aqui (e nao no Synthesizer): a narrativa precisa de RAG para
ancorar em literatura. Separar permite mockar RAG so neste agente.

Por que SEM DOIs no output: citacao formal e responsabilidade do
Citation Agent (single source of truth para DOIs).
"""

from __future__ import annotations

from crewai import Agent

from src.agents._builder import make_agent
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
    return make_agent(
        role="Especialista em educacao comparada Brasil-Internacional",
        goal=(
            "Construir narrativa fundamentada nos dados sobre como o "
            "Brasil se posiciona em relacao a paises e grupos de "
            "referencia, com contexto historico (PNE, lacunas temporais) "
            "e ressalvas metodologicas explicitas, ancorada em literatura "
            "cientifica via RAG."
        ),
        prompt_name="comparativist_system",
        llm_kind="smart",
        tools=rag_tools,
        max_iter=4,
    )
