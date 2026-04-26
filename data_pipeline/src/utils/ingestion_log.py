"""Registro de execuções de ingestão em PostgreSQL.

Cada execução de coletor produz uma linha em `ingestion_log` com proveniência
e status. Se o Postgres estiver indisponível, o logger degrada de forma
graciosa (warning + no-op) para não derrubar pipelines de dados.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.logging_config import get_logger

log = get_logger(__name__)


# DDL idempotente — replicado em infra/postgres/migrations/001_ingestion_log.sql.
INGESTION_LOG_DDL = """
CREATE TABLE IF NOT EXISTS ingestion_log (
    id BIGSERIAL PRIMARY KEY,
    source VARCHAR(64)  NOT NULL,
    dataset VARCHAR(128) NOT NULL,
    reference_period VARCHAR(64),
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    status VARCHAR(16) NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    rows_ingested BIGINT,
    output_path TEXT,
    source_url TEXT,
    error_message TEXT,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS ix_ingestion_log_source_dataset
    ON ingestion_log (source, dataset, started_at DESC);
"""


class IngestionLogger:
    """Insere linhas em `ingestion_log` para auditar coletas.

    Caso `dsn` seja None ou a conexão falhe, o logger entra em modo no-op.
    Nunca propaga erros de logging para o coletor.
    """

    def __init__(self, dsn: str | None) -> None:
        self.dsn = dsn
        self._enabled = bool(dsn)
        self._schema_ready = False

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------
    def ensure_schema(self) -> None:
        if not self._enabled or self._schema_ready:
            return
        try:
            import psycopg  # type: ignore[import-not-found]

            with psycopg.connect(self.dsn, autocommit=True) as conn:
                conn.execute(INGESTION_LOG_DDL)
            self._schema_ready = True
        except Exception as exc:  # noqa: BLE001 — log e desativa
            log.warning(
                "ingestion_log.schema_ensure_failed",
                error=str(exc),
                dsn_host=self._dsn_host(),
            )
            self._enabled = False

    # ------------------------------------------------------------------
    # API de runs
    # ------------------------------------------------------------------
    def start_run(
        self,
        *,
        source: str,
        dataset: str,
        reference_period: str | None,
        source_url: str,
    ) -> int | None:
        if not self._enabled:
            return None
        self.ensure_schema()
        if not self._enabled:
            return None
        try:
            import psycopg  # type: ignore[import-not-found]

            with psycopg.connect(self.dsn, autocommit=True) as conn:
                row = conn.execute(
                    """
                    INSERT INTO ingestion_log
                        (source, dataset, reference_period, started_at,
                         status, source_url)
                    VALUES (%s, %s, %s, %s, 'running', %s)
                    RETURNING id
                    """,
                    (
                        source,
                        dataset,
                        reference_period,
                        datetime.now(timezone.utc),
                        source_url,
                    ),
                ).fetchone()
                return int(row[0]) if row else None
        except Exception as exc:  # noqa: BLE001
            log.warning("ingestion_log.start_run_failed", error=str(exc))
            return None

    def finish_run(
        self,
        run_id: int | None,
        *,
        status: str,
        rows_ingested: int | None = None,
        output_path: str | None = None,
        source_url: str | None = None,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if run_id is None or not self._enabled:
            return
        if status not in {"success", "failed"}:
            raise ValueError(f"status inválido: {status!r}")
        try:
            import psycopg  # type: ignore[import-not-found]

            metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
            with psycopg.connect(self.dsn, autocommit=True) as conn:
                conn.execute(
                    """
                    UPDATE ingestion_log
                       SET finished_at   = %s,
                           status        = %s,
                           rows_ingested = %s,
                           output_path   = COALESCE(%s, output_path),
                           source_url    = COALESCE(%s, source_url),
                           error_message = %s,
                           metadata      = %s::jsonb
                     WHERE id = %s
                    """,
                    (
                        datetime.now(timezone.utc),
                        status,
                        rows_ingested,
                        output_path,
                        source_url,
                        error_message,
                        metadata_json,
                        run_id,
                    ),
                )
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "ingestion_log.finish_run_failed",
                error=str(exc),
                run_id=run_id,
                status=status,
            )

    # ------------------------------------------------------------------
    # Util
    # ------------------------------------------------------------------
    def _dsn_host(self) -> str | None:
        if not self.dsn:
            return None
        try:
            after_at = self.dsn.split("@", 1)[1]
            return after_at.split("/", 1)[0]
        except IndexError:
            return None
