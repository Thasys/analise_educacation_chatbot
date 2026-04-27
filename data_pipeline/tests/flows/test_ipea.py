"""Testes do flow Prefect de ingestão IPEADATA.

Usa `prefect_test_harness` para isolar o servidor Prefect em SQLite efêmero,
sem depender do Postgres do docker-compose nem do PREFECT_API_URL do .env.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from prefect.testing.utilities import prefect_test_harness

from src.flows import ipea as flow_module


SAMPLE_PAYLOAD: dict[str, Any] = {
    "@odata.context": "http://www.ipeadata.gov.br/api/odata4/$metadata#Valores",
    "value": [
        {
            "SERCODIGO": "ANALF15M",
            "VALDATA": "2023-01-01T00:00:00-03:00",
            "VALVALOR": 6.6,
            "NIVNOME": "Brasil",
            "TERCODIGO": "",
        }
    ],
}


@pytest.fixture(scope="module", autouse=True)
def prefect_harness():
    with prefect_test_harness():
        yield


@pytest.fixture()
def patch_collector(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    bronze_root = tmp_path / "bronze"
    bronze_root.mkdir()

    def fake_client_factory() -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(
                lambda req: httpx.Response(200, json=SAMPLE_PAYLOAD)
            )
        )

    original_init = flow_module.IpeaDataCollector.__init__

    def patched_init(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("http_client", fake_client_factory())
        kwargs["bronze_writer"] = flow_module.BronzeWriter(bronze_root)
        kwargs["ingestion_logger"] = flow_module.IngestionLogger(dsn=None)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(flow_module.IpeaDataCollector, "__init__", patched_init)
    return bronze_root


def test_flow_runs_for_explicit_series(patch_collector: Path) -> None:
    results = flow_module.ingest_education_series(
        series=["ANALF15M", "IDEB_BR_SAI"], reference_period="all"
    )
    assert len(results) == 2
    assert {r["dataset"] for r in results} == {"serie_analf15m", "serie_ideb_br_sai"}
    for r in results:
        assert Path(r["parquet_path"]).exists()


def test_flow_runs_with_default_series(patch_collector: Path) -> None:
    results = flow_module.ingest_education_series(reference_period="all")
    assert len(results) == len(flow_module.DEFAULT_EDUCATION_SERIES)
    for r in results:
        assert r["row_count"] == 1
