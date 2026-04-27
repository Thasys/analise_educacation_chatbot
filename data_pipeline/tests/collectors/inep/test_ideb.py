"""Testes do IdebCollector (XLSX bulk download)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.collectors.inep.ideb import IdebCollector
from src.utils.bronze import BronzeWriter
from src.utils.bulk_downloader import BulkDownloader
from src.utils.ingestion_log import IngestionLogger


def _build_xlsx(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="IDEB", index=False)
    return buf.getvalue()


def _mock_client(payload: bytes) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_constructor_rejects_empty_url() -> None:
    with pytest.raises(ValueError):
        IdebCollector(url="")


def test_build_url_returns_explicit_url() -> None:
    c = IdebCollector(url="https://example.com/ideb_2023.xlsx", cache_root="/tmp")
    assert c.build_url(2023) == "https://example.com/ideb_2023.xlsx"


def test_collect_reads_xlsx_to_bronze(
    tmp_path: Path,
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    df_in = pd.DataFrame(
        {
            "UF": ["AC", "AL", "AM"],
            "IDEB_2021": [5.5, 4.7, 5.0],
            "IDEB_2023": [5.8, 4.9, 5.2],
        }
    )
    client = _mock_client(_build_xlsx(df_in))
    cache = tmp_path / "ideb_cache"
    c = IdebCollector(
        url="https://example.com/ideb_2023_uf.xlsx",
        cache_root=cache,
        downloader=BulkDownloader(cache, http_client=client),
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period=2023)
    client.close()

    expected_dir = tmp_bronze_root / "inep" / "ideb" / "2023"
    assert (expected_dir / "data.parquet").exists()
    assert result.row_count == 3

    table = pq.read_table(result.parquet_path)
    cols = set(table.column_names)
    assert "UF" in cols
    assert "IDEB_2023" in cols


def test_collect_with_skiprows(
    tmp_path: Path,
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    """Planilhas IDEB normalmente têm linhas-cabeçalho descritivas a pular."""
    # Linha 0: descrição; Linha 1: header real; Linhas 2+: dados.
    raw = pd.DataFrame(
        [
            ["Descrição livre", None, None],
            ["UF", "Valor 2021", "Valor 2023"],
            ["AC", 5.5, 5.8],
            ["AL", 4.7, 4.9],
        ]
    )
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        raw.to_excel(writer, sheet_name="IDEB", index=False, header=False)
    payload = buf.getvalue()

    client = _mock_client(payload)
    cache = tmp_path / "ideb_cache"
    c = IdebCollector(
        url="https://example.com/ideb_2023_uf.xlsx",
        sheet_name="IDEB",
        skiprows=1,  # pula a linha de descrição; cabeçalho real é a próxima
        cache_root=cache,
        downloader=BulkDownloader(cache, http_client=client),
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period=2023)
    client.close()

    assert result.row_count == 2
    table = pq.read_table(result.parquet_path)
    assert "UF" in table.column_names
