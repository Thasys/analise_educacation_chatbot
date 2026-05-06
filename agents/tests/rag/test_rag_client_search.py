"""Sprint 5.5 — testes do RagClient + ingest + search."""

from __future__ import annotations

import uuid

import yaml

from src.rag.client import RagClient, StubEmbedding
from src.rag.ingest import _entry_to_record, _stable_id, ingest_manifest
from src.rag.search import _build_where, search_papers


# ----------------------------------------------------------------------
# StubEmbedding
# ----------------------------------------------------------------------


def test_stub_embedding_deterministic():
    """ChromaDB envelope EmbeddingFunction.__call__ e retorna numpy
    arrays — comparamos via list cast."""
    fn = StubEmbedding()
    out1 = [list(v) for v in fn(["hello world"])]
    out2 = [list(v) for v in fn(["hello world"])]
    assert out1 == out2
    assert len(out1[0]) == 32
    assert all(0.0 <= v <= 1.0 for v in out1[0])


def test_stub_embedding_different_texts_diff_vectors():
    fn = StubEmbedding()
    out = [list(v) for v in fn(["hello", "world"])]
    assert out[0] != out[1]


# ----------------------------------------------------------------------
# RagClient
# ----------------------------------------------------------------------


def test_rag_client_in_memory_starts_empty():
    c = RagClient(
        embedding_fn=StubEmbedding(),
        in_memory=True,
        collection_name=f"unit_{uuid.uuid4().hex[:8]}",
    )
    assert c.count() == 0


def test_rag_client_upsert_and_query():
    c = RagClient(
        embedding_fn=StubEmbedding(),
        in_memory=True,
        collection_name=f"unit_{uuid.uuid4().hex[:8]}",
    )
    c.upsert(
        ids=["a", "b"],
        documents=["Brazil education spending", "Finland reading reform"],
        metadatas=[
            {"doi": "10.1/a", "title": "BR study", "year": 2020, "lang": "en", "source": "x"},
            {"doi": "10.1/b", "title": "FIN study", "year": 2021, "lang": "en", "source": "y"},
        ],
    )
    assert c.count() == 2
    hits = c.query(text="Brazil", k=1)
    assert len(hits) == 1
    assert hits[0]["id"] in {"a", "b"}


def test_rag_client_upsert_idempotent():
    c = RagClient(
        embedding_fn=StubEmbedding(),
        in_memory=True,
        collection_name=f"unit_{uuid.uuid4().hex[:8]}",
    )
    payload = {
        "ids": ["a"],
        "documents": ["foo"],
        "metadatas": [{"year": 2020, "lang": "en", "source": "x"}],
    }
    c.upsert(**payload)
    c.upsert(**payload)
    assert c.count() == 1


# ----------------------------------------------------------------------
# ingest
# ----------------------------------------------------------------------


def test_stable_id_from_doi():
    e1 = {"doi": "10.1/X", "title": "Foo"}
    e2 = {"doi": "10.1/X", "title": "Bar"}
    assert _stable_id(e1) == _stable_id(e2)


def test_stable_id_falls_back_to_title():
    eid = _stable_id({"doi": None, "title": "BarBaz"})
    assert len(eid) == 24


def test_entry_to_record_with_full_metadata():
    entry = {
        "doi": "10.1234/test",
        "title": "Title",
        "authors": ["A. One", "B. Two"],
        "year": 2020,
        "journal": "J1",
        "lang": "pt",
        "source": "scielo",
        "abstract": "Resumo do paper.",
    }
    doc_id, document, meta = _entry_to_record(entry)
    assert document == "Resumo do paper."
    assert meta["doi"] == "10.1234/test"
    assert meta["authors"] == "A. One; B. Two"
    assert meta["year"] == 2020


def test_ingest_manifest_loads_seed(rag_client_in_memory):
    """Fixture ja roda ingest_manifest; validamos contagem."""
    assert rag_client_in_memory.count() == 25


def test_ingest_manifest_idempotent(rag_client_in_memory, tmp_path):
    """Re-rodar ingest com mesmo manifest nao duplica."""
    from pathlib import Path

    manifest = (
        Path(__file__).resolve().parent.parent.parent
        / "src"
        / "rag"
        / "seeds"
        / "manifest.yaml"
    )
    summary = ingest_manifest(manifest, client=rag_client_in_memory)
    assert summary["total_in_collection"] == 25


# ----------------------------------------------------------------------
# search_papers
# ----------------------------------------------------------------------


def test_build_where_no_filters():
    assert _build_where(None, None, None, None) is None


def test_build_where_single_filter():
    assert _build_where("pt", None, None, None) == {"lang": {"$eq": "pt"}}


def test_build_where_multi_filters_and():
    where = _build_where("pt", "scielo", 2010, 2020)
    assert "$and" in where
    assert len(where["$and"]) == 4


def test_search_papers_returns_relevance_score(rag_client_in_memory):
    hits = search_papers("PISA Brazil OECD", k=3, client=rag_client_in_memory)
    assert 1 <= len(hits) <= 3
    for h in hits:
        assert h["relevance_score"] is None or 0.0 <= h["relevance_score"] <= 1.0
        assert "metadata" in h
        assert "title" in h["metadata"]


def test_search_papers_filter_by_lang(rag_client_in_memory):
    hits_pt = search_papers("educacao", k=20, lang="pt", client=rag_client_in_memory)
    hits_en = search_papers("education", k=20, lang="en", client=rag_client_in_memory)
    assert all(h["metadata"]["lang"] == "pt" for h in hits_pt)
    assert all(h["metadata"]["lang"] == "en" for h in hits_en)
    assert len(hits_pt) >= 4  # manifest tem ~6 em portugues
    assert len(hits_en) >= 10


def test_search_papers_filter_by_year_range(rag_client_in_memory):
    hits = search_papers(
        "PISA", k=20, year_from=2018, year_to=2024, client=rag_client_in_memory
    )
    for h in hits:
        assert 2018 <= h["metadata"]["year"] <= 2024


def test_search_papers_empty_query_returns_empty(rag_client_in_memory):
    hits = search_papers("   ", client=rag_client_in_memory)
    assert hits == []
