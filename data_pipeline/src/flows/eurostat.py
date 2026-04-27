"""Prefect flows para ingestão de datasets Eurostat (JSON-stat 2.0)."""

from __future__ import annotations

from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from src.collectors.eurostat.jsonstat_client import EurostatCollector
from src.config import settings
from src.utils.bronze import BronzeWriteResult, BronzeWriter
from src.utils.ingestion_log import IngestionLogger


# Cesta default — datasets centrais da educação europeia (UOE coleta).
DEFAULT_EUROSTAT_DATASETS: list[str] = [
    "educ_uoe_enrt01",   # matrículas por nível ISCED
    "educ_uoe_fine01",   # despesa em educação por fonte e categoria
    "edat_lfse_14",      # abandono escolar precoce (% 18-24)
]


@task(retries=3, retry_delay_seconds=60)
def collect_eurostat_dataset(
    dataset_code: str,
    reference_period: str,
    *,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Coleta um dataset Eurostat para um período (ano único, range ou 'all')."""
    logger = get_run_logger()
    logger.info(
        "Coletando Eurostat dataset=%s período=%s filtros=%s",
        dataset_code,
        reference_period,
        filters,
    )
    collector = EurostatCollector(
        dataset_code=dataset_code,
        filters=filters,
        bronze_writer=BronzeWriter(settings.bronze_root),
        ingestion_logger=IngestionLogger(settings.effective_database_url),
    )
    result: BronzeWriteResult = collector.collect(reference_period=reference_period)
    return result.to_dict()


@flow(name="eurostat-education-datasets")
def ingest_eurostat_education_datasets(
    datasets: list[str] | None = None,
    *,
    reference_period: str = "2010-2023",
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Ingere uma cesta de datasets de educação do Eurostat.

    Args:
        datasets: lista de códigos; default = DEFAULT_EUROSTAT_DATASETS.
        reference_period: 'all', ano único ou range 'YYYY-YYYY'.
        filters: filtros adicionais por dimensão (geo, sex, age, isced11...).
    """
    datasets = datasets or DEFAULT_EUROSTAT_DATASETS
    logger = get_run_logger()
    logger.info(
        "Iniciando ingestão de %d datasets Eurostat período=%s",
        len(datasets),
        reference_period,
    )

    results: list[dict[str, Any]] = []
    for code in datasets:
        results.append(
            collect_eurostat_dataset(
                dataset_code=code,
                reference_period=reference_period,
                filters=filters,
            )
        )
    return results


if __name__ == "__main__":
    ingest_eurostat_education_datasets()
