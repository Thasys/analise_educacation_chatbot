"""Sprint 6.1 — testes do POST /api/chat/stream (mini server)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src.schemas import FinalAnswer, VizSpec
from src.server.main import app


def _make_final() -> FinalAnswer:
    return FinalAnswer(
        markdown="# Resposta\n\nCorpo.",
        profile_used="researcher",
        flow_used="data",
        sources_cited=["worldbank"],
        visualizations=[
            VizSpec(
                chart_type="bar_vertical",
                title="Test",
                plotly_figure={"data": [], "layout": {}},
                sources=["worldbank"],
            )
        ],
        citations=[],
        warnings=[],
        follow_up_suggestions=[],
    )


@pytest.fixture
def client():
    return TestClient(app)


# ----------------------------------------------------------------------
# /health
# ----------------------------------------------------------------------


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    payload = r.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "agents-server"


# ----------------------------------------------------------------------
# /api/chat/stream — mock do run_master
# ----------------------------------------------------------------------


def _parse_sse(body_text: str) -> list[dict]:
    """Parser simples de SSE: extrai (event, data) de cada bloco."""
    blocks = body_text.strip().split("\n\n")
    events: list[dict] = []
    for block in blocks:
        if not block.strip():
            continue
        lines = block.split("\n")
        evt = {}
        for line in lines:
            if line.startswith("event: "):
                evt["event"] = line[len("event: ") :].strip()
            elif line.startswith("data: "):
                evt["data"] = json.loads(line[len("data: ") :])
        if evt:
            events.append(evt)
    return events


def test_chat_stream_emits_sse_events(client, monkeypatch):
    """Mocka run_master para emitir 3 eventos via callback + retornar FinalAnswer."""
    final = _make_final()

    def fake_run_master(question, *, on_event=None, **kwargs):
        if on_event is not None:
            on_event({"type": "flow_started", "question": question, "ts": 1.0})
            on_event({"type": "agent_started", "agent": "Core", "ts": 2.0})
            on_event({"type": "agent_done", "agent": "Core", "ts": 3.0})
            on_event(
                {"type": "final_answer", "elapsed_s": 1.5,
                 "payload": final.model_dump(), "ts": 4.0}
            )
        return final

    monkeypatch.setattr("src.server.chat_stream.run_master", fake_run_master)

    r = client.post("/api/chat/stream", json={"question": "Pergunta de teste"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(r.text)
    types = [e["event"] for e in events]
    assert "flow_started" in types
    assert "agent_started" in types
    assert "agent_done" in types
    assert types[-1] == "final_answer"

    # Final event carrega o FinalAnswer completo serializado
    final_event = events[-1]
    assert final_event["data"]["payload"]["flow_used"] == "data"
    assert final_event["data"]["payload"]["markdown"].startswith("# Resposta")


def test_chat_stream_validates_empty_question(client):
    r = client.post("/api/chat/stream", json={"question": ""})
    assert r.status_code == 422


def test_chat_stream_validates_missing_question(client):
    r = client.post("/api/chat/stream", json={})
    assert r.status_code == 422


def test_chat_stream_emits_error_event_on_failure(client, monkeypatch):
    """Quando run_master levanta, emitimos `event: error` em vez de 500."""

    def boom(*args, **kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("src.server.chat_stream.run_master", boom)

    r = client.post("/api/chat/stream", json={"question": "x"})
    assert r.status_code == 200  # SSE ja foi aberto
    events = _parse_sse(r.text)
    error_events = [e for e in events if e["event"] == "error"]
    assert len(error_events) == 1
    assert "simulated failure" in error_events[0]["data"]["error"]
