"""Prefect flows para ingestão de indicadores World Bank."""

from __future__ import annotations

from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from src.collectors.worldbank.api_client import WorldBankCollector
from src.config import settings
from src.utils.bronze import BronzeWriteResult, BronzeWriter
from src.utils.ingestion_log import IngestionLogger


# Conjunto inicial de indicadores acompanhados (educação básica + capital humano).
# Lista deliberadamente pequena — expandir conforme análises ganham foco.
DEFAULT_EDUCATION_INDICATORS: list[str] = [
    "SE.XPD.TOTL.GD.ZS",  # gasto em educação (% PIB)
    "SE.PRM.CMPT.ZS",     # taxa de conclusão da primária
    "SE.PRM.ENRR",        # matrícula primária bruta
    "SE.SEC.ENRR",        # matrícula secundária bruta
    "SE.ADT.LITR.ZS",     # alfabetização adulta
    "HD.HCI.OVRL",        # Human Capital Index
]


@task(retries=3, retry_delay_seconds=60)
def collect_indicator(
    indicator: str,
    reference_period: str,
    *,
    countries: str = "all",
) -> dict[str, Any]:
    """Coleta um indicador para um período (ano ou range tipo '2000-2023')."""
    logger = get_run_logger()
    logger.info(
        "Coletando World Bank %s período=%s países=%s",
        indicator,
        reference_period,
        countries,
    )
    collector = WorldBankCollector(
        indicator=indicator,
        countries=countries,
        bronze_writer=BronzeWriter(settings.bronze_root),
        ingestion_logger=IngestionLogger(settings.effective_database_url),
    )
    result: BronzeWriteResult = collector.collect(reference_period=reference_period)
    return result.to_dict()


@flow(name="worldbank-education-indicators")
def ingest_education_indicators(
    indicators: list[str] | None = None,
    *,
    reference_period: str = "2000-2023",
    countries: str = "all",
) -> list[dict[str, Any]]:
    """Ingere uma cesta de indicadores de educação para um range de anos.

    Args:
        indicators: lista de IDs de indicadores; default = DEFAULT_EDUCATION_INDICATORS.
        reference_period: ano único ('2023') ou range ('2000-2023').
        countries: 'all' (default) ou códigos ISO-3 separados por ';'.
    """
    indicators = indicators or DEFAULT_EDUCATION_INDICATORS
    logger = get_run_logger()
    logger.info(
        "Iniciando ingestão de %d indicadores World Bank período=%s",
        len(indicators),
        reference_period,
    )

    results: list[dict[str, Any]] = []
    for indicator in indicators:
        results.append(
            collect_indicator(
                indicator=indicator,
                reference_period=reference_period,
                countries=countries,
            )
        )
    return results


if __name__ == "__main__":
    ingest_education_indicators()
