"""Testes do coletor SIDRA — IBGE."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.collectors.ibge.sidra_educacao import (
    SidraEducacaoCollector,
    make_pnad_continua_t7136,
)
from src.utils.bronze import BronzeWriter
from src.utils.ingestion_log import IngestionLogger


# Payload mínimo no formato SIDRA: header + 2 linhas.
SAMPLE_PAYLOAD: list[dict[str, Any]] = [
    {
        "NC": "Nível Territorial (Código)",
        "NN": "Nível Territorial",
        "MC": "Município (Código)",
        "MN": "Município",
        "V": "Valor",
        "D1C": "Brasil (Código)",
        "D1N": "Brasil",
        "D2C": "Variável (Código)",
        "D2N": "Variável",
        "D3C": "Ano (Código)",
        "D3N": "Ano",
    },
    {
        "NC": "1",
        "NN": "Brasil",
        "MC": "",
        "MN": "",
        "V": "6.6",
        "D1C": "1",
        "D1N": "Brasil",
        "D2C": "1",
        "D2N": "Taxa de analfabetismo",
        "D3C": "2023",
        "D3N": "2023",
    },
    {
        "NC": "1",
        "NN": "Brasil",
        "MC": "",
        "MN": "",
        "V": "7.0",
        "D1C": "1",
        "D1N": "Brasil",
        "D2C": "1",
        "D2N": "Taxa de analfabetismo",
        "D3C": "2022",
        "D3N": "2022",
    },
]


# ----------------------------------------------------------------------
# build_url
# ----------------------------------------------------------------------
def test_build_url_default_segments() -> None:
    c = SidraEducacaoCollector(table_id=7136, api_base="https://apisidra.ibge.gov.br")
    url = c.build_url(2023)
    assert url == "https://apisidra.ibge.gov.br/values/t/7136/n1/all/v/all/p/2023"


def test_build_url_with_uf_and_classifications() -> None:
    c = SidraEducacaoCollector(
        table_id=7144,
        territorial_level="n3",
        territorial_codes="26,35",
        variables="123",
        classifications="c2/4,5",
        api_base="https://apisidra.ibge.gov.br",
    )
    url = c.build_url("2024")
    assert url == "https://apisidra.ibge.gov.br/values/t/7144/n3/26,35/v/123/p/2024/c2/4,5"


def test_build_url_strips_trailing_slash_from_base() -> None:
    c = SidraEducacaoCollector(table_id=1, api_base="https://apisidra.ibge.gov.br/")
    assert c.build_url(1).startswith("https://apisidra.ibge.gov.br/values/")


# ----------------------------------------------------------------------
# _parse_payload
# ----------------------------------------------------------------------
def test_parse_payload_renames_columns_with_header() -> None:
    df = SidraEducacaoCollector._parse_payload(SAMPLE_PAYLOAD)
    assert len(df) == 2
    # Renamed columns from header
    assert "Valor" in df.columns
    assert "Ano" in df.columns
    assert "Brasil" in df.columns


def test_parse_payload_empty_returns_empty_dataframe() -> None:
    df = SidraEducacaoCollector._parse_payload([])
    assert df.empty


def test_parse_payload_only_header_returns_empty_with_columns() -> None:
    df = SidraEducacaoCollector._parse_payload([SAMPLE_PAYLOAD[0]])
    assert df.empty
    # Esperamos os rótulos do header como nomes de coluna
    assert "Valor" in df.columns


# ----------------------------------------------------------------------
# fetch (com httpx mockado via MockTransport)
# ----------------------------------------------------------------------
def _make_mock_client(payload: list[dict[str, Any]]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    return httpx.Client(transport=transport)


def test_fetch_returns_dataframe_and_url() -> None:
    client = _make_mock_client(SAMPLE_PAYLOAD)
    c = SidraEducacaoCollector(
        table_id=7136,
        api_base="https://apisidra.ibge.gov.br",
        http_client=client,
    )
    df, url = c.fetch(reference_period=2023)
    client.close()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert "Valor" in df.columns
    assert url.endswith("/p/2023")


def test_fetch_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server error")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = SidraEducacaoCollector(
        table_id=7136, api_base="https://apisidra.ibge.gov.br", http_client=client
    )
    with pytest.raises(httpx.HTTPStatusError):
        c.fetch(reference_period=2023)
    client.close()


# ----------------------------------------------------------------------
# collect — pipeline completo
# ----------------------------------------------------------------------
def test_collect_writes_to_bronze_and_returns_metadata(
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    client = _make_mock_client(SAMPLE_PAYLOAD)
    c = SidraEducacaoCollector(
        table_id=7136,
        api_base="https://apisidra.ibge.gov.br",
        http_client=client,
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )

    result = c.collect(reference_period=2023)
    client.close()

    expected_dir = tmp_bronze_root / "ibge" / "sidra_7136" / "2023"
    assert (expected_dir / "data.parquet").exists()
    assert (expected_dir / "_metadata.json").exists()
    assert result.row_count == 2
    assert result.dataset == "sidra_7136"

    # Round-trip: parquet contains parsed data
    table = pq.read_table(result.parquet_path)
    assert "Valor" in table.column_names


def test_make_pnad_continua_t7136_returns_collector_with_correct_table() -> None:
    c = make_pnad_continua_t7136()
    assert c.table_id == 7136
    assert c.dataset == "sidra_7136"
    assert c.source == "ibge"
