-- =============================================================================
-- Migration 001 — tabela ingestion_log
-- =============================================================================
-- Auditoria de execuções de coletores Bronze. Cada linha documenta uma
-- chamada de `BaseCollector.collect()` para um (source, dataset, período).
--
-- Esta DDL é IDEMPOTENTE: também é executada pelo Python (IngestionLogger
-- em src/utils/ingestion_log.py) na primeira chamada. Mantida aqui para
-- ser aplicável manualmente via `psql` em ambientes de troubleshooting.
-- =============================================================================

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

COMMENT ON TABLE  ingestion_log IS 'Auditoria de execuções de coletores Bronze (Fase 1).';
COMMENT ON COLUMN ingestion_log.source           IS 'Nome curto da fonte: ibge, oecd, inep, etc.';
COMMENT ON COLUMN ingestion_log.dataset          IS 'Identificador estável do dataset dentro da fonte.';
COMMENT ON COLUMN ingestion_log.reference_period IS 'Ano ou período de referência dos dados (string, formato livre).';
COMMENT ON COLUMN ingestion_log.metadata         IS 'Metadados livres (JSON), ex.: SHA-256 do parquet, schema, parâmetros.';
