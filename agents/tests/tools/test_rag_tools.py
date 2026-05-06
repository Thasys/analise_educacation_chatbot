"""Sprint 5.5 — testes RAGSearchTool + CiteResolveTool."""

from __future__ import annotations

import json

from src.tools import CiteResolveTool, RAGSearchTool, build_rag_tools


def test_build_rag_tools_returns_two(rag_client_in_memory):
    tools = build_rag_tools(client=rag_client_in_memory)
    names = [t.name for t in tools]
    assert names == ["rag_search", "cite_resolve"]


# ----------------------------------------------------------------------
# RAGSearchTool
# ----------------------------------------------------------------------


def test_rag_search_basic_query(rag_client_in_memory):
    tools = build_rag_tools(client=rag_client_in_memory)
    rag = next(t for t in tools if t.name == "rag_search")
    raw = rag.run(query="Brazil education spending OECD")
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert 1 <= len(payload["hits"]) <= 5
    h0 = payload["hits"][0]
    assert "title" in h0 and "year" in h0


def test_rag_search_with_lang_filter(rag_client_in_memory):
    tools = build_rag_tools(client=rag_client_in_memory)
    rag = next(t for t in tools if t.name == "rag_search")
    raw = rag.run(query="educacao SAEB", lang="pt", k=3)
    payload = json.loads(raw)
    assert payload["ok"] is True
    for h in payload["hits"]:
        assert h["lang"] == "pt"


def test_rag_search_validation_query_too_short(rag_client_in_memory):
    tools = build_rag_tools(client=rag_client_in_memory)
    rag = next(t for t in tools if t.name == "rag_search")
    raw = rag.run(query="x")  # min_length=3
    payload = json.loads(raw)
    assert payload["ok"] is False
    assert payload["error"]["error_type"] == "validation"


def test_rag_search_validation_invalid_year(rag_client_in_memory):
    tools = build_rag_tools(client=rag_client_in_memory)
    rag = next(t for t in tools if t.name == "rag_search")
    raw = rag.run(query="education", year_from=1800)  # < 1900
    payload = json.loads(raw)
    assert payload["ok"] is False


def test_rag_search_returns_compact_snippet(rag_client_in_memory):
    tools = build_rag_tools(client=rag_client_in_memory)
    rag = next(t for t in tools if t.name == "rag_search")
    raw = rag.run(query="Hanushek economic growth education")
    payload = json.loads(raw)
    for h in payload["hits"]:
        assert "snippet" in h
        assert len(h["snippet"]) <= 300


# ----------------------------------------------------------------------
# CiteResolveTool
# ----------------------------------------------------------------------


def test_cite_resolve_invalid_format(rag_client_in_memory):
    tools = build_rag_tools(client=rag_client_in_memory)
    cite = next(t for t in tools if t.name == "cite_resolve")
    raw = cite.run(doi="not-a-doi")
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["valid"] is False
    assert payload["found_in_rag"] is False


def test_cite_resolve_valid_format_not_in_rag(rag_client_in_memory):
    tools = build_rag_tools(client=rag_client_in_memory)
    cite = next(t for t in tools if t.name == "cite_resolve")
    raw = cite.run(doi="10.9999/never-exists-xxxx")
    payload = json.loads(raw)
    assert payload["valid"] is True
    assert payload["found_in_rag"] is False


def test_cite_resolve_found_in_rag(rag_client_in_memory):
    """Hanushek-Woessmann 2011 esta no manifest seed."""
    tools = build_rag_tools(client=rag_client_in_memory)
    cite = next(t for t in tools if t.name == "cite_resolve")
    raw = cite.run(doi="10.1162/REST_a_00081")
    payload = json.loads(raw)
    assert payload["valid"] is True
    assert payload["found_in_rag"] is True
    assert "Hanushek" in payload["metadata"]["authors"]


def test_cite_resolve_validation_empty_doi(rag_client_in_memory):
    tools = build_rag_tools(client=rag_client_in_memory)
    cite = next(t for t in tools if t.name == "cite_resolve")
    raw = cite.run(doi="")  # min_length=4
    payload = json.loads(raw)
    assert payload["ok"] is False
    assert payload["error"]["error_type"] == "validation"
