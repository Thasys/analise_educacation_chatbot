"""Prefect flows para ingestão de indicadores UNESCO UIS (REST API publica).

Em fevereiro/2026 a UIS migrou da arquitetura SDMX para REST. Este flow
agora usa `UisRestCollector` apontando para `api.uis.unesco.org/api/public`.
O coletor SDMX legado permanece em `src/collectors/unesco/uis_client.py`
para referencia historica (mas o endpoint subjacente esta fora do ar).
"""

from __future__ import annotations

from typing import Any

from prefect import flow, task
from prefect.logging import get_run_logger

from src.collectors.unesco.uis_rest_client import UisRestCollector
from src.config import settings
from src.utils.bronze import BronzeWriteResult, BronzeWriter
from src.utils.ingestion_log import IngestionLogger


# Cesta default — indicadores UIS centrais para comparações BR×Internacional.
# Codigos da Data Browser (https://databrowser.uis.unesco.org/).
DEFAULT_INDICATORS: list[str] = [
    "CR.1",          # Taxa de conclusao do ensino fundamental
    "CR.2",          # Taxa de conclusao do ensino medio
    "NER.1",         # Taxa liquida de matricula no fundamental
    "NER.2",         # Taxa liquida de matricula no medio
    "XGDP.FSGOV",    # Gasto governamental em educacao (% PIB)
    "XGOVEXP.IMF",   # Gasto em educacao (% gasto govt total) -- NAO equivale a % PIB
    "FOSEP.1.GPV",   # Gasto governo por aluno (PPP, fundamental)
    "LR.AG15T99",    # Taxa de alfabetizacao 15+ (UIS estimativas)
]


@task(retries=3, retry_delay_seconds=60)
def collect_uis_indicator(
    indicator: str,
    reference_period: str,
    *,
    geo_unit: str | None = None,
) -> dict[str, Any]:
    """Coleta um indicador UIS para um período (ano único, range ou 'all')."""
    logger = get_run_logger()
    logger.info(
        "Coletando UIS indicator=%s período=%s geoUnit=%s",
        indicator,
        reference_period,
        geo_unit,
    )
    collector = UisRestCollector(
        indicator=indicator,
        geo_unit=geo_unit,
        bronze_writer=BronzeWriter(settings.bronze_root),
        ingestion_logger=IngestionLogger(settings.effective_database_url),
    )
    result: BronzeWriteResult = collector.collect(reference_period=reference_period)
    return result.to_dict()


@flow(name="unesco-uis-education-indicators")
def ingest_uis_education_indicators(
    indicators: list[str] | None = None,
    *,
    reference_period: str = "2000-2023",
    geo_unit: str | None = None,
) -> list[dict[str, Any]]:
    """Ingere uma cesta de indicadores UIS para um range de anos.

    Args:
        indicators: lista de codigos UIS; default = DEFAULT_INDICATORS.
        reference_period: 'all', ano único ou range 'YYYY-YYYY'.
        geo_unit: filtro ISO-3 do pais (ex.: 'BRA' ou 'BRA,USA,FIN').
            None = todos os paises.
    """
    indicators = indicators or DEFAULT_INDICATORS
    logger = get_run_logger()
    logger.info(
        "Iniciando ingestão de %d indicadores UIS período=%s",
        len(indicators),
        reference_period,
    )

    results: list[dict[str, Any]] = []
    for code in indicators:
        results.append(
            collect_uis_indicator(
                indicator=code,
                reference_period=reference_period,
                geo_unit=geo_unit,
            )
        )
    return results


if __name__ == "__main__":
    ingest_uis_education_indicators()
