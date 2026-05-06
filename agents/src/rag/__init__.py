"""RAG sobre literatura cientifica em educacao comparada.

- `client`: wrapper ChromaDB embedded (persistencia em disco) +
  `EmbeddingFunction` opcional injetavel para testes.
- `ingest`: pipeline de ingestao a partir de manifest YAML.
- `search`: busca semantica com filtros (lang, year_range, source).
"""

from src.rag.client import RagClient, get_rag_client
from src.rag.ingest import ingest_manifest
from src.rag.search import search_papers

__all__ = ["RagClient", "get_rag_client", "ingest_manifest", "search_papers"]
