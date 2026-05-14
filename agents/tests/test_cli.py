"""Sprint 5.6 — testes do CLI (`python -m src.cli`).

Sem chamar Anthropic real: monkeypatch `run_master` por uma stub.
"""

from __future__ import annotations

import json

import pytest

from src.schemas import (
    Citation,
    FinalAnswer,
    VizSpec,
)


def _stub_final() -> FinalAnswer:
    return FinalAnswer(
        markdown="# Resposta\n\nCorpo da resposta...",
        profile_used="researcher",
        flow_used="data",
        sources_cited=["worldbank"],
        visualizations=[
            VizSpec(
                chart_type="bar_vertical",
                title="Gasto 2020",
                plotly_figure={"data": [{"x": ["BRA"], "y": [5.77]}], "layout": {}},
                sources=["worldbank"],
            )
        ],
        citations=[
            Citation(
                doi="10.1234/test",
                title="Test Paper",
                authors=["Author One"],
                year=2024,
                source="oecd",
            )
        ],
        warnings=[],
        follow_up_suggestions=["Pergunta extra 1"],
    )


def _patch_has_key_true(monkeypatch):
    """Substitui `Settings.has_llm_key` por property -> True.

    Ataca a CLASSE para nao depender do estado global do settings ja
    instanciado (lru_cache + env var loaded em import time)."""
    from src import cli

    monkeypatch.setattr(
        type(cli.settings),
        "has_llm_key",
        property(lambda self: True),
    )


def _patch_has_key_false(monkeypatch):
    from src import cli

    monkeypatch.setattr(
        type(cli.settings),
        "has_llm_key",
        property(lambda self: False),
    )


def test_cli_returns_zero_on_success(monkeypatch, capsys):
    _patch_has_key_true(monkeypatch)
    monkeypatch.setattr("src.cli.run_master", lambda q: _stub_final())

    from src.cli import main

    rc = main(["Pergunta de teste"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Test Paper" in out
    assert "doi:10.1234/test" in out
    assert "Pergunta extra 1" in out
    assert "perfil=researcher" in out


def test_cli_json_only_mode(monkeypatch, capsys):
    _patch_has_key_true(monkeypatch)
    monkeypatch.setattr("src.cli.run_master", lambda q: _stub_final())

    from src.cli import main

    rc = main(["--json-only", "Pergunta de teste"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["profile_used"] == "researcher"
    assert payload["flow_used"] == "data"
    assert len(payload["citations"]) == 1


def test_cli_fails_without_api_key(monkeypatch, capsys):
    _patch_has_key_false(monkeypatch)

    from src.cli import main

    rc = main(["Qualquer pergunta"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "ANTHROPIC_API_KEY" in err


def test_cli_handles_run_master_exception(monkeypatch, capsys):
    _patch_has_key_true(monkeypatch)

    def _explode(_q):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("src.cli.run_master", _explode)

    from src.cli import main

    rc = main(["Pergunta"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "simulated failure" in err
