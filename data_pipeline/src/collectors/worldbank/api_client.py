"""Coletor World Bank Open Data — Indicators API.

A API do Banco Mundial expõe indicadores em REST JSON sem autenticação
(rate limit generoso, sem chave necessária).

Formato de resposta:
    [metadata, [records]]
onde `metadata` traz `page`, `pages`, `per_page`, `total`, `lastupdated`
e cada registro tem `indicator.id`, `country.id`, `countryiso3code`,
`date`, `value`, `unit`, `obs_status`, `decimal`.

Indicadores de educação relevantes para este projeto:
    SE.XPD.TOTL.GD.ZS  — gasto em educação (% PIB)
    SE.PRM.CMPT.ZS     — taxa de conclusão da primária
    SE.PRM.ENRR        — matrícula primária bruta
    SE.SEC.ENRR        — matrícula secundária bruta
    SE.ADT.LITR.ZS     — alfabetização adulta
    HD.HCI.OVRL        — Human Capital Index

Doc: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
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


class WorldBankCollector(BaseCollector):
    """Coletor genérico para um indicador da API World Bank.

    Args:
        indicator: ID do indicador (ex.: 'SE.XPD.TOTL.GD.ZS').
        countries: 'all', código ISO-3 ou múltiplos separados por ';'
            (ex.: 'BRA;USA;FIN'). Para todos os países, default é 'all'.
        api_base: override do endpoint (default: settings.worldbank_api_base).
        per_page: tamanho de página (default 1000, máximo permitido pela API).
    """

    source: ClassVar[str] = "worldbank"
    DEFAULT_PER_PAGE: ClassVar[int] = 1000

    def __init__(
        self,
        indicator: str,
        *,
        countries: str = "all",
        api_base: str | None = None,
        per_page: int = DEFAULT_PER_PAGE,
        http_client: httpx.Client | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.indicator = indicator
        self.countries = countries
        self.api_base = (api_base or settings.worldbank_api_base).rstrip("/")
        self.per_page = per_page
        self._http_client = http_client
        # 'SE.XPD.TOTL.GD.ZS' → 'indicator_se_xpd_totl_gd_zs'
        self.dataset = f"indicator_{indicator.lower().replace('.', '_')}"

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------
    def build_url(self, period: str | int, *, page: int = 1) -> str:
        """Monta URL do indicator endpoint.

        `period` pode ser:
          - "2023"        → ano único
          - "2010-2023"   → range (convertido para "2010:2023" pela API)
        """
        api_period = str(period).replace("-", ":")
        params = {
            "date": api_period,
            "format": "json",
            "per_page": str(self.per_page),
            "page": str(page),
        }
        path = f"/country/{self.countries}/indicator/{self.indicator}"
        return f"{self.api_base}{path}?{urlencode(params)}"

    # ------------------------------------------------------------------
    # Fetch (com paginação)
    # ------------------------------------------------------------------
    def fetch(
        self,
        *,
        reference_period: str | int,
        **kwargs: Any,
    ) -> tuple[pd.DataFrame, str]:
        client = self._http_client or httpx.Client(timeout=settings.http_timeout_seconds)
        try:
            records, first_url = self._fetch_paginated(client, reference_period)
        finally:
            if self._http_client is None:
                client.close()

        df = self._records_to_dataframe(records)
        log.info(
            "worldbank.fetch.parsed",
            url=first_url,
            indicator=self.indicator,
            rows=len(df),
            columns=len(df.columns),
        )
        return df, first_url

    def _fetch_paginated(
        self,
        client: httpx.Client,
        period: str | int,
    ) -> tuple[list[dict[str, Any]], str]:
        first_url = self.build_url(period, page=1)
        records: list[dict[str, Any]] = []
        page = 1
        while True:
            url = self.build_url(period, page=page)
            log.info(
                "worldbank.fetch",
                url=url,
                indicator=self.indicator,
                period=str(period),
                page=page,
            )
            response = client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()

            metadata, data = self._split_payload(payload, url=url)
            records.extend(data)

            total_pages = int(metadata.get("pages", 1) or 1)
            if page >= total_pages:
                break
            page += 1
            if page > 50:  # safety cap
                log.warning("worldbank.pagination.cap_hit", indicator=self.indicator, pages=page)
                break
        return records, first_url

    @staticmethod
    def _split_payload(
        payload: Any,
        *,
        url: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """A API retorna [metadata, records] em sucesso ou [{message: [...]}] em erro."""
        if not isinstance(payload, list) or len(payload) < 2:
            # erro semântico (a API retorna 200 com payload de erro)
            raise ValueError(f"World Bank API retornou payload inesperado: {payload!r} (URL: {url})")
        metadata = payload[0] or {}
        data = payload[1] or []
        if not isinstance(data, list):
            raise ValueError(f"World Bank API: registros não-lista em {url}: {data!r}")
        return metadata, data

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    @staticmethod
    def _records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
        """Achata registros aninhados (indicator/country como dicts) em colunas simples."""
        if not records:
            return pd.DataFrame(
                columns=[
                    "indicator_id",
                    "indicator_name",
                    "country_id",
                    "country_name",
                    "country_iso3",
                    "date",
                    "value",
                    "unit",
                    "obs_status",
                    "decimal",
                ]
            )

        rows: list[dict[str, Any]] = []
        for r in records:
            indicator = r.get("indicator") or {}
            country = r.get("country") or {}
            rows.append(
                {
                    "indicator_id": indicator.get("id"),
                    "indicator_name": indicator.get("value"),
                    "country_id": country.get("id"),
                    "country_name": country.get("value"),
                    "country_iso3": r.get("countryiso3code"),
                    "date": r.get("date"),
                    "value": r.get("value"),
                    "unit": r.get("unit"),
                    "obs_status": r.get("obs_status"),
                    "decimal": r.get("decimal"),
                }
            )
        return pd.DataFrame(rows)


# ----------------------------------------------------------------------
# Conveniências para indicadores-chave
# ----------------------------------------------------------------------
def make_education_expenditure_collector(**kwargs: Any) -> WorldBankCollector:
    """SE.XPD.TOTL.GD.ZS — Gasto em educação (% PIB)."""
    return WorldBankCollector(indicator="SE.XPD.TOTL.GD.ZS", **kwargs)


def make_human_capital_index_collector(**kwargs: Any) -> WorldBankCollector:
    """HD.HCI.OVRL — Human Capital Index."""
    return WorldBankCollector(indicator="HD.HCI.OVRL", **kwargs)
