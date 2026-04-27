"""Prefect flows para ingestão de dataflows UNESCO UIS (SDMX-JSON 2.0)."""

from __future__ import annotations

from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from src.collectors.unesco.uis_client import UisCollector
from src.config import settings
from src.utils.bronze import BronzeWriteResult, BronzeWriter
from src.utils.ingestion_log import IngestionLogger


# Cesta default — dataflows UIS centrais para comparações BR×Internacional.
DEFAULT_FLOW_REFS: list[str] = [
    "UNESCO,EDU_NON_FINANCE,1.0",  # matrículas, conclusão, atendimento
    "UNESCO,EDU_FINANCE,1.0",      # gasto público em educação
    "UNESCO,SDG,1.0",              # indicadores ODS 4
]


@task(retries=3, retry_delay_seconds=60)
def collect_uis_flow(
    flow_ref: str,
    reference_period: str,
    *,
    countries: str | None = None,
    key: str = "",
) -> dict[str, Any]:
    """Coleta um dataflow UIS para um período (ano único, range ou 'all')."""
    logger = get_run_logger()
    logger.info(
        "Coletando UIS flow=%s período=%s países=%s key=%r",
        flow_ref,
        reference_period,
        countries,
        key,
    )
    collector = UisCollector(
        flow_ref=flow_ref,
        countries=countries,
        key=key,
        bronze_writer=BronzeWriter(settings.bronze_root),
        ingestion_logger=IngestionLogger(settings.effective_database_url),
    )
    result: BronzeWriteResult = collector.collect(reference_period=reference_period)
    return result.to_dict()


@flow(name="unesco-uis-education-flows")
def ingest_uis_education_flows(
    flow_refs: list[str] | None = None,
    *,
    reference_period: str = "2000-2023",
    countries: str | None = None,
) -> list[dict[str, Any]]:
    """Ingere uma cesta de dataflows UIS para um range de anos.

    Args:
        flow_refs: lista de dataflows; default = DEFAULT_FLOW_REFS.
        reference_period: 'all', ano único ou range 'YYYY-YYYY'.
        countries: filtro REF_AREA (ex.: 'BRA' ou 'BRA+USA+FIN'). None = todos.
    """
    flow_refs = flow_refs or DEFAULT_FLOW_REFS
    logger = get_run_logger()
    logger.info(
        "Iniciando ingestão de %d dataflows UIS período=%s",
        len(flow_refs),
        reference_period,
    )

    results: list[dict[str, Any]] = []
    for ref in flow_refs:
        results.append(
            collect_uis_flow(
                flow_ref=ref,
                reference_period=reference_period,
                countries=countries,
            )
        )
    return results


if __name__ == "__main__":
    ingest_uis_education_flows()
