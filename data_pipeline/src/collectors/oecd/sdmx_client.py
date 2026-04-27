"""Coletor OCDE — Data Explorer via SDMX REST (sdmx.oecd.org).

Endpoint:

    GET {base}/data/{flow_ref}/{key}?startPeriod=YYYY&endPeriod=YYYY
        &dimensionAtObservation=AllDimensions&format=jsondata

`flow_ref` no formato OCDE: '<agency>,<resource_id>,<version>', ex.:
'OECD.EDU.IMEP,DSD_EAG_FIN@DF_FIN_PERSTUDENT,1.0'.

Resposta SDMX-JSON 2.0 — mesma estrutura do UNESCO UIS, então o parsing é
delegado a `utils.sdmx_json.parse_sdmx_json`.

⚠ stats.oecd.org foi descontinuado em 01/07/2024. Use sempre sdmx.oecd.org.
⚠ Rate limit não-autenticado: 60 requisições por hora por IP.

Doc: https://data-explorer.oecd.org/?fs[0]=Topic%2C0%7CEducation%23EDU%23
"""

from __future__ import annotations

from typing import Any, ClassVar
from urllib.parse import urlencode

import httpx
import pandas as pd

from src.collectors.base import BaseCollector
from src.config import settings
from src.logging_config import get_logger
from src.utils.sdmx_json import parse_sdmx_json

log = get_logger(__name__)


class OecdSdmxCollector(BaseCollector):
    """Coletor de um dataflow OCDE via SDMX REST + SDMX-JSON 2.0.

    Args:
        flow_ref: identificador do dataflow OCDE (formato `agency,id,version`).
        key: filtro de dimensões separado por '.' (ex.: 'BRA....').
        countries: alias amigável que sobrepõe o primeiro segmento da `key`
            (assume REF_AREA como dimensão principal — convenção da OCDE).
        api_base: override do endpoint (default: settings.oecd_sdmx_base).
        http_client: injeção opcional para testes.
    """

    source: ClassVar[str] = "oecd"
    DEFAULT_ACCEPT: ClassVar[str] = "application/vnd.sdmx.data+json;version=2.0.0"

    def __init__(
        self,
        flow_ref: str,
        *,
        key: str = "",
        countries: str | None = None,
        api_base: str | None = None,
        http_client: httpx.Client | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if not flow_ref:
            raise ValueError("flow_ref não pode ser vazio")
        self.flow_ref = flow_ref
        self.key = self._apply_country_alias(key, countries)
        self.api_base = (api_base or settings.oecd_sdmx_base).rstrip("/")
        self._http_client = http_client
        slug = (
            flow_ref.replace(",", "_")
            .replace(".", "_")
            .replace("@", "_")
            .lower()
        )
        self.dataset = f"flow_{slug}"

    @staticmethod
    def _apply_country_alias(key: str, countries: str | None) -> str:
        if not countries:
            return key
        if not key:
            return countries
        parts = key.split(".")
        parts[0] = countries
        return ".".join(parts)

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------
    def build_url(self, period: str | int | None = None) -> str:
        path = f"/data/{self.flow_ref}/{self.key}"
        params: dict[str, str] = {
            "dimensionAtObservation": "AllDimensions",
            "format": "jsondata",
        }
        start, end = self._period_bounds(period)
        if start is not None:
            params["startPeriod"] = str(start)
        if end is not None:
            params["endPeriod"] = str(end)
        return f"{self.api_base}{path}?{urlencode(params)}"

    @staticmethod
    def _period_bounds(period: str | int | None) -> tuple[int | None, int | None]:
        if period is None:
            return None, None
        text = str(period).strip()
        if not text or text.lower() == "all":
            return None, None
        if "-" in text:
            start, end = text.split("-", 1)
            return int(start), int(end)
        year = int(text)
        return year, year

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------
    def fetch(
        self,
        *,
        reference_period: str | int,
        **kwargs: Any,
    ) -> tuple[pd.DataFrame, str]:
        url = self.build_url(reference_period)
        client = self._http_client or httpx.Client(timeout=settings.http_timeout_seconds)
        try:
            log.info("oecd.fetch", url=url, flow=self.flow_ref)
            response = client.get(url, headers={"Accept": self.DEFAULT_ACCEPT})
            response.raise_for_status()
            payload = response.json()
        finally:
            if self._http_client is None:
                client.close()

        df = parse_sdmx_json(payload)
        log.info(
            "oecd.fetch.parsed",
            url=url,
            flow=self.flow_ref,
            rows=len(df),
            columns=len(df.columns),
        )
        return df, url


# ----------------------------------------------------------------------
# Conveniências para dataflows-chave de educação OCDE
# ----------------------------------------------------------------------
def make_eag_finance_collector(**kwargs: Any) -> OecdSdmxCollector:
    """Education at a Glance — finance (gasto educacional, % PIB / por aluno)."""
    return OecdSdmxCollector(
        flow_ref="OECD.EDU.IMEP,DSD_EAG_FIN@DF_FIN_PERSTUDENT,1.0", **kwargs
    )


def make_eag_attainment_collector(**kwargs: Any) -> OecdSdmxCollector:
    """Education at a Glance — educational attainment (níveis ISCED concluídos)."""
    return OecdSdmxCollector(
        flow_ref="OECD.EDU.IMEP,DSD_EAG_NEAC@DF_NEAC_DIST,1.0", **kwargs
    )
