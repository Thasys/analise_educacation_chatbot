"""RAG tools — busca semantica sobre literatura cientifica + cite resolve.

`RAGSearchTool`: invocada pelo Comparativist e pelo Citation Agent
para fundamentar afirmacoes ou listar referencias relevantes.

`CiteResolveTool`: stub local — recebe um DOI, valida formato e procura
metadata na colecao RAG local. Network call para crossref.org pode ser
adicionado futuramente sem mudar a interface.
"""

from __future__ import annotations

import json
import re
from typing import ClassVar, Literal

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from src.rag.client import RagClient
from src.rag.search import search_papers
from src.tools._base import SafeTool, instantiate_with_shared_client


# ----------------------------------------------------------------------
# RAGSearchTool
# ----------------------------------------------------------------------


class RAGSearchArgs(BaseModel):
    """Argumentos da busca no RAG."""

    # min_length/max_length removidos: viram repeticoes em GBNF que excedem
    # o limite do llama.cpp parser e crasham o runner do Ollama.
    # Validacao continua sendo aplicada via RAGSearchTool.run().
    query: str = Field(..., description="Texto livre da busca (3-500 chars).")
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


class RAGSearchTool(SafeTool):
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

    def _run(
        self,
        query: str,
        k: int = 5,
        lang: str | None = None,
        source: str | None = None,
        year_from: int | None = None,
        year_to: int | None = None,
    ) -> str:
        # Validacao de tamanho aqui (em vez do args_schema) para nao
        # gerar repeticao GBNF que crasha o Ollama. Promessa do comentario
        # no args_schema agora cumprida.
        if not (3 <= len(query) <= 500):
            raise ValueError(
                f"query precisa ter 3-500 chars (recebeu {len(query)})."
            )
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

# Placeholders detectados em testes 2026-05-15 (qwen2.5:32b emitiu
# `10.xxxx/...` literalmente). Rejeitamos antes de chegar a Crossref.
# Cada padrao casa contra a parte SUFIXO do DOI (depois da barra).
_DOI_PLACEHOLDER_SUFFIXES = re.compile(
    r"^(?:x{2,}|y{2,}|z{2,}|nnnn|abcd|1234|placeholder|example|sample|tbd|todo|"
    r"x{2,}[.\-/_]|.*[/\-]x{2,}$|.*y{4,}|.*z{4,})",
    re.IGNORECASE,
)


def is_real_doi(doi: str | None) -> bool:
    """True apenas se o DOI parece real (formato + sem placeholder).

    Usado tanto na `CiteResolveTool` quanto no pos-processamento do
    Citation Agent (analysis_crew._run_citation) para descartar
    `10.xxxx/...` e similares antes de chegar ao FinalAnswer.
    """
    if not doi or not doi.strip():
        return False
    cleaned = doi.strip()
    if not _DOI_PATTERN.match(cleaned):
        return False
    # Quebra em prefix/suffix; suffix sempre vai existir por causa do regex.
    suffix = cleaned.split("/", 1)[1]
    if _DOI_PLACEHOLDER_SUFFIXES.match(suffix):
        return False
    # Tambem rejeita se PREFIX termina com 'xxxx' (ex.: '10.xxxx/...').
    prefix = cleaned.split("/", 1)[0]
    if "xxxx" in prefix.lower() or "yyyy" in prefix.lower():
        return False
    return True


class CiteResolveArgs(BaseModel):
    doi: str = Field(..., description="DOI no formato 10.xxxx/...")


class CiteResolveTool(SafeTool):
    """Valida DOI e busca metadata local na colecao RAG.

    Hoje stub local — futuramente pode chamar crossref.org com cache
    para validar contra o registro real. Retorna
    `{ok, valid, doi, found_in_rag, metadata?}`.
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

    def _run(self, doi: str) -> str:
        if not doi or not doi.strip():
            raise ValueError("doi nao pode ser vazio.")
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
    return instantiate_with_shared_client(
        [RAGSearchTool, CiteResolveTool],
        client,
    )
