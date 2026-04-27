"""Prefect flows para ingestão de séries IPEADATA (OData v4)."""

from __future__ import annotations

from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from src.collectors.ipea.odata_client import IpeaDataCollector
from src.config import settings
from src.utils.bronze import BronzeWriteResult, BronzeWriter
from src.utils.ingestion_log import IngestionLogger


# Cesta inicial de séries IPEADATA acompanhadas. Foco em educação básica
# brasileira; expansões futuras devem ser adicionadas com justificativa
# (cada série puxa um payload independente para a Bronze).
DEFAULT_EDUCATION_SERIES: list[str] = [
    "ANALF15M",     # taxa de analfabetismo, 15 anos+
    "IDEB_BR_SAI",  # IDEB Brasil, anos iniciais
    "IDEB_BR_SAF",  # IDEB Brasil, anos finais
    "IDEB_BR_EM",   # IDEB Brasil, ensino médio
]


@task(retries=3, retry_delay_seconds=60)
def collect_ipea_series(
    series_code: str,
    reference_period: str,
    *,
    territorial_level: str | None = None,
) -> dict[str, Any]:
    """Coleta uma série IPEADATA para um período (ano único, range ou 'all')."""
    logger = get_run_logger()
    logger.info(
        "Coletando IPEADATA série=%s período=%s nível=%s",
        series_code,
        reference_period,
        territorial_level,
    )
    collector = IpeaDataCollector(
        series_code=series_code,
        territorial_level=territorial_level,
        bronze_writer=BronzeWriter(settings.bronze_root),
        ingestion_logger=IngestionLogger(settings.effective_database_url),
    )
    result: BronzeWriteResult = collector.collect(reference_period=reference_period)
    return result.to_dict()


@flow(name="ipeadata-education-series")
def ingest_education_series(
    series: list[str] | None = None,
    *,
    reference_period: str = "all",
    territorial_level: str | None = None,
) -> list[dict[str, Any]]:
    """Ingere uma cesta de séries de educação do IPEADATA.

    Args:
        series: lista de SERCODIGOs; default = DEFAULT_EDUCATION_SERIES.
        reference_period: 'all', ano único ('2023') ou range ('2010-2023').
        territorial_level: filtro opcional ('Brasil', 'Estados', 'Municípios').
    """
    series = series or DEFAULT_EDUCATION_SERIES
    logger = get_run_logger()
    logger.info(
        "Iniciando ingestão de %d séries IPEADATA período=%s",
        len(series),
        reference_period,
    )

    results: list[dict[str, Any]] = []
    for code in series:
        results.append(
            collect_ipea_series(
                series_code=code,
                reference_period=reference_period,
                territorial_level=territorial_level,
            )
        )
    return results


if __name__ == "__main__":
    ingest_education_series()
