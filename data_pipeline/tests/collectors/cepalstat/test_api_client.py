"""Testes do coletor CEPALSTAT."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.collectors.cepalstat.api_client import (
    CepalstatCollector,
    make_analfabetismo_15m_collector,
    make_anos_estudio_promedio_collector,
)
from src.utils.bronze import BronzeWriter
from src.utils.ingestion_log import IngestionLogger


def _record(iso3: str, year: int, value: float | None) -> dict[str, Any]:
    return {
        "country_id": "76" if iso3 == "BRA" else "152",
        "country_name": "Brasil" if iso3 == "BRA" else "Chile",
        "country_iso3": iso3,
        "year": year,
        "value": value,
        "unit": "%",
        "source": "Encuesta de hogares",
        "notes": None,
    }


SAMPLE_PAYLOAD: dict[str, Any] = {
    "indicator": {"id": "1471", "name": "Tasa de analfabetismo", "unit": "%"},
    "data": [
        _record("BRA", 2020, 6.6),
        _record("BRA", 2021, 6.4),
        _record("CHL", 2020, 3.4),
    ],
}


# ----------------------------------------------------------------------
# Constructor
# ----------------------------------------------------------------------
def test_constructor_accepts_int_id() -> None:
    c = CepalstatCollector(indicator_id=1471, api_base="https://x/api/v1")
    assert c.indicator_id == "1471"
    assert c.dataset == "indicator_1471"


def test_constructor_normalises_country_list() -> None:
    c = CepalstatCollector(
        indicator_id="1471", countries=["BRA", "CHL", "ARG"], api_base="https://x/api/v1"
    )
    assert c.countries == "BRA+CHL+ARG"


def test_constructor_accepts_country_string() -> None:
    c = CepalstatCollector(
        indicator_id="1471", countries="BRA+CHL", api_base="https://x/api/v1"
    )
    assert c.countries == "BRA+CHL"


def test_constructor_handles_none_countries() -> None:
    c = CepalstatCollector(indicator_id="1471", api_base="https://x/api/v1")
    assert c.countries is None


# ----------------------------------------------------------------------
# build_url
# ----------------------------------------------------------------------
def test_build_url_minimal() -> None:
    c = CepalstatCollector(indicator_id="1471", api_base="https://x/api/v1")
    url = c.build_url(None)
    assert url.startswith("https://x/api/v1/indicator/data?")
    assert "ids_indicator=1471" in url
    assert "format=json" in url
    assert "ids_areas" not in url
    assert "start_year" not in url


def test_build_url_with_countries_and_range() -> None:
    c = CepalstatCollector(
        indicator_id="1471",
        countries=["BRA", "CHL"],
        api_base="https://x/api/v1",
    )
    url = c.build_url("2010-2023")
    assert "ids_areas=BRA%2BCHL" in url or "ids_areas=BRA+CHL" in url
    assert "start_year=2010" in url
    assert "end_year=2023" in url


def test_build_url_single_year_sets_both_bounds() -> None:
    c = CepalstatCollector(indicator_id="1471", api_base="https://x/api/v1")
    url = c.build_url(2022)
    assert "start_year=2022" in url
    assert "end_year=2022" in url


def test_build_url_all_skips_period() -> None:
    c = CepalstatCollector(indicator_id="1471", api_base="https://x/api/v1")
    url = c.build_url("all")
    assert "start_year" not in url
    assert "end_year" not in url


# ----------------------------------------------------------------------
# _parse_payload
# ----------------------------------------------------------------------
def test_parse_payload_returns_typed_dataframe() -> None:
    df = CepalstatCollector._parse_payload(SAMPLE_PAYLOAD)
    assert len(df) == 3
    assert {
        "country_id",
        "country_name",
        "country_iso3",
        "year",
        "value",
        "unit",
    } <= set(df.columns)
    assert pd.api.types.is_numeric_dtype(df["value"])
    bra_2020 = df[(df["country_iso3"] == "BRA") & (df["year"] == 2020)]
    assert bra_2020["value"].iloc[0] == 6.6


def test_parse_payload_empty_data_returns_empty_df_with_columns() -> None:
    df = CepalstatCollector._parse_payload({"data": []})
    assert df.empty
    for col in CepalstatCollector.DATA_FIELDS:
        assert col in df.columns


def test_parse_payload_handles_null_value() -> None:
    df = CepalstatCollector._parse_payload({"data": [_record("BRA", 2020, None)]})
    assert pd.isna(df["value"].iloc[0])


def test_parse_payload_raises_when_data_is_not_list() -> None:
    with pytest.raises(ValueError):
        CepalstatCollector._parse_payload({"data": "oops"})


def test_parse_payload_year_is_nullable_integer_dtype() -> None:
    df = CepalstatCollector._parse_payload(SAMPLE_PAYLOAD)
    # Int64 (nullable) — preserva anos com missing sem converter para float64
    assert str(df["year"].dtype) == "Int64"


# ----------------------------------------------------------------------
# fetch
# ----------------------------------------------------------------------
def _mock_client(payload: Any, *, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_returns_dataframe_and_url() -> None:
    client = _mock_client(SAMPLE_PAYLOAD)
    c = CepalstatCollector(
        indicator_id="1471",
        countries=["BRA", "CHL"],
        api_base="https://x/api/v1",
        http_client=client,
    )
    df, url = c.fetch(reference_period="2020-2021")
    client.close()

    assert len(df) == 3
    assert "indicator/data?" in url
    assert "ids_indicator=1471" in url


def test_fetch_raises_on_http_error() -> None:
    client = _mock_client(None, status=503)
    c = CepalstatCollector(
        indicator_id="1471",
        api_base="https://x/api/v1",
        http_client=client,
    )
    with pytest.raises(httpx.HTTPStatusError):
        c.fetch(reference_period="2022")
    client.close()


# ----------------------------------------------------------------------
# collect — pipeline completo
# ----------------------------------------------------------------------
def test_collect_writes_to_bronze(
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    client = _mock_client(SAMPLE_PAYLOAD)
    c = CepalstatCollector(
        indicator_id="1471",
        countries=["BRA"],
        api_base="https://x/api/v1",
        http_client=client,
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period="2020-2021")
    client.close()

    expected_dir = tmp_bronze_root / "cepalstat" / "indicator_1471" / "2020-2021"
    assert (expected_dir / "data.parquet").exists()
    assert (expected_dir / "_metadata.json").exists()
    assert result.row_count == 3

    table = pq.read_table(result.parquet_path)
    assert "country_iso3" in table.column_names
    assert "year" in table.column_names
    assert "value" in table.column_names


# ----------------------------------------------------------------------
# Conveniências
# ----------------------------------------------------------------------
def test_make_analfabetismo_15m_collector() -> None:
    c = make_analfabetismo_15m_collector()
    assert c.indicator_id == "1471"
    assert c.source == "cepalstat"


def test_make_anos_estudio_promedio_collector() -> None:
    c = make_anos_estudio_promedio_collector()
    assert c.indicator_id == "1407"
