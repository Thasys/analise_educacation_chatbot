"""Busca semantica sobre a colecao de literatura.

API simples para consumo pelas tools (`RAGSearchTool`):

- `search_papers(query, k=5, lang=None, source=None, year_from=None,
  year_to=None, client=None)` -> lista de Hits.

Cada Hit traz `relevance_score = 1 - cosine_distance`, normalizado em
[0, 1]. Filtros sao aplicados via `where` do ChromaDB (tipos primitivos
apenas).
"""

from __future__ import annotations

from typing import Any

from src.rag.client import RagClient, get_rag_client


def _build_where(
    lang: str | None,
    source: str | None,
    year_from: int | None,
    year_to: int | None,
) -> dict[str, Any] | None:
    """Constroi clausula `where` do ChromaDB.

    Operadores: $eq, $gte, $lte, $and. Multiplas condicoes sao
    combinadas via $and. Retorna None se nenhuma condicao.
    """
    clauses: list[dict[str, Any]] = []
    if lang:
        clauses.append({"lang": {"$eq": lang}})
    if source:
        clauses.append({"source": {"$eq": source}})
    if year_from is not None:
        clauses.append({"year": {"$gte": year_from}})
    if year_to is not None:
        clauses.append({"year": {"$lte": year_to}})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def search_papers(
    query: str,
    *,
    k: int = 5,
    lang: str | None = None,
    source: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    client: RagClient | None = None,
) -> list[dict[str, Any]]:
    """Busca papers similar a `query`. Retorna lista de hits ordenada
    pela similaridade (maior primeiro).

    Cada hit:
        {
            "id": "...",
            "document": "<abstract>",
            "metadata": {doi, title, authors, year, journal, lang, source},
            "relevance_score": <float em [0, 1]>,
        }
    """
    rag = client or get_rag_client()
    where = _build_where(lang, source, year_from, year_to)
    items = rag.query(text=query, k=k, where=where)
    hits: list[dict[str, Any]] = []
    for it in items:
        distance = it.get("distance")
        # cosine distance ∈ [0, 2] -> similarity ∈ [-1, 1] -> normalizar
        if distance is None:
            score: float | None = None
        else:
            similarity = 1.0 - float(distance)
            score = max(0.0, min(1.0, (similarity + 1.0) / 2.0))
        hits.append(
            {
                "id": it["id"],
                "document": it["document"],
                "metadata": it["metadata"],
                "relevance_score": score,
            }
        )
    return hits
