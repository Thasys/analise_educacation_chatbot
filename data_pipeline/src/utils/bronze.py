"""Escrita padronizada na camada Bronze.

Convenções:
  - Layout: `<bronze_root>/<source>/<dataset>/<reference_period>/data.parquet`
  - Sidecar: `_metadata.json` no mesmo diretório, com proveniência completa.
  - Compressão: ZSTD (boa razão e velocidade competitiva).
  - Imutabilidade: a camada Bronze nunca é editada — sempre reescrita por completo.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


@dataclass(frozen=True)
class BronzeWriteResult:
    """Resultado de uma escrita na Bronze (retornado para logging/auditoria)."""

    source: str
    dataset: str
    reference_period: str
    ingested_at: str
    source_url: str
    row_count: int
    column_count: int
    parquet_path: str
    metadata_path: str
    parquet_sha256: str
    columns: list[dict[str, str]] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BronzeWriter:
    """Escreve DataFrames na camada Bronze com metadados de proveniência."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    # ------------------------------------------------------------------
    # Resolução de caminhos
    # ------------------------------------------------------------------
    def path_for(
        self,
        source: str,
        dataset: str,
        reference_period: str | int,
    ) -> Path:
        return self.root / source / dataset / str(reference_period)

    # ------------------------------------------------------------------
    # API principal
    # ------------------------------------------------------------------
    def write(
        self,
        df: pd.DataFrame,
        *,
        source: str,
        dataset: str,
        reference_period: str | int,
        source_url: str,
        extra_metadata: dict[str, Any] | None = None,
        compression: str = "zstd",
    ) -> BronzeWriteResult:
        """Persiste o DataFrame e seu sidecar de metadados.

        Diretórios são criados sob demanda. Arquivos existentes são
        sobrescritos — Bronze é sempre regravada por completo.
        """
        target_dir = self.path_for(source, dataset, reference_period)
        target_dir.mkdir(parents=True, exist_ok=True)

        parquet_path = target_dir / "data.parquet"
        metadata_path = target_dir / "_metadata.json"

        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, parquet_path, compression=compression)

        parquet_bytes = parquet_path.read_bytes()
        digest = hashlib.sha256(parquet_bytes).hexdigest()

        ingested_at = datetime.now(timezone.utc).isoformat()
        columns = [{"name": str(c), "dtype": str(df[c].dtype)} for c in df.columns]

        result = BronzeWriteResult(
            source=source,
            dataset=dataset,
            reference_period=str(reference_period),
            ingested_at=ingested_at,
            source_url=source_url,
            row_count=int(len(df)),
            column_count=int(len(df.columns)),
            parquet_path=str(parquet_path),
            metadata_path=str(metadata_path),
            parquet_sha256=digest,
            columns=columns,
            extra=dict(extra_metadata or {}),
        )

        metadata_path.write_text(
            json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return result
