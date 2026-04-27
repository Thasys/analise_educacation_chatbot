"""Testes do InepBulkCollector (resolução de URL + pipeline com BulkDownloader)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import httpx
import pandas as pd
import pytest

from src.collectors.inep.inep_base import InepBulkCollector
from src.utils.bronze import BronzeWriter
from src.utils.bulk_downloader import BulkDownloader
from src.utils.ingestion_log import IngestionLogger


class FakeInepCollector(InepBulkCollector):
    URL_TEMPLATE: ClassVar[str] = "https://inep.example.com/microdados_{year}.csv"
    dataset: ClassVar[str] = "fake"

    def _load_dataframe(self, local_path: Path) -> pd.DataFrame:
        # Lê o arquivo CSV simples baixado.
        return pd.read_csv(local_path)


CSV_BYTES = b"col_a,col_b\n1,2\n3,4\n5,6\n"


def _mock_client(payload: bytes, *, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_url_template_substitutes_year() -> None:
    c = FakeInepCollector(cache_root="/tmp/inep")
    assert c.build_url(2023) == "https://inep.example.com/microdados_2023.csv"


def test_collect_writes_to_bronze(
    tmp_path: Path,
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    client = _mock_client(CSV_BYTES)
    cache = tmp_path / "inep_cache"
    c = FakeInepCollector(
        cache_root=cache,
        downloader=BulkDownloader(cache, http_client=client),
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period=2023)
    client.close()

    expected_dir = tmp_bronze_root / "inep" / "fake" / "2023"
    assert (expected_dir / "data.parquet").exists()
    assert result.row_count == 3
    assert result.dataset == "fake"

    # Cache do bulk download permanece (não pertence à Bronze).
    assert (cache / "microdados_2023.csv").exists()


def test_subclass_without_url_template_raises() -> None:
    class BrokenCollector(InepBulkCollector):
        dataset: ClassVar[str] = "broken"

    with pytest.raises(ValueError):
        BrokenCollector()


def test_collect_propagates_download_error(
    tmp_path: Path,
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    client = _mock_client(b"", status=404)
    c = FakeInepCollector(
        cache_root=tmp_path / "cache",
        downloader=BulkDownloader(tmp_path / "cache", http_client=client),
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    with pytest.raises(httpx.HTTPStatusError):
        c.collect(reference_period=2023)
    client.close()
