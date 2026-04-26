"""Smoke test do endpoint /api/health."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.main import app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "edu-api"
    assert "version" in body
    assert "timestamp" in body
