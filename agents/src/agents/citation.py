"""Citation & Evidence Agent — fundamenta resposta com DOIs do RAG.

LLM: Haiku 4.5 (filtragem e formatacao). Tools: RAGSearchTool +
CiteResolveTool. Output: Citations (lista de Citation com DOI, autores,
ano, snippet curto).
"""

from __future__ import annotations

from crewai import Agent

from src.agents._prompt_loader import load_prompt
from src.llm import make_llm
from src.rag.client import RagClient
from src.tools.rag_tools import build_rag_tools


def build_citation(client: RagClient | None = None) -> Agent:
    """Cria o Citation Agent acoplando o RagClient (opcional)."""
    return Agent(
        role="Curador de evidencias academicas em educacao comparada",
        goal=(
            "Selecionar 2-5 referencias academicas reais (com DOI) do RAG "
            "local que fundamentem as afirmacoes da resposta, sem inventar "
            "DOIs nem reproduzir trechos literais."
        ),
        backstory=load_prompt("citation_system"),
        llm=make_llm("fast"),
        tools=build_rag_tools(client=client),
        allow_delegation=False,
        verbose=False,
        max_iter=4,
    )
