"""Citation & Evidence Agent — fundamenta resposta com DOIs do RAG.

LLM: Haiku 4.5 (filtragem e formatacao). Tools: RAGSearchTool +
CiteResolveTool. Output: Citations (lista de Citation com DOI, autores,
ano, snippet curto).
"""

from __future__ import annotations

from crewai import Agent

from src.agents._builder import make_agent
from src.rag.client import RagClient
from src.tools.rag_tools import build_rag_tools


def build_citation(client: RagClient | None = None) -> Agent:
    """Cria o Citation Agent acoplando o RagClient (opcional)."""
    return make_agent(
        role="Curador de evidencias academicas em educacao comparada",
        goal=(
            "Selecionar 2-5 referencias academicas reais (com DOI) do RAG "
            "local que fundamentem as afirmacoes da resposta, sem inventar "
            "DOIs nem reproduzir trechos literais."
        ),
        prompt_name="citation_system",
        llm_kind="fast",
        tools=build_rag_tools(client=client),
        max_iter=4,
    )
