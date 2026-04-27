"""Testes do flow Prefect CEPALSTAT."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from prefect.testing.utilities import prefect_test_harness

from src.flows import cepalstat as flow_module


SAMPLE_PAYLOAD: dict[str, Any] = {
    "data": [
        {
            "country_id": "76",
            "country_name": "Brasil",
            "country_iso3": "BRA",
            "year": 2020,
            "value": 6.6,
            "unit": "%",
            "source": "Encuesta",
            "notes": None,
        }
    ]
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

    original_init = flow_module.CepalstatCollector.__init__

    def patched_init(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("http_client", fake_client_factory())
        kwargs["bronze_writer"] = flow_module.BronzeWriter(bronze_root)
        kwargs["ingestion_logger"] = flow_module.IngestionLogger(dsn=None)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(flow_module.CepalstatCollector, "__init__", patched_init)
    return bronze_root


def test_flow_runs_for_explicit_indicators(patch_collector: Path) -> None:
    results = flow_module.ingest_cepalstat_indicators(
        indicators=["1471", "1407"], reference_period="2020"
    )
    assert len(results) == 2
    assert {r["dataset"] for r in results} == {"indicator_1471", "indicator_1407"}
    for r in results:
        assert Path(r["parquet_path"]).exists()


def test_flow_runs_with_default_indicators(patch_collector: Path) -> None:
    results = flow_module.ingest_cepalstat_indicators(reference_period="2020")
    assert len(results) == len(flow_module.DEFAULT_CEPALSTAT_INDICATORS)
