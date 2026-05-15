"""Testes do `is_real_doi` (ajuste 3 do quality-assessment 2026-05-15).

Bloqueia DOIs placeholder (`10.xxxx/...`) que LLMs locais emitem quando
nao tem certeza. Aplicado no pos-processamento de
`analysis_crew._run_citation`.
"""

from __future__ import annotations

import pytest

from src.tools.rag_tools import is_real_doi


@pytest.mark.parametrize(
    "doi",
    [
        "10.1162/REST_a_00081",
        "10.1590/198053143331",
        "10.1787/9789264315131-en",
        "10.1038/s41586-021-03323-7",
        "10.1234/real-paper-2024",
    ],
)
def test_accepts_real_doi(doi: str) -> None:
    assert is_real_doi(doi) is True


@pytest.mark.parametrize(
    "doi",
    [
        "10.xxxx/...",
        "10.xxxx/oecd-edu-2020",
        "10.1234/yyyy-placeholder",
        "10.5678/abcd1234",
        "10.9999/placeholder-doi",
        "10.xxxx/y",
        "10.0000/example",
        "10.1234/zzzz-foo",
    ],
)
def test_rejects_placeholder_doi(doi: str) -> None:
    assert is_real_doi(doi) is False


@pytest.mark.parametrize("doi", ["", "   ", "not-a-doi", "10/123/abc"])
def test_rejects_malformed(doi: str) -> None:
    assert is_real_doi(doi) is False


def test_rejects_none() -> None:
    assert is_real_doi(None) is False
