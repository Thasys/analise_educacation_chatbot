"""Prefect flows para ingestão de indicadores CEPALSTAT (CEPAL)."""

from __future__ import annotations

from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from src.collectors.cepalstat.api_client import CepalstatCollector
from src.config import settings
from src.utils.bronze import BronzeWriteResult, BronzeWriter
from src.utils.ingestion_log import IngestionLogger


# Cesta inicial — indicadores LATAM-comparáveis para BR × América Latina.
# IDs revalidados em 2026-04-28 contra o catálogo `thematic-tree` do novo host
# api-cepalstat.cepal.org. IDs antigos (1471/1407) foram aposentados.
DEFAULT_CEPALSTAT_INDICATORS: list[str] = [
    "2236",  # Literacy rate of population aged 15+, by sex
    "53",    # Illiteracy rate by sex, age group and area
    "460",   # Public expenditure on education
    "184",   # Net enrollment rate by sex and level of education
]


@task(retries=3, retry_delay_seconds=60)
def collect_cepalstat_indicator(
    indicator_id: str,
    reference_period: str,
    *,
    countries: str | None = None,
) -> dict[str, Any]:
    """Coleta um indicador CEPALSTAT para um período (ano único, range ou 'all')."""
    logger = get_run_logger()
    logger.info(
        "Coletando CEPALSTAT indicador=%s período=%s países=%s",
        indicator_id,
        reference_period,
        countries,
    )
    collector = CepalstatCollector(
        indicator_id=indicator_id,
        countries=countries,
        bronze_writer=BronzeWriter(settings.bronze_root),
        ingestion_logger=IngestionLogger(settings.effective_database_url),
    )
    result: BronzeWriteResult = collector.collect(reference_period=reference_period)
    return result.to_dict()


@flow(name="cepalstat-education-indicators")
def ingest_cepalstat_indicators(
    indicators: list[str] | None = None,
    *,
    reference_period: str = "2000-2023",
    countries: str | None = None,
) -> list[dict[str, Any]]:
    """Ingere uma cesta de indicadores CEPALSTAT para um range de anos."""
    indicators = indicators or DEFAULT_CEPALSTAT_INDICATORS
    logger = get_run_logger()
    logger.info(
        "Iniciando ingestão de %d indicadores CEPALSTAT período=%s",
        len(indicators),
        reference_period,
    )

    results: list[dict[str, Any]] = []
    for indicator_id in indicators:
        results.append(
            collect_cepalstat_indicator(
                indicator_id=indicator_id,
                reference_period=reference_period,
                countries=countries,
            )
        )
    return results


if __name__ == "__main__":
    ingest_cepalstat_indicators()
