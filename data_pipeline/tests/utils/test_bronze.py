"""Testes do BronzeWriter."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from src.utils.bronze import BronzeWriter


def test_path_for_segments_correctly(tmp_bronze_root: Path) -> None:
    writer = BronzeWriter(tmp_bronze_root)
    path = writer.path_for("ibge", "sidra_7136", 2023)
    assert path == tmp_bronze_root / "ibge" / "sidra_7136" / "2023"


def test_write_creates_parquet_and_metadata(bronze_writer: BronzeWriter) -> None:
    df = pd.DataFrame(
        {
            "valor": ["6.6", "7.1", "5.4"],
            "uf": ["BR", "PE", "SP"],
        }
    )
    result = bronze_writer.write(
        df,
        source="ibge",
        dataset="sidra_7136",
        reference_period=2023,
        source_url="https://example.test/sidra",
        extra_metadata={"table_id": 7136},
    )

    parquet_path = Path(result.parquet_path)
    metadata_path = Path(result.metadata_path)

    assert parquet_path.exists()
    assert metadata_path.exists()
    assert result.row_count == 3
    assert result.column_count == 2
    assert result.parquet_sha256  # 64 hex chars
    assert len(result.parquet_sha256) == 64
    assert result.extra == {"table_id": 7136}


def test_write_parquet_round_trip_preserves_data(bronze_writer: BronzeWriter) -> None:
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
    result = bronze_writer.write(
        df,
        source="t",
        dataset="d",
        reference_period="2024",
        source_url="https://example.test",
    )
    table = pq.read_table(result.parquet_path)
    assert table.num_rows == 3
    assert set(table.column_names) == {"a", "b"}


def test_write_metadata_json_is_valid_and_complete(bronze_writer: BronzeWriter) -> None:
    df = pd.DataFrame({"x": [1.0, 2.0]})
    result = bronze_writer.write(
        df,
        source="src",
        dataset="ds",
        reference_period=2025,
        source_url="https://example.test",
    )

    payload = json.loads(Path(result.metadata_path).read_text(encoding="utf-8"))
    expected_keys = {
        "source",
        "dataset",
        "reference_period",
        "ingested_at",
        "source_url",
        "row_count",
        "column_count",
        "parquet_path",
        "metadata_path",
        "parquet_sha256",
        "columns",
        "extra",
    }
    assert expected_keys.issubset(payload.keys())
    assert payload["reference_period"] == "2025"
    assert payload["columns"] == [{"name": "x", "dtype": "float64"}]


def test_write_overwrites_existing(bronze_writer: BronzeWriter) -> None:
    """Bronze é regravada por completo a cada coleta — sem append."""
    df1 = pd.DataFrame({"v": [1, 2, 3]})
    df2 = pd.DataFrame({"v": [10, 20]})

    bronze_writer.write(
        df1, source="s", dataset="d", reference_period=1, source_url="u"
    )
    result = bronze_writer.write(
        df2, source="s", dataset="d", reference_period=1, source_url="u"
    )

    table = pq.read_table(result.parquet_path)
    assert table.num_rows == 2
