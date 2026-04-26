"""Fixtures globais de teste do data_pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.utils.bronze import BronzeWriter
from src.utils.ingestion_log import IngestionLogger


@pytest.fixture()
def tmp_bronze_root(tmp_path: Path) -> Path:
    """Diretório temporário para a Bronze, isolado por teste."""
    root = tmp_path / "bronze"
    root.mkdir()
    return root


@pytest.fixture()
def bronze_writer(tmp_bronze_root: Path) -> BronzeWriter:
    return BronzeWriter(tmp_bronze_root)


@pytest.fixture()
def disabled_ingestion_logger() -> IngestionLogger:
    """Logger no-op (sem DSN) para testes que não querem tocar Postgres."""
    return IngestionLogger(dsn=None)
