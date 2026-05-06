"""Pipeline de ingestao do RAG a partir de manifest YAML.

Idempotente: cada entrada gera um id estavel (sha256 do DOI ou do
titulo), `upsert` evita duplicatas.

Manifest esperado (`agents/src/rag/seeds/manifest.yaml`):

  papers:
    - doi: "10.1162/REST_a_00028"
      title: "..."
      authors: ["Hanushek, E.", "Woessmann, L."]
      year: 2011
      journal: "Economic Policy"
      lang: "en"
      source: "nber"
      abstract: "We show that ..."
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import structlog
import yaml

from src.rag.client import RagClient, get_rag_client


log = structlog.get_logger(__name__)


def _stable_id(entry: dict[str, Any]) -> str:
    """Id determinista: sha256 do DOI se houver; senao do titulo."""
    key = (entry.get("doi") or entry.get("title") or "").strip()
    if not key:
        raise ValueError(f"Entrada sem doi nem titulo: {entry}")
    return hashlib.sha256(key.lower().encode("utf-8")).hexdigest()[:24]


def _entry_to_record(entry: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    """Converte 1 entrada do manifest em (id, document, metadata).

    O `document` e abstract OU titulo (fallback). A metadata aceita
    apenas tipos primitivos pelo ChromaDB — listas viram strings
    separadas por `;`.
    """
    doc_id = _stable_id(entry)
    document = (
        entry.get("abstract")
        or f"{entry.get('title', '')}. {entry.get('journal', '')}"
    ).strip()
    if not document:
        raise ValueError(f"Entrada sem abstract nem titulo: {entry}")
    authors = entry.get("authors") or []
    metadata: dict[str, Any] = {
        "doi": entry.get("doi") or "",
        "title": entry.get("title", ""),
        "authors": "; ".join(authors) if isinstance(authors, list) else str(authors),
        "year": int(entry["year"]) if entry.get("year") is not None else 0,
        "journal": entry.get("journal", ""),
        "lang": entry.get("lang", "en"),
        "source": entry.get("source", "unknown"),
    }
    return doc_id, document, metadata


def ingest_manifest(
    manifest_path: Path | str,
    client: RagClient | None = None,
) -> dict[str, Any]:
    """Le um manifest YAML e popula a colecao via `upsert`.

    Returns:
        Dict com `inserted`, `total_in_collection`, `manifest_path`.
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest nao encontrado: {manifest_path}")

    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    entries = raw.get("papers") or []
    if not isinstance(entries, list):
        raise ValueError("Manifest invalido: 'papers' deve ser lista.")

    rag = client or get_rag_client()
    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict[str, Any]] = []
    errors: list[str] = []

    for i, entry in enumerate(entries):
        try:
            doc_id, document, meta = _entry_to_record(entry)
        except ValueError as exc:
            errors.append(f"#{i}: {exc}")
            continue
        ids.append(doc_id)
        docs.append(document)
        metas.append(meta)

    rag.upsert(ids=ids, documents=docs, metadatas=metas)
    summary = {
        "inserted": len(ids),
        "total_in_collection": rag.count(),
        "manifest_path": str(manifest_path),
        "errors": errors,
    }
    log.info("agents.rag.ingest_done", **summary)
    return summary
