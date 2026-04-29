"""Fixtures compartilhadas para testes da API.

Todos os testes que precisam de DuckDB sao "skipados" automaticamente
se `data/duckdb/education.duckdb` nao existir (ex.: quando rodando em
CI sem ter executado `dbt build` antes).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.main import app


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def client():
    """TestClient com lifespan ativo (DuckDB conectado se possivel)."""
    duckdb_path = settings.duckdb_path.resolve()
    if not duckdb_path.exists():
        pytest.skip(
            f"DuckDB nao encontrado em {duckdb_path}; rode `dbt build` primeiro."
        )
    with TestClient(app) as c:
        yield c
