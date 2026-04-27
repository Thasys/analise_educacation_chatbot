"""Coletor IPEADATA — séries históricas via API OData v4.

A API do IPEA expõe séries socioeconômicas brasileiras em OData v4 RESTful,
sem autenticação. Endpoints relevantes:

    GET /Metadados                              — catálogo de séries
    GET /Metadados('SERCODIGO')                 — metadados de uma série
    GET /Metadados('SERCODIGO')/Valores         — valores observados (preferido)

Resposta OData padrão:
    {
      "@odata.context": "...",
      "value": [ {...}, {...} ],
      "@odata.nextLink": "..."   # opcional, paginação
    }

Cada registro de valor tem:
    SERCODIGO  — código curto da série (ex.: 'ANALF15M')
    VALDATA    — data ISO 8601 (com timezone -03:00)
    VALVALOR   — valor numérico (pode ser nulo)
    NIVNOME    — nível territorial (ex.: 'Brasil', 'Estados', 'Municípios')
    TERCODIGO  — código IBGE do território (vazio quando NIVNOME='Brasil')

Séries de educação relevantes para este projeto (exemplos):
    ANALF15M       — taxa de analfabetismo, 15 anos ou mais
    IDEB_BR_SAI    — IDEB Brasil, séries iniciais
    IDEB_BR_SAF    — IDEB Brasil, séries finais
    IDEB_BR_EM     — IDEB Brasil, ensino médio
    SE_DESPEDPIB   — despesa pública em educação (% PIB)

Doc: http://www.ipeadata.gov.br/api/odata4/$metadata
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


class IpeaDataCollector(BaseCollector):
    """Coletor genérico para uma série IPEADATA via OData v4.

    Args:
        series_code: código da série (SERCODIGO), ex.: 'ANALF15M'.
        api_base: override do endpoint OData (default: settings.ipea_odata_api_base).
        territorial_level: filtro opcional sobre NIVNOME ('Brasil', 'Estados',
            'Municípios', 'Regiões'). Se None, retorna todos os níveis.
        http_client: injeção opcional para testes.
    """

    source: ClassVar[str] = "ipea"

    def __init__(
        self,
        series_code: str,
        *,
        api_base: str | None = None,
        territorial_level: str | None = None,
        http_client: httpx.Client | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if not series_code:
            raise ValueError("series_code não pode ser vazio")
        self.series_code = series_code
        self.api_base = (api_base or settings.ipea_odata_api_base).rstrip("/")
        self.territorial_level = territorial_level
        self._http_client = http_client
        # Ex.: 'ANALF15M' → 'serie_analf15m'
        self.dataset = f"serie_{series_code.lower()}"

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------
    def build_url(self, period: str | int | None = None) -> str:
        """Monta URL OData para a série, com filtro opcional de período.

        `period` aceita:
          - None ou 'all' → sem filtro
          - "2023"        → year(VALDATA) eq 2023
          - "2010-2023"   → year(VALDATA) ge 2010 and year(VALDATA) le 2023
        """
        path = f"/Metadados('{self.series_code}')/Valores"
        filters = self._build_filters(period)
        if not filters:
            return f"{self.api_base}{path}"
        return f"{self.api_base}{path}?{urlencode({'$filter': ' and '.join(filters)})}"

    def _build_filters(self, period: str | int | None) -> list[str]:
        filters: list[str] = []
        period_filter = self._period_filter(period)
        if period_filter:
            filters.append(period_filter)
        if self.territorial_level:
            # Strings em OData são delimitadas por aspas simples; '' duplica para escape.
            value = self.territorial_level.replace("'", "''")
            filters.append(f"NIVNOME eq '{value}'")
        return filters

    @staticmethod
    def _period_filter(period: str | int | None) -> str | None:
        if period is None:
            return None
        text = str(period).strip()
        if not text or text.lower() == "all":
            return None
        if "-" in text:
            start, end = text.split("-", 1)
            start_int = int(start)
            end_int = int(end)
            return f"year(VALDATA) ge {start_int} and year(VALDATA) le {end_int}"
        year = int(text)
        return f"year(VALDATA) eq {year}"

    # ------------------------------------------------------------------
    # Fetch (com paginação OData @odata.nextLink)
    # ------------------------------------------------------------------
    def fetch(
        self,
        *,
        reference_period: str | int,
        **kwargs: Any,
    ) -> tuple[pd.DataFrame, str]:
        first_url = self.build_url(reference_period)
        client = self._http_client or httpx.Client(timeout=settings.http_timeout_seconds)
        try:
            records = self._fetch_paginated(client, first_url)
        finally:
            if self._http_client is None:
                client.close()

        df = self._records_to_dataframe(records)
        log.info(
            "ipea.fetch.parsed",
            url=first_url,
            series=self.series_code,
            rows=len(df),
            columns=len(df.columns),
        )
        return df, first_url

    def _fetch_paginated(
        self,
        client: httpx.Client,
        first_url: str,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        url: str | None = first_url
        page = 0
        while url:
            page += 1
            log.info("ipea.fetch", url=url, series=self.series_code, page=page)
            response = client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()

            value = payload.get("value")
            if not isinstance(value, list):
                raise ValueError(
                    f"IPEADATA OData: payload sem campo 'value' lista (URL: {url}, "
                    f"payload={payload!r})"
                )
            records.extend(value)

            next_link = payload.get("@odata.nextLink")
            url = next_link if isinstance(next_link, str) and next_link else None
            if page > 200:  # safety cap (séries longas raramente passam disso)
                log.warning(
                    "ipea.pagination.cap_hit", series=self.series_code, pages=page
                )
                break
        return records

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    @staticmethod
    def _records_to_dataframe(records: list[dict[str, Any]]) -> pd.DataFrame:
        """Normaliza colunas dos valores OData IPEADATA.

        Mantém os nomes originais SERCODIGO/VALDATA/VALVALOR/NIVNOME/TERCODIGO
        (Bronze preserva fidelidade da fonte) e garante tipagem mínima:
        VALDATA como datetime UTC (timezone-naive em UTC), VALVALOR como float.
        """
        if not records:
            return pd.DataFrame(
                columns=["SERCODIGO", "VALDATA", "VALVALOR", "NIVNOME", "TERCODIGO"]
            )
        df = pd.DataFrame(records)
        for col in ("SERCODIGO", "VALDATA", "VALVALOR", "NIVNOME", "TERCODIGO"):
            if col not in df.columns:
                df[col] = pd.NA
        if "VALDATA" in df.columns:
            df["VALDATA"] = pd.to_datetime(df["VALDATA"], utc=True, errors="coerce")
        if "VALVALOR" in df.columns:
            df["VALVALOR"] = pd.to_numeric(df["VALVALOR"], errors="coerce")
        ordered = ["SERCODIGO", "VALDATA", "VALVALOR", "NIVNOME", "TERCODIGO"]
        remaining = [c for c in df.columns if c not in ordered]
        return df[ordered + remaining]


# ----------------------------------------------------------------------
# Conveniências para séries-chave de educação
# ----------------------------------------------------------------------
def make_analfabetismo_15m_collector(**kwargs: Any) -> IpeaDataCollector:
    """ANALF15M — Taxa de analfabetismo, 15 anos ou mais (PNAD/Censo)."""
    return IpeaDataCollector(series_code="ANALF15M", **kwargs)


def make_ideb_br_series_iniciais_collector(**kwargs: Any) -> IpeaDataCollector:
    """IDEB_BR_SAI — IDEB Brasil, anos iniciais do ensino fundamental."""
    return IpeaDataCollector(series_code="IDEB_BR_SAI", **kwargs)
