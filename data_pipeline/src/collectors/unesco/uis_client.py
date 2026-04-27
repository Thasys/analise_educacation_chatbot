"""Coletor UNESCO UIS — Bulk Data Download Service via SDMX-JSON 2.0.

A UIS expõe os datasets oficiais (EDU_NON_FINANCE, EDU_FINANCE, SDG, …) como
fluxos SDMX. O endpoint REST padrão é:

    GET {base}/data/{flow_ref}/{key}?startPeriod=YYYY&endPeriod=YYYY
        &dimensionAtObservation=AllDimensions&format=jsondata

Onde:
    flow_ref : identifica o dataflow (ex.: 'UNESCO,EDU_NON_FINANCE,1.0')
    key      : filtro de dimensões separadas por '.', ex.: 'BRA....'
               (vazio = "todas" naquela posição). A ordem segue a definição
               do dataflow.

Saída SDMX-JSON 2.0 (resumida):

    {
      "data": {
        "structures": [{
          "dimensions": {
            "series":      [ {id, name, values:[{id,name},...]}, ... ],
            "observation": [ {id, name, values:[{id,name},...]} ]
          },
          "attributes":   {"observation": [...]}
        }],
        "dataSets": [{
          "series": {
            "0:0:1": {                         # índices nas dimensões `series`
              "observations": {
                "5":  [98.5, 0],               # idx_TIME_PERIOD: [value, attr0_idx, ...]
                "6":  [99.0, 0]
              }
            },
            ...
          }
        }]
      }
    }

Este coletor achata a estrutura para um DataFrame longo:
    | <dim_series_1> | <dim_series_2> | … | TIME_PERIOD | OBS_VALUE | <attr_obs_1> | …

Doc oficial: https://api.uis.unesco.org/sdmx/index.html
"""

from __future__ import annotations

from typing import Any, ClassVar
from urllib.parse import urlencode

import httpx
import pandas as pd

from src.collectors.base import BaseCollector
from src.config import settings
from src.logging_config import get_logger
from src.utils.sdmx_json import parse_sdmx_json as _parse_sdmx_json

log = get_logger(__name__)


class UisCollector(BaseCollector):
    """Coletor de um dataflow UIS via SDMX-JSON 2.0.

    Args:
        flow_ref: identificador do dataflow (ex.: 'UNESCO,EDU_NON_FINANCE,1.0').
        key: filtro de dimensões separado por '.' (ex.: 'BRA....'); '' = todas.
        countries: alias amigável — se fornecido, sobrepõe o primeiro segmento
            de `key` (assume que REF_AREA é a primeira dimensão, padrão da UIS).
            Aceita 'BRA' ou 'BRA+USA+FIN'.
        api_base: override do endpoint (default: settings.unesco_uis_api_base).
        http_client: injeção opcional para testes.
    """

    source: ClassVar[str] = "unesco"

    # Header SDMX-JSON 2.0 — UIS aceita 'jsondata' como atalho equivalente.
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
        self.api_base = (api_base or settings.unesco_uis_api_base).rstrip("/")
        self._http_client = http_client
        # 'UNESCO,EDU_NON_FINANCE,1.0' → 'flow_unesco_edu_non_finance_1_0'
        slug = flow_ref.replace(",", "_").replace(".", "_").lower()
        self.dataset = f"flow_{slug}"

    @staticmethod
    def _apply_country_alias(key: str, countries: str | None) -> str:
        if not countries:
            return key
        # Se `key` for vazio, REF_AREA fica no primeiro segmento e o resto
        # permanece implícito (todas as outras dimensões). UIS aceita key curto.
        if not key:
            return countries
        parts = key.split(".")
        parts[0] = countries
        return ".".join(parts)

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------
    def build_url(self, period: str | int | None = None) -> str:
        """Monta URL SDMX-data com filtros opcionais de período.

        `period` aceita None, 'all', ano único ou 'AAAA-AAAA' (range inclusivo).
        """
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
            log.info("uis.fetch", url=url, flow=self.flow_ref)
            response = client.get(url, headers={"Accept": self.DEFAULT_ACCEPT})
            response.raise_for_status()
            payload = response.json()
        finally:
            if self._http_client is None:
                client.close()

        df = self.parse_sdmx_json(payload)
        log.info(
            "uis.fetch.parsed",
            url=url,
            flow=self.flow_ref,
            rows=len(df),
            columns=len(df.columns),
        )
        return df, url

    # ------------------------------------------------------------------
    # SDMX-JSON 2.0 parsing — delegado ao util compartilhado com OCDE.
    # ------------------------------------------------------------------
    @staticmethod
    def parse_sdmx_json(payload: dict[str, Any]) -> pd.DataFrame:
        """Wrapper estável: delega ao parser comum em utils.sdmx_json."""
        return _parse_sdmx_json(payload)


# ----------------------------------------------------------------------
# Conveniências para dataflows-chave
# ----------------------------------------------------------------------
def make_edu_non_finance_collector(**kwargs: Any) -> UisCollector:
    """EDU_NON_FINANCE — matrículas, taxas de conclusão, atendimento, etc."""
    return UisCollector(flow_ref="UNESCO,EDU_NON_FINANCE,1.0", **kwargs)


def make_edu_finance_collector(**kwargs: Any) -> UisCollector:
    """EDU_FINANCE — gasto governamental e por aluno (% PIB, US$ PPP)."""
    return UisCollector(flow_ref="UNESCO,EDU_FINANCE,1.0", **kwargs)


def make_sdg_collector(**kwargs: Any) -> UisCollector:
    """SDG — indicadores ODS 4 (objetivo de educação)."""
    return UisCollector(flow_ref="UNESCO,SDG,1.0", **kwargs)
