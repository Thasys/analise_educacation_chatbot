"""Testes herméticos do UisRestCollector (UIS REST API publica, 2026+)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pytest

from src.collectors.unesco.uis_rest_client import UisRestCollector
from src.utils.bronze import BronzeWriter
from src.utils.ingestion_log import IngestionLogger


SAMPLE_RESPONSE: dict[str, Any] = {
    "hints": [],
    "records": [
        {"indicatorId": "CR.1", "geoUnit": "BRA", "year": 2018, "value": 95.1,
         "magnitude": None, "qualifier": None},
        {"indicatorId": "CR.1", "geoUnit": "BRA", "year": 2019, "value": 95.7,
         "magnitude": None, "qualifier": None},
        {"indicatorId": "CR.1", "geoUnit": "USA", "year": 2018, "value": 89.0,
         "magnitude": None, "qualifier": None},
    ],
    "indicatorMetadata": [],
}


@pytest.fixture
def mock_client() -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json=SAMPLE_RESPONSE)
        )
    )


@pytest.fixture
def empty_response_client() -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(200, json={"hints": [], "records": [],
                                                  "indicatorMetadata": []})
        )
    )


@pytest.fixture
def disabled_ingestion_logger() -> IngestionLogger:
    return IngestionLogger(dsn=None)


def test_init_rejects_empty_indicator() -> None:
    with pytest.raises(ValueError, match="indicator"):
        UisRestCollector(indicator="")


def test_dataset_slug_normalizes_dot_separated() -> None:
    c = UisRestCollector(indicator="CR.1")
    assert c.dataset == "indicator_cr_1"


def test_dataset_slug_normalizes_multiple_indicators() -> None:
    c = UisRestCollector(indicator="CR.1,NER.1")
    assert c.dataset == "indicator_cr_1_plus_ner_1"


def test_build_url_no_period() -> None:
    c = UisRestCollector(indicator="CR.1", geo_unit="BRA")
    url = c.build_url(period=None)
    assert "indicator=CR.1" in url
    assert "geoUnit=BRA" in url
    assert "start=" not in url
    assert "end=" not in url
    assert url.startswith("https://api.uis.unesco.org/api/public/data/indicators?")


def test_build_url_single_year() -> None:
    c = UisRestCollector(indicator="CR.1")
    url = c.build_url(period=2020)
    assert "start=2020" in url
    assert "end=2020" in url


def test_build_url_range() -> None:
    c = UisRestCollector(indicator="CR.1")
    url = c.build_url(period="2018-2022")
    assert "start=2018" in url
    assert "end=2022" in url


def test_build_url_all_means_no_filter() -> None:
    c = UisRestCollector(indicator="CR.1")
    url = c.build_url(period="all")
    assert "start=" not in url
    assert "end=" not in url


def test_parse_records_flattens_to_dataframe() -> None:
    df = UisRestCollector.parse_records(SAMPLE_RESPONSE)
    assert len(df) == 3
    assert set(df.columns) == {"indicatorId", "geoUnit", "year", "value",
                                "magnitude", "qualifier"}
    bra_rows = df[df["geoUnit"] == "BRA"]
    assert len(bra_rows) == 2
    assert bra_rows["value"].tolist() == [95.1, 95.7]


def test_parse_records_handles_empty() -> None:
    df = UisRestCollector.parse_records({"hints": [], "records": [],
                                          "indicatorMetadata": []})
    assert df.empty
    assert "indicatorId" in df.columns


def test_collect_writes_to_bronze(
    tmp_path: Path,
    mock_client: httpx.Client,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    bronze_root = tmp_path / "bronze"
    bronze_root.mkdir()

    collector = UisRestCollector(
        indicator="CR.1",
        geo_unit="BRA",
        http_client=mock_client,
        bronze_writer=BronzeWriter(bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = collector.collect(reference_period="2018-2022")

    assert result.dataset == "indicator_cr_1"
    assert result.source == "unesco"
    parquet = Path(result.parquet_path)
    assert parquet.exists()
    df = pd.read_parquet(parquet)
    assert len(df) == 3
    assert (df["indicatorId"] == "CR.1").all()


def test_collect_handles_empty_response(
    tmp_path: Path,
    empty_response_client: httpx.Client,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    """Empty response should still write a valid (empty) parquet."""
    bronze_root = tmp_path / "bronze"
    bronze_root.mkdir()

    collector = UisRestCollector(
        indicator="CR.1",
        http_client=empty_response_client,
        bronze_writer=BronzeWriter(bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = collector.collect(reference_period="2020")

    assert result.dataset == "indicator_cr_1"
    parquet = Path(result.parquet_path)
    assert parquet.exists()
    df = pd.read_parquet(parquet)
    assert len(df) == 0
