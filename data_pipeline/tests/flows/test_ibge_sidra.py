"""Testes do flow Prefect de ingestão SIDRA.

Usa `prefect_test_harness` para isolar cada teste em um servidor Prefect
ephemeral com SQLite — sem depender do Postgres do docker-compose nem
do PREFECT_API_URL configurado no .env do projeto.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from prefect.testing.utilities import prefect_test_harness

from src.flows import ibge_sidra as flow_module


SAMPLE_PAYLOAD: list[dict[str, Any]] = [
    {"NC": "Nível Territorial (Código)", "V": "Valor", "D1N": "Brasil"},
    {"NC": "1", "V": "6.6", "D1N": "Brasil"},
]


@pytest.fixture(scope="module", autouse=True)
def prefect_harness():
    """Servidor Prefect efêmero para todos os testes do módulo."""
    with prefect_test_harness():
        yield


@pytest.fixture()
def patch_collector(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Substitui a construção do coletor para usar httpx mockado e bronze tmp."""
    bronze_root = tmp_path / "bronze"
    bronze_root.mkdir()

    def fake_client_factory() -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(200, json=SAMPLE_PAYLOAD)
            )
        )

    original_init = flow_module.SidraEducacaoCollector.__init__

    def patched_init(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("http_client", fake_client_factory())
        kwargs["bronze_writer"] = flow_module.BronzeWriter(bronze_root)
        kwargs["ingestion_logger"] = flow_module.IngestionLogger(dsn=None)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(
        flow_module.SidraEducacaoCollector, "__init__", patched_init
    )
    return bronze_root


def test_flow_runs_for_explicit_years(patch_collector: Path) -> None:
    results = flow_module.ingest_pnad_continua_t7136(years=[2022, 2023])
    assert len(results) == 2
    for r in results:
        assert r["dataset"] == "sidra_7136"
        assert Path(r["parquet_path"]).exists()


def test_flow_runs_for_default_year(patch_collector: Path) -> None:
    results = flow_module.ingest_pnad_continua_t7136()
    assert len(results) == 1
    assert results[0]["row_count"] == 1
