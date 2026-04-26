"""Prefect flows para ingestão de tabelas SIDRA de educação."""

from __future__ import annotations

from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from src.collectors.ibge.sidra_educacao import SidraEducacaoCollector
from src.config import settings
from src.utils.bronze import BronzeWriteResult, BronzeWriter
from src.utils.ingestion_log import IngestionLogger


@task(retries=2, retry_delay_seconds=30)
def collect_sidra_table(
    table_id: int,
    reference_period: str | int,
    *,
    territorial_level: str = "n1",
    territorial_codes: str = "all",
    variables: str = "all",
    classifications: str | None = None,
) -> dict[str, Any]:
    """Task isolável: coleta uma tabela SIDRA para um período."""
    logger = get_run_logger()
    logger.info(
        "Coletando SIDRA t=%s período=%s nível=%s",
        table_id,
        reference_period,
        territorial_level,
    )

    collector = SidraEducacaoCollector(
        table_id=table_id,
        territorial_level=territorial_level,
        territorial_codes=territorial_codes,
        variables=variables,
        classifications=classifications,
        bronze_writer=BronzeWriter(settings.bronze_root),
        ingestion_logger=IngestionLogger(settings.effective_database_url),
    )
    result: BronzeWriteResult = collector.collect(reference_period=reference_period)
    return result.to_dict()


@flow(name="ibge-sidra-pnad-continua-7136")
def ingest_pnad_continua_t7136(
    years: list[int] | None = None,
    *,
    territorial_level: str = "n1",
) -> list[dict[str, Any]]:
    """Ingere a tabela 7136 (taxa de analfabetismo) para uma lista de anos.

    Default: ano corrente menos 1 (PNAD Continua educação é divulgada anual,
    com defasagem de cerca de 6 meses).
    """
    logger = get_run_logger()
    if not years:
        from datetime import date

        years = [date.today().year - 1]

    logger.info("Anos solicitados: %s", years)
    results: list[dict[str, Any]] = []
    for year in years:
        results.append(
            collect_sidra_table(
                table_id=7136,
                reference_period=year,
                territorial_level=territorial_level,
            )
        )
    return results


if __name__ == "__main__":
    # Execução direta: `python -m src.flows.ibge_sidra`
    ingest_pnad_continua_t7136()
