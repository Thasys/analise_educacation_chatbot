"""Testes do IngestionLogger.

Foco no comportamento de degrade gracioso: sem DSN ou com DSN inválido,
o logger nunca propaga exceções.
"""

from __future__ import annotations

from src.utils.ingestion_log import IngestionLogger


def test_disabled_when_dsn_is_none() -> None:
    logger = IngestionLogger(dsn=None)
    # Todas as operações devem ser no-op
    logger.ensure_schema()
    run_id = logger.start_run(
        source="t", dataset="d", reference_period="2024", source_url="u"
    )
    assert run_id is None
    # finish_run com run_id=None é seguro
    logger.finish_run(None, status="success")


def test_invalid_dsn_does_not_raise() -> None:
    """DSN inválido faz ensure_schema falhar silenciosamente e desativar o logger."""
    logger = IngestionLogger(dsn="postgresql://invalid:invalid@nonexistent-host:5432/none")
    logger.ensure_schema()
    # Após falha, não deve lançar em chamadas subsequentes
    assert logger.start_run(
        source="t", dataset="d", reference_period="2024", source_url="u"
    ) is None


def test_dsn_host_extracts_correctly() -> None:
    logger = IngestionLogger(dsn="postgresql://user:pass@db.example.com:5432/mydb")
    assert logger._dsn_host() == "db.example.com:5432"


def test_dsn_host_returns_none_when_no_dsn() -> None:
    logger = IngestionLogger(dsn=None)
    assert logger._dsn_host() is None
