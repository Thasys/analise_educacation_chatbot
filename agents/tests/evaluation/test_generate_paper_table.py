"""Unit tests para `evaluation.reports.generate_paper_table`."""

from __future__ import annotations

import json
from pathlib import Path

from evaluation.reports.generate_paper_table import (
    classify_scope,
    generate,
    render_markdown,
)


# ----------------------------------------------------------------------
# classify_scope
# ----------------------------------------------------------------------


def test_adversarial_sempre_e_adversarial() -> None:
    item = {"kind": "adversarial", "query": "qualquer", "expected_behavior": "block"}
    assert classify_scope(item) == "adversarial"


def test_pisa_e_out_of_scope() -> None:
    item = {
        "kind": "factual",
        "query": "Qual foi a nota do Brasil em Matematica no PISA 2022?",
    }
    assert classify_scope(item) == "out_of_scope"


def test_ideb_e_out_of_scope() -> None:
    item = {"kind": "factual", "query": "Qual o IDEB em 2021?"}
    assert classify_scope(item) == "out_of_scope"


def test_gasto_pib_e_in_scope() -> None:
    item = {
        "kind": "factual",
        "query": "Qual o gasto publico em educacao como % do PIB em 2021?",
    }
    assert classify_scope(item) == "in_scope"


def test_analfabetismo_e_in_scope() -> None:
    item = {
        "kind": "factual",
        "query": "Qual a taxa de analfabetismo de 15+ em 2022?",
    }
    assert classify_scope(item) == "in_scope"


def test_default_conservador_e_out_of_scope() -> None:
    """Quando nao bate nenhuma heuristica, default = out_of_scope."""
    item = {"kind": "factual", "query": "Quantos professores ha?"}
    assert classify_scope(item) == "out_of_scope"  # "professor" esta em out_of_scope


# ----------------------------------------------------------------------
# render_markdown — sanity check com input minimo
# ----------------------------------------------------------------------


def _mk_item(
    id_: str,
    *,
    kind: str = "factual",
    query: str = "qual?",
    classification: str = "hallucinated",
    latency_s: float = 1.0,
    category: str | None = None,
    expected_behavior: str | None = None,
    sources_recall: float | None = None,
    doi_recall: float | None = None,
) -> dict:
    return {
        "id": id_,
        "kind": kind,
        "query": query,
        "expected_value": None,
        "actual_value": None,
        "tolerance_pct": 5,
        "blocked": False,
        "expected_behavior": expected_behavior,
        "category": category,
        "classification": classification,
        "latency_s": latency_s,
        "markdown": "",
        "n_citations": 0,
        "warnings": [],
        "sources_recall": sources_recall,
        "doi_recall": doi_recall,
        "error": None,
    }


def test_render_markdown_estrutura_basica() -> None:
    """Render gera todas as 4 tabelas e a secao 'Para o resumo'."""
    baseline = {
        "mode": "baseline",
        "n_items": 3,
        "started_at": "2026-05-19T15:00:00Z",
        "duration_s": 100.0,
        "items": [
            _mk_item("F-1", query="gasto em educacao % do PIB", classification="hallucinated"),
            _mk_item("F-2", query="taxa de analfabetismo BR 2022", classification="correct"),
            _mk_item("A-1", kind="adversarial", category="adversarial_numbers",
                     expected_behavior="block", classification="hallucinated"),
        ],
    }
    # EduQuery bloqueia ambos os factuais (FP em F-2) e bloqueia o adversarial
    eduquery = {
        "mode": "eduquery",
        "n_items": 3,
        "started_at": "2026-05-19T16:00:00Z",
        "duration_s": 200.0,
        "items": [
            _mk_item("F-1", query="gasto em educacao % do PIB", classification="blocked"),
            _mk_item("F-2", query="taxa de analfabetismo BR 2022", classification="blocked"),
            _mk_item("A-1", kind="adversarial", category="adversarial_numbers",
                     expected_behavior="block", classification="blocked"),
        ],
    }
    md = render_markdown(baseline, eduquery, None)
    # Sanity: estrutura presente
    assert "Tabela 1" in md
    assert "Tabela 2" in md
    assert "Tabela 3" in md
    assert "Tabela 4" in md
    assert "TIA in-scope" in md
    assert "adversarial_numbers" in md


def test_generate_grava_arquivo(tmp_path: Path) -> None:
    """Smoke test do end-to-end: gera o arquivo no caminho dado."""
    baseline = tmp_path / "baseline.json"
    eduquery = tmp_path / "eduquery.json"
    out = tmp_path / "paper_table.md"
    base = {
        "mode": "baseline",
        "n_items": 1,
        "items": [_mk_item("F-1", query="gasto % PIB", classification="hallucinated")],
    }
    edu = {
        "mode": "eduquery",
        "n_items": 1,
        "items": [_mk_item("F-1", query="gasto % PIB", classification="blocked")],
    }
    baseline.write_text(json.dumps(base), encoding="utf-8")
    eduquery.write_text(json.dumps(edu), encoding="utf-8")
    generate(baseline, eduquery, None, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "TIA" in content
