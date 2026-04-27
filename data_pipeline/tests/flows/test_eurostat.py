"""Testes do flow Prefect Eurostat."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from prefect.testing.utilities import prefect_test_harness

from src.flows import eurostat as flow_module


SAMPLE_JSONSTAT: dict[str, Any] = {
    "version": "2.0",
    "class": "dataset",
    "id": ["geo", "time"],
    "size": [1, 1],
    "dimension": {
        "geo": {"category": {"index": {"BE": 0}}},
        "time": {"category": {"index": {"2020": 0}}},
    },
    "value": [42.0],
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
                lambda req: httpx.Response(200, json=SAMPLE_JSONSTAT)
            )
        )

    original_init = flow_module.EurostatCollector.__init__

    def patched_init(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("http_client", fake_client_factory())
        kwargs["bronze_writer"] = flow_module.BronzeWriter(bronze_root)
        kwargs["ingestion_logger"] = flow_module.IngestionLogger(dsn=None)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(flow_module.EurostatCollector, "__init__", patched_init)
    return bronze_root


def test_flow_runs_for_explicit_datasets(patch_collector: Path) -> None:
    results = flow_module.ingest_eurostat_education_datasets(
        datasets=["educ_uoe_enrt01", "edat_lfse_14"],
        reference_period="2020",
    )
    assert len(results) == 2
    datasets = {r["dataset"] for r in results}
    assert "dataset_educ_uoe_enrt01" in datasets
    assert "dataset_edat_lfse_14" in datasets
    for r in results:
        assert Path(r["parquet_path"]).exists()


def test_flow_runs_with_default_datasets(patch_collector: Path) -> None:
    results = flow_module.ingest_eurostat_education_datasets(reference_period="2020")
    assert len(results) == len(flow_module.DEFAULT_EUROSTAT_DATASETS)
