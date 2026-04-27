"""Coletor CEPALSTAT — API REST de indicadores LATAM (CEPAL/ECLAC).

Endpoint:

    GET {base}/indicator/data?ids_indicator={id}&ids_areas={iso3+...}
                              &start_year={YYYY}&end_year={YYYY}&format=json

A API CEPALSTAT é REST puro, sem autenticação. A resposta JSON tem a
estrutura típica:

    {
      "indicator": {"id": "...", "name": "...", "unit": "..."},
      "data": [
        {
          "country_id":   "76",
          "country_name": "Brasil",
          "country_iso3": "BRA",
          "year":         2020,
          "value":        6.6,
          "source":       "...",
          "notes":        null,
          ...
        },
        ...
      ]
    }

Bronze preserva os campos originais; o coletor garante apenas tipagem
mínima (`year` int, `value` float) e a presença das colunas-chave.

Doc: https://statistics.cepal.org/portal/cepalstat/index.html
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


class CepalstatCollector(BaseCollector):
    """Coletor de um indicador CEPALSTAT.

    Args:
        indicator_id: ID numérico ou string do indicador (ex.: '1471').
        countries: lista/iterável de códigos ISO-3 (ex.: ['BRA', 'CHL']) ou
            string separada por '+' / ','. None = todos os países da CEPAL.
        api_base: override do endpoint (default: settings.cepalstat_api_base).
        http_client: injeção opcional para testes.
    """

    source: ClassVar[str] = "cepalstat"
    DATA_FIELDS: ClassVar[tuple[str, ...]] = (
        "country_id",
        "country_name",
        "country_iso3",
        "year",
        "value",
        "unit",
        "source",
        "notes",
    )

    def __init__(
        self,
        indicator_id: str | int,
        *,
        countries: str | list[str] | tuple[str, ...] | None = None,
        api_base: str | None = None,
        http_client: httpx.Client | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if not str(indicator_id):
            raise ValueError("indicator_id não pode ser vazio")
        self.indicator_id = str(indicator_id)
        self.countries = self._normalise_countries(countries)
        self.api_base = (api_base or settings.cepalstat_api_base).rstrip("/")
        self._http_client = http_client
        self.dataset = f"indicator_{self.indicator_id.lower()}"

    @staticmethod
    def _normalise_countries(
        countries: str | list[str] | tuple[str, ...] | None,
    ) -> str | None:
        if countries is None:
            return None
        if isinstance(countries, (list, tuple, set)):
            return "+".join(str(c) for c in countries)
        text = str(countries).strip()
        return text or None

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------
    def build_url(self, period: str | int | None = None) -> str:
        params: list[tuple[str, str]] = [
            ("ids_indicator", self.indicator_id),
            ("format", "json"),
        ]
        if self.countries:
            params.append(("ids_areas", self.countries))
        start, end = self._period_bounds(period)
        if start is not None:
            params.append(("start_year", str(start)))
        if end is not None:
            params.append(("end_year", str(end)))
        return f"{self.api_base}/indicator/data?{urlencode(params)}"

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
            log.info("cepalstat.fetch", url=url, indicator=self.indicator_id)
            response = client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
        finally:
            if self._http_client is None:
                client.close()

        df = self._parse_payload(payload)
        log.info(
            "cepalstat.fetch.parsed",
            url=url,
            indicator=self.indicator_id,
            rows=len(df),
            columns=len(df.columns),
        )
        return df, url

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    @classmethod
    def _parse_payload(cls, payload: dict[str, Any]) -> pd.DataFrame:
        """Achata a chave 'data' do payload em DataFrame com tipagem mínima."""
        records = (payload.get("data") if isinstance(payload, dict) else None) or []
        if not isinstance(records, list):
            raise ValueError(
                f"CEPALSTAT: campo 'data' deveria ser lista; recebido: {type(records).__name__}"
            )
        if not records:
            return pd.DataFrame(columns=list(cls.DATA_FIELDS))

        df = pd.DataFrame(records)
        for field in cls.DATA_FIELDS:
            if field not in df.columns:
                df[field] = pd.NA
        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        if "value" in df.columns:
            df["value"] = pd.to_numeric(df["value"], errors="coerce")

        ordered = list(cls.DATA_FIELDS)
        remaining = [c for c in df.columns if c not in ordered]
        return df[ordered + remaining]


# ----------------------------------------------------------------------
# Conveniências para indicadores-chave de educação na CEPALSTAT
# ----------------------------------------------------------------------
def make_analfabetismo_15m_collector(**kwargs: Any) -> CepalstatCollector:
    """Indicador 1471 — Tasa de analfabetismo, 15 años o más (LATAM)."""
    return CepalstatCollector(indicator_id="1471", **kwargs)


def make_anos_estudio_promedio_collector(**kwargs: Any) -> CepalstatCollector:
    """Indicador 1407 — Años de estudio promedio, 25-59 años."""
    return CepalstatCollector(indicator_id="1407", **kwargs)
