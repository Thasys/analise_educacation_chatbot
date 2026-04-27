"""Testes do coletor IPEADATA (OData v4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.collectors.ipea.odata_client import (
    IpeaDataCollector,
    make_analfabetismo_15m_collector,
    make_ideb_br_series_iniciais_collector,
)
from src.utils.bronze import BronzeWriter
from src.utils.ingestion_log import IngestionLogger


def _value(date: str, val: float | None, *, niv: str = "Brasil", ter: str = "") -> dict[str, Any]:
    return {
        "SERCODIGO": "ANALF15M",
        "VALDATA": date,
        "VALVALOR": val,
        "NIVNOME": niv,
        "TERCODIGO": ter,
    }


SAMPLE_PAYLOAD: dict[str, Any] = {
    "@odata.context": "http://www.ipeadata.gov.br/api/odata4/$metadata#Valores",
    "value": [
        _value("2021-01-01T00:00:00-03:00", 7.0),
        _value("2022-01-01T00:00:00-03:00", 7.0),
        _value("2023-01-01T00:00:00-03:00", 6.6),
    ],
}


# ----------------------------------------------------------------------
# build_url
# ----------------------------------------------------------------------
def test_build_url_no_period_no_filter() -> None:
    c = IpeaDataCollector(
        series_code="ANALF15M",
        api_base="http://www.ipeadata.gov.br/api/odata4",
    )
    url = c.build_url(None)
    assert url == "http://www.ipeadata.gov.br/api/odata4/Metadados('ANALF15M')/Valores"


def test_build_url_all_keyword_skips_filter() -> None:
    c = IpeaDataCollector(series_code="ANALF15M", api_base="http://x/odata4")
    assert c.build_url("all") == "http://x/odata4/Metadados('ANALF15M')/Valores"


def test_build_url_single_year_filter() -> None:
    c = IpeaDataCollector(series_code="ANALF15M", api_base="http://x/odata4")
    url = c.build_url(2023)
    assert "%24filter=year%28VALDATA%29+eq+2023" in url or "$filter=year(VALDATA) eq 2023" in url


def test_build_url_year_range_filter() -> None:
    c = IpeaDataCollector(series_code="ANALF15M", api_base="http://x/odata4")
    url = c.build_url("2010-2023")
    # quoted ou plain — só verificamos que ambos os ends do range aparecem
    assert "ge+2010" in url and "le+2023" in url


def test_build_url_with_territorial_level() -> None:
    c = IpeaDataCollector(
        series_code="IDEB_BR_SAI",
        api_base="http://x/odata4",
        territorial_level="Estados",
    )
    url = c.build_url(2023)
    # ' aparece como %27 quando urlencoded
    assert "NIVNOME+eq+%27Estados%27" in url
    assert "year%28VALDATA%29+eq+2023" in url


def test_build_url_strips_trailing_slash_from_base() -> None:
    c = IpeaDataCollector(series_code="X", api_base="http://x/odata4/")
    assert c.build_url(None) == "http://x/odata4/Metadados('X')/Valores"


def test_constructor_rejects_empty_series_code() -> None:
    with pytest.raises(ValueError):
        IpeaDataCollector(series_code="")


# ----------------------------------------------------------------------
# _records_to_dataframe
# ----------------------------------------------------------------------
def test_records_to_dataframe_typed_columns() -> None:
    df = IpeaDataCollector._records_to_dataframe(SAMPLE_PAYLOAD["value"])
    assert len(df) == 3
    assert {"SERCODIGO", "VALDATA", "VALVALOR", "NIVNOME", "TERCODIGO"} <= set(df.columns)
    assert pd.api.types.is_datetime64_any_dtype(df["VALDATA"])
    assert pd.api.types.is_numeric_dtype(df["VALVALOR"])
    assert df.loc[df["VALDATA"].dt.year == 2023, "VALVALOR"].iloc[0] == 6.6


def test_records_to_dataframe_empty_returns_empty_with_columns() -> None:
    df = IpeaDataCollector._records_to_dataframe([])
    assert df.empty
    for col in ("SERCODIGO", "VALDATA", "VALVALOR", "NIVNOME", "TERCODIGO"):
        assert col in df.columns


def test_records_to_dataframe_handles_missing_value() -> None:
    records = [_value("2020-01-01T00:00:00-03:00", None)]
    df = IpeaDataCollector._records_to_dataframe(records)
    assert pd.isna(df["VALVALOR"].iloc[0])


# ----------------------------------------------------------------------
# fetch (com httpx mockado)
# ----------------------------------------------------------------------
def _make_mock_client(payload: Any) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_returns_dataframe_and_first_url() -> None:
    client = _make_mock_client(SAMPLE_PAYLOAD)
    c = IpeaDataCollector(
        series_code="ANALF15M",
        api_base="http://www.ipeadata.gov.br/api/odata4",
        http_client=client,
    )
    df, url = c.fetch(reference_period="all")
    client.close()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "Metadados('ANALF15M')/Valores" in url


def test_fetch_handles_pagination_via_nextlink() -> None:
    """Quando @odata.nextLink presente, o coletor agrega páginas subsequentes."""
    page1 = {
        "value": [_value("2021-01-01T00:00:00-03:00", 7.0)],
        "@odata.nextLink": "http://www.ipeadata.gov.br/api/odata4/Metadados('ANALF15M')/Valores?$skip=1",
    }
    page2 = {
        "value": [
            _value("2022-01-01T00:00:00-03:00", 7.0),
            _value("2023-01-01T00:00:00-03:00", 6.6),
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=page2 if "$skip" in str(request.url) else page1)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = IpeaDataCollector(
        series_code="ANALF15M",
        api_base="http://www.ipeadata.gov.br/api/odata4",
        http_client=client,
    )
    df, _ = c.fetch(reference_period="all")
    client.close()

    assert len(df) == 3
    assert df["VALDATA"].dt.year.tolist() == [2021, 2022, 2023]


def test_fetch_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server error")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = IpeaDataCollector(
        series_code="ANALF15M",
        api_base="http://x/odata4",
        http_client=client,
    )
    with pytest.raises(httpx.HTTPStatusError):
        c.fetch(reference_period="all")
    client.close()


def test_fetch_raises_when_payload_missing_value_field() -> None:
    client = _make_mock_client({"@odata.context": "x"})  # sem 'value'
    c = IpeaDataCollector(
        series_code="ANALF15M",
        api_base="http://x/odata4",
        http_client=client,
    )
    with pytest.raises(ValueError):
        c.fetch(reference_period="all")
    client.close()


# ----------------------------------------------------------------------
# collect — pipeline completo
# ----------------------------------------------------------------------
def test_collect_writes_to_bronze(
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    client = _make_mock_client(SAMPLE_PAYLOAD)
    c = IpeaDataCollector(
        series_code="ANALF15M",
        api_base="http://www.ipeadata.gov.br/api/odata4",
        http_client=client,
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period="all")
    client.close()

    expected_dir = tmp_bronze_root / "ipea" / "serie_analf15m" / "all"
    assert (expected_dir / "data.parquet").exists()
    assert (expected_dir / "_metadata.json").exists()
    assert result.row_count == 3
    assert result.dataset == "serie_analf15m"

    table = pq.read_table(result.parquet_path)
    assert "SERCODIGO" in table.column_names
    assert "VALDATA" in table.column_names


def test_collect_with_year_period_uses_period_in_path(
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    client = _make_mock_client(SAMPLE_PAYLOAD)
    c = IpeaDataCollector(
        series_code="ANALF15M",
        api_base="http://www.ipeadata.gov.br/api/odata4",
        http_client=client,
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period=2023)
    client.close()
    assert (tmp_bronze_root / "ipea" / "serie_analf15m" / "2023" / "data.parquet").exists()
    assert result.reference_period == "2023"


# ----------------------------------------------------------------------
# Conveniências
# ----------------------------------------------------------------------
def test_make_analfabetismo_15m_collector() -> None:
    c = make_analfabetismo_15m_collector()
    assert c.series_code == "ANALF15M"
    assert c.dataset == "serie_analf15m"
    assert c.source == "ipea"


def test_make_ideb_br_series_iniciais_collector() -> None:
    c = make_ideb_br_series_iniciais_collector()
    assert c.series_code == "IDEB_BR_SAI"
    assert c.dataset == "serie_ideb_br_sai"
