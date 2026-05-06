"""RAG tools — busca semantica sobre literatura cientifica + cite resolve.

`RAGSearchTool`: invocada pelo Comparativist e pelo Citation Agent
para fundamentar afirmacoes ou listar referencias relevantes.

`CiteResolveTool`: stub simples — recebe um DOI e devolve metadata
estruturada (sem chamar crossref nesta sprint; ficaria como network
call em Sprint 5+ se necessario). Por agora apenas valida formato.
"""

from __future__ import annotations

import json
import re
from typing import Any, ClassVar, Literal

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from src.rag.client import RagClient
from src.rag.search import search_papers


# ----------------------------------------------------------------------
# RAGSearchTool
# ----------------------------------------------------------------------


class RAGSearchArgs(BaseModel):
    """Argumentos da busca no RAG."""

    query: str = Field(..., min_length=3, max_length=500)
    k: int = Field(default=5, ge=1, le=20)
    lang: Literal["pt", "en", "es"] | None = Field(
        default=None, description="Filtra por idioma do paper."
    )
    source: str | None = Field(
        default=None,
        description="Filtra por fonte (scielo, oecd, nber, unesco, ...).",
    )
    year_from: int | None = Field(default=None, ge=1900, le=2030)
    year_to: int | None = Field(default=None, ge=1900, le=2030)


class RAGSearchTool(BaseTool):
    """Busca semantica sobre literatura cientifica em educacao comparada."""

    name: str = "rag_search"
    description: str = (
        "Busca semantica sobre ~25 papers em educacao comparada (CLAUDE.md "
        "bibliografia + complementares). Argumentos: query (texto livre), k "
        "(1-20, default 5), lang (pt/en/es), source (scielo/oecd/nber/unesco/"
        "iea/inep/...), year_from, year_to. Retorna lista de hits com doi, "
        "title, authors, year, abstract e relevance_score (0-1)."
    )
    args_schema: type[BaseModel] = RAGSearchArgs

    _client_override: ClassVar[RagClient | None] = None

    def run(self, *args: Any, **kwargs: Any) -> Any:
        try:
            return super().run(*args, **kwargs)
        except ValueError as exc:
            return json.dumps(
                {"ok": False, "error": {"error_type": "validation", "message": str(exc)}}
            )

    def _run(
        self,
        query: str,
        k: int = 5,
        lang: str | None = None,
        source: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> str:
        hits = search_papers(
            query,
            k=k,
            lang=lang,
            source=source,
            year_from=year_from,
            year_to=year_to,
            client=type(self)._client_override,
        )
        # Compactar para reduzir tokens
        compact = [
            {
                "id": h["id"],
                "doi": h["metadata"].get("doi") or None,
                "title": h["metadata"].get("title"),
                "authors": h["metadata"].get("authors"),
                "year": h["metadata"].get("year"),
                "journal": h["metadata"].get("journal"),
                "lang": h["metadata"].get("lang"),
                "source": h["metadata"].get("source"),
                "snippet": (h.get("document") or "")[:300],
                "relevance_score": h.get("relevance_score"),
            }
            for h in hits
        ]
        return json.dumps({"ok": True, "hits": compact, "query": query})


# ----------------------------------------------------------------------
# CiteResolveTool — validacao basica de DOI + lookup metadata local
# ----------------------------------------------------------------------


_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$")


class CiteResolveArgs(BaseModel):
    doi: str = Field(..., min_length=4, description="DOI no formato 10.xxxx/...")


class CiteResolveTool(BaseTool):
    """Valida DOI e busca metadata local na colecao RAG.

    Sprint 5.5: stub local. Em Sprint 5+ pode chamar crossref.org com
    cache. Retorna `{ok, valid, doi, found_in_rag, metadata?}`.
    """

    name: str = "cite_resolve"
    description: str = (
        "Valida o formato de um DOI (10.xxxx/...) e tenta encontra-lo na "
        "colecao RAG local. Retorna metadata se encontrado, ou apenas "
        "valid=true se o DOI eh sintaticamente valido mas nao consta "
        "do RAG. Use ANTES de citar um DOI no markdown final."
    )
    args_schema: type[BaseModel] = CiteResolveArgs

    _client_override: ClassVar[RagClient | None] = None

    def run(self, *args: Any, **kwargs: Any) -> Any:
        try:
            return super().run(*args, **kwargs)
        except ValueError as exc:
            return json.dumps(
                {"ok": False, "error": {"error_type": "validation", "message": str(exc)}}
            )

    def _run(self, doi: str) -> str:
        valid = bool(_DOI_PATTERN.match(doi.strip()))
        if not valid:
            return json.dumps(
                {"ok": True, "valid": False, "doi": doi, "found_in_rag": False}
            )
        # Busca por DOI exato na metadata
        client = type(self)._client_override
        hits = search_papers(doi, k=10, client=client)
        match = next(
            (h for h in hits if (h["metadata"].get("doi") or "").strip() == doi.strip()),
            None,
        )
        if match is None:
            return json.dumps(
                {"ok": True, "valid": True, "doi": doi, "found_in_rag": False}
            )
        return json.dumps(
            {
                "ok": True,
                "valid": True,
                "doi": doi,
                "found_in_rag": True,
                "metadata": {
                    "title": match["metadata"].get("title"),
                    "authors": match["metadata"].get("authors"),
                    "year": match["metadata"].get("year"),
                    "journal": match["metadata"].get("journal"),
                    "lang": match["metadata"].get("lang"),
                    "source": match["metadata"].get("source"),
                },
            }
        )


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------


def build_rag_tools(client: RagClient | None = None) -> list[BaseTool]:
    """Retorna `[RAGSearchTool, CiteResolveTool]` com client opcional."""
    if client is not None:
        RAGSearchTool._client_override = client
        CiteResolveTool._client_override = client
    return [RAGSearchTool(), CiteResolveTool()]
