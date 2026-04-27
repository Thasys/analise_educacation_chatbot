"""Prefect flows para ingestão de microdados INEP (bulk download)."""

from __future__ import annotations

from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from src.collectors.inep.censo_escolar import (
    CensoEscolarCollector,
    EnemCollector,
    SaebCollector,
)
from src.collectors.inep.ideb import IdebCollector
from src.config import settings
from src.utils.bronze import BronzeWriteResult, BronzeWriter
from src.utils.ingestion_log import IngestionLogger


@task(retries=2, retry_delay_seconds=120)
def collect_censo_escolar(year: int, **kwargs: Any) -> dict[str, Any]:
    logger = get_run_logger()
    logger.info("Coletando Censo Escolar ano=%s", year)
    collector = CensoEscolarCollector(
        bronze_writer=BronzeWriter(settings.bronze_root),
        ingestion_logger=IngestionLogger(settings.effective_database_url),
        **kwargs,
    )
    result: BronzeWriteResult = collector.collect(reference_period=year)
    return result.to_dict()


@task(retries=2, retry_delay_seconds=120)
def collect_saeb(year: int, **kwargs: Any) -> dict[str, Any]:
    logger = get_run_logger()
    logger.info("Coletando SAEB ano=%s", year)
    collector = SaebCollector(
        bronze_writer=BronzeWriter(settings.bronze_root),
        ingestion_logger=IngestionLogger(settings.effective_database_url),
        **kwargs,
    )
    return collector.collect(reference_period=year).to_dict()


@task(retries=2, retry_delay_seconds=120)
def collect_enem(year: int, **kwargs: Any) -> dict[str, Any]:
    logger = get_run_logger()
    logger.info("Coletando ENEM ano=%s", year)
    collector = EnemCollector(
        bronze_writer=BronzeWriter(settings.bronze_root),
        ingestion_logger=IngestionLogger(settings.effective_database_url),
        **kwargs,
    )
    return collector.collect(reference_period=year).to_dict()


@task(retries=2, retry_delay_seconds=120)
def collect_ideb(
    year: int,
    *,
    url: str,
    sheet_name: str | int = 0,
    skiprows: int = 0,
) -> dict[str, Any]:
    logger = get_run_logger()
    logger.info("Coletando IDEB ano=%s url=%s", year, url)
    collector = IdebCollector(
        url=url,
        sheet_name=sheet_name,
        skiprows=skiprows,
        bronze_writer=BronzeWriter(settings.bronze_root),
        ingestion_logger=IngestionLogger(settings.effective_database_url),
    )
    return collector.collect(reference_period=year).to_dict()


@flow(name="inep-censo-escolar")
def ingest_censo_escolar(years: list[int]) -> list[dict[str, Any]]:
    return [collect_censo_escolar(year=y) for y in years]


@flow(name="inep-saeb")
def ingest_saeb(years: list[int]) -> list[dict[str, Any]]:
    return [collect_saeb(year=y) for y in years]


@flow(name="inep-enem")
def ingest_enem(years: list[int]) -> list[dict[str, Any]]:
    return [collect_enem(year=y) for y in years]


@flow(name="inep-ideb")
def ingest_ideb(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Ingere uma lista de planilhas IDEB.

    Cada item: {"year": int, "url": str, "sheet_name": ..., "skiprows": ...}.
    """
    results: list[dict[str, Any]] = []
    for item in items:
        results.append(
            collect_ideb(
                year=item["year"],
                url=item["url"],
                sheet_name=item.get("sheet_name", 0),
                skiprows=item.get("skiprows", 0),
            )
        )
    return results
