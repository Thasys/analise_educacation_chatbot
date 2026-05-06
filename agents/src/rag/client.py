"""Wrapper ChromaDB para a colecao de literatura educacional.

Decisoes:

- ChromaDB **embedded** (PersistentClient) — sem servidor, sem porta. O
  diretorio fica em `settings.rag_persist_dir` (default
  `data/chromadb/edu_literature/`).
- A `EmbeddingFunction` e injetavel: producao usa
  `SentenceTransformerEmbeddingFunction` com modelo multilingual
  (`paraphrase-multilingual-MiniLM-L12-v2`); testes podem injetar uma
  `StubEmbedding` deterministica para evitar download de ~500 MB.
- Documento canonico: o abstract (ou titulo se abstract ausente). A
  metadata carrega doi/title/authors/year/journal/lang/source para
  recuperacao posterior.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import chromadb
import structlog
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from src.config import settings


log = structlog.get_logger(__name__)


class StubEmbedding(EmbeddingFunction):
    """Embedding determinista 32-dim baseado em hash MD5.

    Usado em TESTES para evitar baixar o modelo sentence-transformers
    (~500 MB) e manter resultados reproducible. NAO use em producao —
    similaridade semantica e zero, so identidade textual aproxima.
    """

    def __init__(self, dim: int = 32) -> None:
        self.dim = dim

    @staticmethod
    def name() -> str:
        return "stub_md5"

    def __call__(self, input: Documents) -> Embeddings:
        out: list[list[float]] = []
        for txt in input:
            digest = hashlib.md5(txt.encode("utf-8"), usedforsecurity=False).digest()
            # Repete digest ate cobrir dim bytes; normaliza para [0,1]
            stretched = (digest * ((self.dim // len(digest)) + 1))[: self.dim]
            out.append([b / 255.0 for b in stretched])
        return out


def _build_st_embedding() -> EmbeddingFunction:
    """Constroi EmbeddingFunction do sentence-transformers (lazy import)."""
    from chromadb.utils import embedding_functions

    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=settings.rag_embedding_model
    )


class RagClient:
    """Cliente da colecao `edu_literature`.

    Args:
        persist_dir: diretorio do ChromaDB. None -> settings.
        embedding_fn: funcao de embedding. None -> sentence-transformers
            multilingual (producao).
        in_memory: se True, ignora persist_dir e usa client em memoria
            (testes).
    """

    def __init__(
        self,
        persist_dir: Path | None = None,
        embedding_fn: EmbeddingFunction | None = None,
        in_memory: bool = False,
        collection_name: str | None = None,
    ) -> None:
        self.persist_dir = (
            None if in_memory else Path(persist_dir or settings.rag_persist_dir)
        )
        if in_memory:
            # EphemeralClient compartilha tenant default em chromadb 1.1.1,
            # entao colecoes precisam ter nome unico por teste para
            # garantir isolamento.
            self._chroma = chromadb.EphemeralClient()
        else:
            assert self.persist_dir is not None
            self.persist_dir.mkdir(parents=True, exist_ok=True)
            self._chroma = chromadb.PersistentClient(path=str(self.persist_dir))
        self._embedding_fn = embedding_fn or _build_st_embedding()
        self.collection_name = collection_name or settings.rag_collection_name
        self._collection = self._chroma.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        log.info(
            "agents.rag.client_ready",
            persist_dir=str(self.persist_dir) if self.persist_dir else "memory",
            collection=self.collection_name,
            count=self._collection.count(),
        )

    # ------------------------------------------------------------------
    # Operacoes
    # ------------------------------------------------------------------

    def upsert(
        self,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Insere ou atualiza documentos. ChromaDB upsert e idempotente
        por id."""
        if not ids:
            return
        self._collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    def query(
        self,
        *,
        text: str,
        k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Busca semantica. Retorna lista de dicts com:
        id, document, metadata, distance (menor = mais similar com cosine).
        """
        if not text.strip():
            return []
        result = self._collection.query(
            query_texts=[text],
            n_results=k,
            where=where,
        )
        items: list[dict[str, Any]] = []
        ids = (result.get("ids") or [[]])[0]
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        for i, doc_id in enumerate(ids):
            items.append(
                {
                    "id": doc_id,
                    "document": docs[i] if i < len(docs) else None,
                    "metadata": metas[i] if i < len(metas) else {},
                    "distance": dists[i] if i < len(dists) else None,
                }
            )
        return items

    def count(self) -> int:
        return self._collection.count()

    def reset(self) -> None:
        """Limpa a colecao (testes)."""
        ids = self._collection.get()["ids"]
        if ids:
            self._collection.delete(ids=ids)


# ----------------------------------------------------------------------
# Singleton
# ----------------------------------------------------------------------


_singleton: RagClient | None = None


def get_rag_client() -> RagClient:
    """Retorna o RagClient producao (cacheado)."""
    global _singleton
    if _singleton is None:
        _singleton = RagClient()
    return _singleton


def reset_singleton() -> None:
    """Limpa o cache (uso interno em testes)."""
    global _singleton
    _singleton = None
