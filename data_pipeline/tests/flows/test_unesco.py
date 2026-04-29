"""Testes do flow Prefect UNESCO UIS (REST API)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from prefect.testing.utilities import prefect_test_harness

from src.flows import unesco as flow_module


SAMPLE_REST: dict[str, Any] = {
    "hints": [],
    "records": [
        {"indicatorId": "CR.1", "geoUnit": "BRA", "year": 2020, "value": 96.3,
         "magnitude": None, "qualifier": None},
        {"indicatorId": "CR.1", "geoUnit": "BRA", "year": 2021, "value": 96.7,
         "magnitude": None, "qualifier": None},
    ],
    "indicatorMetadata": [],
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
                lambda req: httpx.Response(200, json=SAMPLE_REST)
            )
        )

    original_init = flow_module.UisRestCollector.__init__

    def patched_init(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("http_client", fake_client_factory())
        kwargs["bronze_writer"] = flow_module.BronzeWriter(bronze_root)
        kwargs["ingestion_logger"] = flow_module.IngestionLogger(dsn=None)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(flow_module.UisRestCollector, "__init__", patched_init)
    return bronze_root


def test_flow_runs_for_explicit_indicators(patch_collector: Path) -> None:
    results = flow_module.ingest_uis_education_indicators(
        indicators=["CR.1", "CR.2"],
        reference_period="2020",
    )
    assert len(results) == 2
    datasets = {r["dataset"] for r in results}
    assert "indicator_cr_1" in datasets
    assert "indicator_cr_2" in datasets
    for r in results:
        assert Path(r["parquet_path"]).exists()


def test_flow_runs_with_default_indicators(patch_collector: Path) -> None:
    results = flow_module.ingest_uis_education_indicators(reference_period="2020")
    assert len(results) == len(flow_module.DEFAULT_INDICATORS)
