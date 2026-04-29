"""Testes do flow Prefect CEPALSTAT (REST v1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
from prefect.testing.utilities import prefect_test_harness

from src.flows import cepalstat as flow_module


SAMPLE_DATA_PAYLOAD: dict[str, Any] = {
    "header": {"success": True, "code": 200},
    "body": {
        "metadata": {
            "indicator_id": 2236,
            "indicator_name": "Literacy rate",
            "unit": "Percentage",
        },
        "data": [
            {"value": "97.29", "iso3": "BRA",
             "dim_144": 146, "dim_208": 222, "dim_29117": 68309},
        ],
    },
}

SAMPLE_DIMS_PAYLOAD: dict[str, Any] = {
    "header": {"success": True, "code": 200},
    "body": {
        "dimensions": [
            {"id": 144, "name": "Sex__ESTANDAR",
             "members": [{"id": 146, "name": "Both sexes"}]},
            {"id": 208, "name": "Country__ESTANDAR",
             "members": [{"id": 222, "name": "Brazil"}]},
            {"id": 29117, "name": "Years__ESTANDAR",
             "members": [{"id": 68309, "name": "2020"}]},
        ]
    },
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
        def handler(request: httpx.Request) -> httpx.Response:
            if "/dimensions" in request.url.path:
                return httpx.Response(200, json=SAMPLE_DIMS_PAYLOAD)
            return httpx.Response(200, json=SAMPLE_DATA_PAYLOAD)

        return httpx.Client(transport=httpx.MockTransport(handler))

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
        indicators=["2236", "53"], reference_period="2020"
    )
    assert len(results) == 2
    assert {r["dataset"] for r in results} == {"indicator_2236", "indicator_53"}
    for r in results:
        assert Path(r["parquet_path"]).exists()


def test_flow_runs_with_default_indicators(patch_collector: Path) -> None:
    results = flow_module.ingest_cepalstat_indicators(reference_period="2020")
    assert len(results) == len(flow_module.DEFAULT_CEPALSTAT_INDICATORS)
