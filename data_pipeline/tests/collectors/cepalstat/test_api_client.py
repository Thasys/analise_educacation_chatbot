"""Testes do coletor CEPALSTAT (REST v1, host api-cepalstat.cepal.org)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.collectors.cepalstat.api_client import (
    CepalstatCollector,
    make_alfabetizacao_15m_collector,
    make_analfabetismo_15m_collector,
    make_gasto_publico_educacao_collector,
)
from src.utils.bronze import BronzeWriter
from src.utils.ingestion_log import IngestionLogger


# ----------------------------------------------------------------------
# Fixtures de payload
# ----------------------------------------------------------------------

SAMPLE_DIMS_PAYLOAD: dict[str, Any] = {
    "header": {"success": True, "code": 200},
    "body": {
        "dimensions": [
            {
                "id": 144,
                "name": "Sex__ESTANDAR",
                "members": [
                    {"id": 146, "name": "Both sexes"},
                    {"id": 265, "name": "Men"},
                    {"id": 266, "name": "Women"},
                ],
            },
            {
                "id": 208,
                "name": "Country__ESTANDAR",
                "members": [
                    {"id": 222, "name": "Brazil"},
                    {"id": 223, "name": "Chile"},
                ],
            },
            {
                "id": 29117,
                "name": "Years__ESTANDAR",
                "members": [
                    {"id": 68309, "name": "2020"},
                    {"id": 68310, "name": "2021"},
                    {"id": 68311, "name": "2022"},
                ],
            },
        ]
    },
}


SAMPLE_DATA_PAYLOAD: dict[str, Any] = {
    "header": {"success": True, "code": 200},
    "body": {
        "metadata": {
            "indicator_id": 2236,
            "indicator_name": "Literacy rate of population aged 15+",
            "unit": "Percentage",
        },
        "data": [
            {"value": "97.29", "iso3": "BRA",
             "dim_144": 146, "dim_208": 222, "dim_29117": 68309},
            {"value": "97.45", "iso3": "BRA",
             "dim_144": 146, "dim_208": 222, "dim_29117": 68310},
            {"value": "96.50", "iso3": "CHL",
             "dim_144": 146, "dim_208": 223, "dim_29117": 68309},
            {"value": None,    "iso3": "BRA",
             "dim_144": 146, "dim_208": 222, "dim_29117": 68311},
        ],
    },
}


# ----------------------------------------------------------------------
# Constructor
# ----------------------------------------------------------------------
def test_constructor_accepts_int_id() -> None:
    c = CepalstatCollector(indicator_id=2236, api_base="https://x/api/v1")
    assert c.indicator_id == "2236"
    assert c.dataset == "indicator_2236"


def test_constructor_normalises_country_list() -> None:
    c = CepalstatCollector(
        indicator_id="2236", countries=["bra", "CHL", "ARG"], api_base="https://x/api/v1"
    )
    assert c.countries == ["BRA", "CHL", "ARG"]


def test_constructor_accepts_country_string_plus_separated() -> None:
    c = CepalstatCollector(
        indicator_id="2236", countries="BRA+CHL", api_base="https://x/api/v1"
    )
    assert c.countries == ["BRA", "CHL"]


def test_constructor_accepts_country_string_comma_separated() -> None:
    c = CepalstatCollector(
        indicator_id="2236", countries="BRA,chl,arg", api_base="https://x/api/v1"
    )
    assert c.countries == ["BRA", "CHL", "ARG"]


def test_constructor_handles_none_countries() -> None:
    c = CepalstatCollector(indicator_id="2236", api_base="https://x/api/v1")
    assert c.countries is None


# ----------------------------------------------------------------------
# build_url
# ----------------------------------------------------------------------
def test_build_url_data_minimal() -> None:
    c = CepalstatCollector(indicator_id="2236", api_base="https://x/api/v1")
    url = c.build_url(None)
    assert url.startswith("https://x/api/v1/indicator/2236/data?")
    assert "format=json" in url


def test_build_dimensions_url() -> None:
    c = CepalstatCollector(indicator_id="2236", api_base="https://x/api/v1")
    url = c.build_dimensions_url()
    assert url.startswith("https://x/api/v1/indicator/2236/dimensions?")
    assert "format=json" in url
    assert "lang=en" in url


def test_period_bounds_handles_range() -> None:
    assert CepalstatCollector._period_bounds("2010-2023") == (2010, 2023)


def test_period_bounds_handles_single_year() -> None:
    assert CepalstatCollector._period_bounds("2022") == (2022, 2022)
    assert CepalstatCollector._period_bounds(2022) == (2022, 2022)


def test_period_bounds_returns_none_for_all() -> None:
    assert CepalstatCollector._period_bounds("all") == (None, None)
    assert CepalstatCollector._period_bounds(None) == (None, None)
    assert CepalstatCollector._period_bounds("") == (None, None)


# ----------------------------------------------------------------------
# _build_dim_lookup
# ----------------------------------------------------------------------
def test_build_dim_lookup_classifies_dimensions() -> None:
    member_labels, purpose = CepalstatCollector._build_dim_lookup(SAMPLE_DIMS_PAYLOAD)
    assert purpose[144] == "sex"
    assert purpose[208] == "country"
    assert purpose[29117] == "year"
    assert member_labels[144][146] == "Both sexes"
    assert member_labels[29117][68309] == "2020"
    assert member_labels[208][222] == "Brazil"


def test_build_dim_lookup_handles_empty() -> None:
    member_labels, purpose = CepalstatCollector._build_dim_lookup({})
    assert member_labels == {}
    assert purpose == {}


# ----------------------------------------------------------------------
# _parse_payload
# ----------------------------------------------------------------------
def test_parse_payload_resolves_dim_year_into_canonical_column() -> None:
    df = CepalstatCollector._parse_payload(SAMPLE_DATA_PAYLOAD, SAMPLE_DIMS_PAYLOAD)
    assert "year" in df.columns
    assert df["year"].tolist() == [2020, 2021, 2020, 2022]
    assert str(df["year"].dtype) == "Int64"


def test_parse_payload_resolves_country_iso3_from_payload() -> None:
    df = CepalstatCollector._parse_payload(SAMPLE_DATA_PAYLOAD, SAMPLE_DIMS_PAYLOAD)
    assert "country_iso3" in df.columns
    assert df["country_iso3"].tolist() == ["BRA", "BRA", "CHL", "BRA"]


def test_parse_payload_resolves_sex_label() -> None:
    df = CepalstatCollector._parse_payload(SAMPLE_DATA_PAYLOAD, SAMPLE_DIMS_PAYLOAD)
    assert "sex" in df.columns
    assert (df["sex"] == "Both sexes").all()


def test_parse_payload_carries_indicator_metadata() -> None:
    df = CepalstatCollector._parse_payload(SAMPLE_DATA_PAYLOAD, SAMPLE_DIMS_PAYLOAD)
    assert (df["indicator_id"] == "2236").all()
    assert (df["indicator_name"] == "Literacy rate of population aged 15+").all()


def test_parse_payload_value_is_numeric() -> None:
    df = CepalstatCollector._parse_payload(SAMPLE_DATA_PAYLOAD, SAMPLE_DIMS_PAYLOAD)
    assert pd.api.types.is_numeric_dtype(df["value"])
    assert df["value"].iloc[0] == 97.29
    assert pd.isna(df["value"].iloc[3])


def test_parse_payload_empty_data_returns_empty_df_with_columns() -> None:
    df = CepalstatCollector._parse_payload({"body": {"data": []}}, SAMPLE_DIMS_PAYLOAD)
    assert df.empty
    for col in CepalstatCollector.DATA_FIELDS:
        assert col in df.columns


def test_parse_payload_filters_by_period() -> None:
    df = CepalstatCollector._parse_payload(
        SAMPLE_DATA_PAYLOAD, SAMPLE_DIMS_PAYLOAD, reference_period="2020-2020"
    )
    assert (df["year"] == 2020).all()
    assert len(df) == 2


def test_parse_payload_filters_by_countries() -> None:
    df = CepalstatCollector._parse_payload(
        SAMPLE_DATA_PAYLOAD, SAMPLE_DIMS_PAYLOAD, countries=["CHL"]
    )
    assert (df["country_iso3"] == "CHL").all()
    assert len(df) == 1


def test_parse_payload_raises_when_data_is_not_list() -> None:
    with pytest.raises(ValueError):
        CepalstatCollector._parse_payload({"body": {"data": "oops"}}, SAMPLE_DIMS_PAYLOAD)


# ----------------------------------------------------------------------
# fetch — exige duas chamadas (data + dimensions)
# ----------------------------------------------------------------------
def _mock_client_two_endpoints(
    data_payload: Any, dims_payload: Any, *, status: int = 200
) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/dimensions" in request.url.path:
            return httpx.Response(status, json=dims_payload)
        return httpx.Response(status, json=data_payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_returns_dataframe_and_data_url() -> None:
    client = _mock_client_two_endpoints(SAMPLE_DATA_PAYLOAD, SAMPLE_DIMS_PAYLOAD)
    c = CepalstatCollector(
        indicator_id="2236",
        api_base="https://x/api/v1",
        http_client=client,
    )
    df, url = c.fetch(reference_period="2020-2022")
    client.close()

    assert len(df) == 4
    assert "indicator/2236/data" in url
    assert (df["country_iso3"].dropna().isin(["BRA", "CHL"])).all()


def test_fetch_raises_on_http_error_data() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/dimensions" in request.url.path:
            return httpx.Response(200, json=SAMPLE_DIMS_PAYLOAD)
        return httpx.Response(503, json=None)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = CepalstatCollector(
        indicator_id="2236",
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
    client = _mock_client_two_endpoints(SAMPLE_DATA_PAYLOAD, SAMPLE_DIMS_PAYLOAD)
    c = CepalstatCollector(
        indicator_id="2236",
        countries=["BRA"],
        api_base="https://x/api/v1",
        http_client=client,
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period="2020-2022")
    client.close()

    expected_dir = tmp_bronze_root / "cepalstat" / "indicator_2236" / "2020-2022"
    assert (expected_dir / "data.parquet").exists()
    assert (expected_dir / "_metadata.json").exists()
    # 4 records no payload, mas filtrado para BRA -> 3
    assert result.row_count == 3

    table = pq.read_table(result.parquet_path)
    assert "country_iso3" in table.column_names
    assert "year" in table.column_names
    assert "value" in table.column_names


# ----------------------------------------------------------------------
# Conveniencias
# ----------------------------------------------------------------------
def test_make_alfabetizacao_15m_collector() -> None:
    c = make_alfabetizacao_15m_collector()
    assert c.indicator_id == "2236"
    assert c.source == "cepalstat"


def test_make_analfabetismo_15m_collector() -> None:
    c = make_analfabetismo_15m_collector()
    assert c.indicator_id == "53"


def test_make_gasto_publico_educacao_collector() -> None:
    c = make_gasto_publico_educacao_collector()
    assert c.indicator_id == "460"
