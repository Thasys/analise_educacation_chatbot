"""Testes do CensoEscolarCollector (e variantes SAEB/ENEM)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Any

import httpx
import pyarrow.parquet as pq

from src.collectors.inep.censo_escolar import (
    CensoEscolarCollector,
    EnemCollector,
    SaebCollector,
)
from src.utils.bronze import BronzeWriter
from src.utils.bulk_downloader import BulkDownloader
from src.utils.ingestion_log import IngestionLogger


def _build_zip(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _mock_client(payload: bytes) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def _csv(rows: int) -> bytes:
    """CSV no formato INEP (separador ';', encoding latin-1)."""
    header = "NU_ANO_CENSO;TP_DEPENDENCIA;NU_MATRICULAS\n"
    body = "\n".join(f"2023;1;{i}" for i in range(rows))
    return (header + body + "\n").encode("latin-1")


def test_url_template_default_for_censo() -> None:
    c = CensoEscolarCollector(cache_root="/tmp/inep")
    assert c.build_url(2023) == (
        "https://download.inep.gov.br/microdados/microdados_censo_escolar_2023.zip"
    )


def test_collect_extracts_largest_csv_matching_pattern(
    tmp_path: Path,
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    members = {
        "MATRICULA_BR.CSV": _csv(rows=10),
        "ESCOLA.CSV": _csv(rows=2),
        "leiame.txt": b"docs",
    }
    client = _mock_client(_build_zip(members))
    cache = tmp_path / "inep_cache"

    c = CensoEscolarCollector(
        cache_root=cache,
        downloader=BulkDownloader(cache, http_client=client),
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period=2023)
    client.close()

    # Selecionou o maior CSV cujo nome contém 'matricula' (case-insensitive).
    assert result.row_count == 10
    expected_dir = tmp_bronze_root / "inep" / "censo_escolar" / "2023"
    assert (expected_dir / "data.parquet").exists()
    table = pq.read_table(result.parquet_path)
    assert "NU_MATRICULAS" in table.column_names


def test_collect_raises_when_pattern_does_not_match_any_csv(
    tmp_path: Path,
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    members = {"OUTRO.CSV": _csv(2)}
    client = _mock_client(_build_zip(members))
    cache = tmp_path / "inep_cache"
    c = CensoEscolarCollector(
        cache_root=cache,
        member_pattern="matricula",
        downloader=BulkDownloader(cache, http_client=client),
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    try:
        import pytest

        with pytest.raises(FileNotFoundError):
            c.collect(reference_period=2023)
    finally:
        client.close()


def test_collect_with_custom_member_pattern(
    tmp_path: Path,
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    members = {
        "MATRICULA_BR.CSV": _csv(2),
        "DOCENTE_BR.CSV": _csv(7),
    }
    client = _mock_client(_build_zip(members))
    cache = tmp_path / "inep_cache"
    c = CensoEscolarCollector(
        cache_root=cache,
        member_pattern="docente",
        downloader=BulkDownloader(cache, http_client=client),
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period=2023)
    client.close()
    assert result.row_count == 7


def test_saeb_collector_uses_saeb_url_template() -> None:
    c = SaebCollector(cache_root="/tmp")
    assert "saeb" in c.build_url(2023).lower()
    assert c.dataset == "saeb"


def test_enem_collector_uses_enem_url_template() -> None:
    c = EnemCollector(cache_root="/tmp")
    assert "enem" in c.build_url(2023).lower()
    assert c.dataset == "enem"
