"""Prefect flows para ingestão de dataflows OCDE (SDMX REST + SDMX-JSON 2.0)."""

from __future__ import annotations

from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from src.collectors.oecd.sdmx_client import OecdSdmxCollector
from src.config import settings
from src.utils.bronze import BronzeWriteResult, BronzeWriter
from src.utils.ingestion_log import IngestionLogger


# Cesta default — dataflows centrais do Education at a Glance (EAG).
# IDs revalidados em 2026-04-28 contra o catalogo OECD SDMX (sdmx.oecd.org).
# A famila DSD_EAG_FIN foi reorganizada em DSD_EAG_UOE_FIN no ciclo atual.
DEFAULT_OECD_FLOWS: list[str] = [
    "OECD.EDU.IMEP,DSD_EAG_UOE_FIN@DF_UOE_INDIC_FIN_GDP,1.0",      # gasto educacao % PIB
    "OECD.EDU.IMEP,DSD_EAG_UOE_FIN@DF_UOE_INDIC_FIN_PERSTUD,3.1",  # gasto por aluno
]


@task(retries=3, retry_delay_seconds=120)  # rate limit OCDE: 60/h sem auth
def collect_oecd_flow(
    flow_ref: str,
    reference_period: str,
    *,
    countries: str | None = None,
    key: str = "",
) -> dict[str, Any]:
    """Coleta um dataflow OCDE para um período (ano único, range ou 'all')."""
    logger = get_run_logger()
    logger.info(
        "Coletando OCDE flow=%s período=%s países=%s key=%r",
        flow_ref,
        reference_period,
        countries,
        key,
    )
    collector = OecdSdmxCollector(
        flow_ref=flow_ref,
        countries=countries,
        key=key,
        bronze_writer=BronzeWriter(settings.bronze_root),
        ingestion_logger=IngestionLogger(settings.effective_database_url),
    )
    result: BronzeWriteResult = collector.collect(reference_period=reference_period)
    return result.to_dict()


@flow(name="oecd-education-flows")
def ingest_oecd_education_flows(
    flow_refs: list[str] | None = None,
    *,
    reference_period: str = "2010-2023",
    countries: str | None = None,
) -> list[dict[str, Any]]:
    """Ingere uma cesta de dataflows OCDE para um range de anos."""
    flow_refs = flow_refs or DEFAULT_OECD_FLOWS
    logger = get_run_logger()
    logger.info(
        "Iniciando ingestão de %d dataflows OCDE período=%s",
        len(flow_refs),
        reference_period,
    )

    results: list[dict[str, Any]] = []
    for ref in flow_refs:
        results.append(
            collect_oecd_flow(
                flow_ref=ref,
                reference_period=reference_period,
                countries=countries,
            )
        )
    return results


if __name__ == "__main__":
    ingest_oecd_education_flows()
