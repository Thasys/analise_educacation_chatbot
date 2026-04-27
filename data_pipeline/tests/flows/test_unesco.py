"""Testes do flow Prefect UNESCO UIS."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from prefect.testing.utilities import prefect_test_harness

from src.flows import unesco as flow_module


SAMPLE_SDMX: dict[str, Any] = {
    "data": {
        "structures": [
            {
                "dimensions": {
                    "series": [
                        {"id": "REF_AREA", "values": [{"id": "BRA"}]}
                    ],
                    "observation": [
                        {"id": "TIME_PERIOD", "values": [{"id": "2020"}]}
                    ],
                },
                "attributes": {"observation": []},
            }
        ],
        "dataSets": [
            {"series": {"0": {"observations": {"0": [95.5]}}}}
        ],
    }
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
                lambda req: httpx.Response(200, json=SAMPLE_SDMX)
            )
        )

    original_init = flow_module.UisCollector.__init__

    def patched_init(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("http_client", fake_client_factory())
        kwargs["bronze_writer"] = flow_module.BronzeWriter(bronze_root)
        kwargs["ingestion_logger"] = flow_module.IngestionLogger(dsn=None)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(flow_module.UisCollector, "__init__", patched_init)
    return bronze_root


def test_flow_runs_for_explicit_flows(patch_collector: Path) -> None:
    results = flow_module.ingest_uis_education_flows(
        flow_refs=["UNESCO,EDU_NON_FINANCE,1.0", "UNESCO,SDG,1.0"],
        reference_period="2020",
    )
    assert len(results) == 2
    datasets = {r["dataset"] for r in results}
    assert "flow_unesco_edu_non_finance_1_0" in datasets
    assert "flow_unesco_sdg_1_0" in datasets
    for r in results:
        assert Path(r["parquet_path"]).exists()


def test_flow_runs_with_default_refs(patch_collector: Path) -> None:
    results = flow_module.ingest_uis_education_flows(reference_period="2020")
    assert len(results) == len(flow_module.DEFAULT_FLOW_REFS)
