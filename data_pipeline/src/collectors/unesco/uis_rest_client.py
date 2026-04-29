"""Coletor UNESCO UIS — nova API REST publica (2026+).

Em fevereiro/2026 a UIS migrou da arquitetura SDMX para uma API REST
"flat" no host `api.uis.unesco.org/api/public`. O endpoint deprecado
permanece em `data_pipeline/src/collectors/unesco/uis_client.py` como
referencia historica.

Endpoint atual:

    GET https://api.uis.unesco.org/api/public/data/indicators
        ?indicator=<ID1>,<ID2>     (separar multiplos por virgula)
        &geoUnit=<ISO3>            (opcional; padrao = todos)
        &start=YYYY                (opcional; ano inicial)
        &end=YYYY                  (opcional; ano final)
        &disaggregations=true|false
        &version=<version>

Resposta:

    {
      "hints": [...],
      "records": [
        {"indicatorId": "CR.1", "geoUnit": "BRA", "year": 2018, "value": 95.1,
         "magnitude": null, "qualifier": null},
        ...
      ],
      "indicatorMetadata": []
    }

Sem autenticacao, sem rate limit conhecido. Limite de 100k registros
por request -- para acima disso, UIS recomenda BDDS (bulk download).

Doc: https://api.uis.unesco.org/api/public/documentation/
"""

from __future__ import annotations

from typing import Any, ClassVar
from urllib.parse import urlencode

import httpx
import pandas as pd

from src.collectors.base import BaseCollector
from src.config import settings
from src.logging_config import get_logger

log = get_logger(__name__)


class UisRestCollector(BaseCollector):
    """Coletor de um (ou mais) indicador UIS via API REST publica.

    Args:
        indicator: codigo UIS do indicador (ex.: 'CR.1', 'XGOVEXP.IMF',
            'GER.1.M', 'NER.1', etc.). Aceita varios separados por virgula.
        geo_unit: ISO-3 do pais (ex.: 'BRA') ou virgula-separado.
            Default `None` = todos os paises disponiveis.
        api_base: override do endpoint (default settings.unesco_uis_api_base
            mas com path adicional `/data/indicators`).
        http_client: injecao opcional para testes.
    """

    source: ClassVar[str] = "unesco"

    DEFAULT_API_BASE: ClassVar[str] = "https://api.uis.unesco.org/api/public"

    def __init__(
        self,
        indicator: str,
        *,
        geo_unit: str | None = None,
        api_base: str | None = None,
        http_client: httpx.Client | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if not indicator:
            raise ValueError("indicator nao pode ser vazio")
        self.indicator = indicator
        self.geo_unit = geo_unit
        # Settings ainda guarda o host SDMX antigo; usar override por
        # default com o host REST atual.
        self.api_base = (api_base or self.DEFAULT_API_BASE).rstrip("/")
        self._http_client = http_client
        # 'CR.1' -> 'indicator_cr_1'
        slug = indicator.lower().replace(".", "_").replace(",", "_plus_")
        self.dataset = f"indicator_{slug}"

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------
    def build_url(self, period: str | int | None = None) -> str:
        """Monta URL REST para o(s) indicador(es) e periodo."""
        params: dict[str, str] = {"indicator": self.indicator}
        if self.geo_unit:
            params["geoUnit"] = self.geo_unit
        start, end = self._period_bounds(period)
        if start is not None:
            params["start"] = str(start)
        if end is not None:
            params["end"] = str(end)
        return f"{self.api_base}/data/indicators?{urlencode(params)}"

    @staticmethod
    def _period_bounds(period: str | int | None) -> tuple[int | None, int | None]:
        if period is None:
            return None, None
        text = str(period).strip()
        if not text or text.lower() == "all":
            return None, None
        if "-" in text:
            left, right = text.split("-", 1)
            return int(left), int(right)
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
        client = self._http_client or httpx.Client(
            timeout=settings.http_timeout_seconds
        )
        try:
            log.info("uis_rest.fetch", url=url, indicator=self.indicator)
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
        finally:
            if self._http_client is None:
                client.close()

        df = self.parse_records(payload)
        log.info(
            "uis_rest.fetch.parsed",
            url=url,
            indicator=self.indicator,
            rows=len(df),
            columns=len(df.columns) if not df.empty else 0,
        )
        return df, url

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    @staticmethod
    def parse_records(payload: dict[str, Any]) -> pd.DataFrame:
        """Achata `records` em DataFrame (sem alterar nomes ou tipos)."""
        records = payload.get("records") or []
        if not records:
            return pd.DataFrame(
                columns=["indicatorId", "geoUnit", "year", "value", "magnitude", "qualifier"]
            )
        return pd.DataFrame(records)
