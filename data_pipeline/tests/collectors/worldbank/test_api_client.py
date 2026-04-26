"""Testes do coletor World Bank."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.collectors.worldbank.api_client import (
    WorldBankCollector,
    make_education_expenditure_collector,
    make_human_capital_index_collector,
)
from src.utils.bronze import BronzeWriter
from src.utils.ingestion_log import IngestionLogger


def _make_record(country_iso3: str, date: str, value: float | None) -> dict[str, Any]:
    return {
        "indicator": {"id": "SE.XPD.TOTL.GD.ZS", "value": "Government expenditure on education"},
        "country": {"id": country_iso3[:2], "value": country_iso3},
        "countryiso3code": country_iso3,
        "date": date,
        "value": value,
        "unit": "",
        "obs_status": "",
        "decimal": 1,
    }


SAMPLE_METADATA: dict[str, Any] = {
    "page": 1,
    "pages": 1,
    "per_page": 1000,
    "total": 3,
    "sourceid": "2",
    "lastupdated": "2024-12-15",
}

SAMPLE_PAYLOAD: list[Any] = [
    SAMPLE_METADATA,
    [
        _make_record("BRA", "2023", 6.0),
        _make_record("USA", "2023", 5.4),
        _make_record("FIN", "2023", 6.6),
    ],
]


# ----------------------------------------------------------------------
# build_url
# ----------------------------------------------------------------------
def test_build_url_default_period() -> None:
    c = WorldBankCollector(
        indicator="SE.XPD.TOTL.GD.ZS", api_base="https://api.worldbank.org/v2"
    )
    url = c.build_url(2023)
    assert "country/all/indicator/SE.XPD.TOTL.GD.ZS" in url
    assert "date=2023" in url
    assert "format=json" in url
    assert "per_page=1000" in url
    assert "page=1" in url


def test_build_url_range_uses_colon() -> None:
    c = WorldBankCollector(
        indicator="HD.HCI.OVRL", api_base="https://api.worldbank.org/v2"
    )
    url = c.build_url("2010-2020")
    # API espera 2010:2020 (formato range), mas o Path usa 2010-2020.
    assert "date=2010%3A2020" in url or "date=2010:2020" in url


def test_build_url_with_country_filter() -> None:
    c = WorldBankCollector(
        indicator="SE.PRM.ENRR",
        countries="BRA;USA;FIN",
        api_base="https://api.worldbank.org/v2",
    )
    url = c.build_url(2022)
    assert "country/BRA;USA;FIN/" in url


# ----------------------------------------------------------------------
# _records_to_dataframe
# ----------------------------------------------------------------------
def test_records_to_dataframe_flattens_nested_objects() -> None:
    records = SAMPLE_PAYLOAD[1]
    df = WorldBankCollector._records_to_dataframe(records)
    assert len(df) == 3
    assert set(df.columns) >= {
        "indicator_id",
        "indicator_name",
        "country_id",
        "country_iso3",
        "date",
        "value",
    }
    assert df.loc[df["country_iso3"] == "BRA", "value"].iloc[0] == 6.0


def test_records_to_dataframe_empty_returns_empty_with_columns() -> None:
    df = WorldBankCollector._records_to_dataframe([])
    assert df.empty
    assert "country_iso3" in df.columns
    assert "value" in df.columns


# ----------------------------------------------------------------------
# _split_payload — modos de erro
# ----------------------------------------------------------------------
def test_split_payload_raises_on_short_payload() -> None:
    with pytest.raises(ValueError):
        WorldBankCollector._split_payload([{"message": "Invalid"}], url="x")


def test_split_payload_raises_on_non_list() -> None:
    with pytest.raises(ValueError):
        WorldBankCollector._split_payload({"error": "x"}, url="x")


# ----------------------------------------------------------------------
# fetch
# ----------------------------------------------------------------------
def _make_mock_client(payload: Any) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_returns_dataframe_and_url() -> None:
    client = _make_mock_client(SAMPLE_PAYLOAD)
    c = WorldBankCollector(
        indicator="SE.XPD.TOTL.GD.ZS",
        api_base="https://api.worldbank.org/v2",
        http_client=client,
    )
    df, url = c.fetch(reference_period=2023)
    client.close()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert set(df["country_iso3"]) == {"BRA", "USA", "FIN"}
    assert "country/all/indicator/" in url


def test_fetch_handles_pagination() -> None:
    """Quando metadata.pages > 1, o coletor agrega páginas subsequentes."""
    page1 = [
        {"page": 1, "pages": 2, "per_page": 2, "total": 3},
        [_make_record("BRA", "2023", 6.0), _make_record("USA", "2023", 5.4)],
    ]
    page2 = [
        {"page": 2, "pages": 2, "per_page": 2, "total": 3},
        [_make_record("FIN", "2023", 6.6)],
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        page = request.url.params.get("page", "1")
        return httpx.Response(200, json=page1 if page == "1" else page2)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = WorldBankCollector(
        indicator="SE.XPD.TOTL.GD.ZS",
        api_base="https://api.worldbank.org/v2",
        http_client=client,
        per_page=2,
    )
    df, _ = c.fetch(reference_period=2023)
    client.close()

    assert len(df) == 3
    assert set(df["country_iso3"]) == {"BRA", "USA", "FIN"}


def test_fetch_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = WorldBankCollector(
        indicator="X", api_base="https://api.worldbank.org/v2", http_client=client
    )
    with pytest.raises(httpx.HTTPStatusError):
        c.fetch(reference_period=2023)
    client.close()


# ----------------------------------------------------------------------
# collect — pipeline completo
# ----------------------------------------------------------------------
def test_collect_writes_to_bronze(
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    client = _make_mock_client(SAMPLE_PAYLOAD)
    c = WorldBankCollector(
        indicator="SE.XPD.TOTL.GD.ZS",
        api_base="https://api.worldbank.org/v2",
        http_client=client,
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period="2023")
    client.close()

    expected_dir = (
        tmp_bronze_root / "worldbank" / "indicator_se_xpd_totl_gd_zs" / "2023"
    )
    assert (expected_dir / "data.parquet").exists()
    assert (expected_dir / "_metadata.json").exists()
    assert result.row_count == 3

    table = pq.read_table(result.parquet_path)
    assert "country_iso3" in table.column_names


def test_collect_handles_range_period_in_path(
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    """O path da Bronze usa o período como string — '-' permanece, ':' não aparece."""
    client = _make_mock_client(SAMPLE_PAYLOAD)
    c = WorldBankCollector(
        indicator="HD.HCI.OVRL",
        api_base="https://api.worldbank.org/v2",
        http_client=client,
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period="2010-2023")
    client.close()

    assert result.parquet_path.endswith("2010-2023\\data.parquet") or result.parquet_path.endswith(
        "2010-2023/data.parquet"
    )


# ----------------------------------------------------------------------
# Conveniências
# ----------------------------------------------------------------------
def test_make_education_expenditure_collector() -> None:
    c = make_education_expenditure_collector()
    assert c.indicator == "SE.XPD.TOTL.GD.ZS"
    assert c.dataset == "indicator_se_xpd_totl_gd_zs"
    assert c.source == "worldbank"


def test_make_human_capital_index_collector() -> None:
    c = make_human_capital_index_collector()
    assert c.indicator == "HD.HCI.OVRL"
    assert c.dataset == "indicator_hd_hci_ovrl"
