"""Coletor CEPALSTAT — API REST de indicadores LATAM (CEPAL/ECLAC).

A CEPALSTAT migrou em 2025 para o host `api-cepalstat.cepal.org` com uma
API REST nova. O endpoint principal de dados:

    GET {base}/indicator/{id}/data?format=json

A resposta vem com IDs internos de dimensoes em vez de labels resolvidos:

    {
      "header": {...},
      "body": {
        "metadata": {"indicator_id": ..., "indicator_name": ...},
        "data": [
          {"value": "97.29", "iso3": "BRA",
           "dim_208": 222,        # Country (resolvivel mas redundante com iso3)
           "dim_144": 146,        # Sex (146=Both, 265=Men, 266=Women)
           "dim_29117": 68233},   # Year (68109=1900, 68110=1901, ...)
          ...
        ]
      }
    }

Para resolver os dim_* IDs em labels (especialmente o ano), o coletor
faz uma segunda chamada ao endpoint de dimensoes:

    GET {base}/indicator/{id}/dimensions?format=json

E constroi um mapa `dim_<id> -> {member_id: label}` aplicado ao
DataFrame final.

Doc: https://api-cepalstat.cepal.org/apidocs
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
    """Coletor de um indicador CEPALSTAT (REST v1).

    Args:
        indicator_id: ID numerico do indicador (ex.: '2236').
        countries: lista/iteravel de codigos ISO-3 (ex.: ['BRA', 'CHL']) ou
            string separada por '+' / ','. None = todos os paises.
            (Nota: a API v1 atual nao filtra por pais via querystring; o
            filtro acontece em pos-processamento se countries informado.)
        api_base: override do endpoint (default settings.cepalstat_api_base).
        http_client: injecao opcional para testes.
    """

    source: ClassVar[str] = "cepalstat"

    # Schema canonico apos resolucao de dim IDs.
    DATA_FIELDS: ClassVar[tuple[str, ...]] = (
        "indicator_id",
        "indicator_name",
        "country_iso3",
        "year",
        "value",
        "sex",
        "source_id",
        "notes_ids",
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
            raise ValueError("indicator_id nao pode ser vazio")
        self.indicator_id = str(indicator_id)
        self.countries = self._normalise_countries(countries)
        self.api_base = (api_base or settings.cepalstat_api_base).rstrip("/")
        self._http_client = http_client
        self.dataset = f"indicator_{self.indicator_id.lower()}"

    @staticmethod
    def _normalise_countries(
        countries: str | list[str] | tuple[str, ...] | None,
    ) -> list[str] | None:
        if countries is None:
            return None
        if isinstance(countries, (list, tuple, set)):
            return [str(c).upper() for c in countries]
        text = str(countries).strip()
        if not text:
            return None
        sep = "," if "," in text else "+"
        return [c.strip().upper() for c in text.split(sep) if c.strip()]

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------
    def build_url(self, period: str | int | None = None) -> str:
        """URL para o endpoint de dados (period filtra em pos-processamento)."""
        params: list[tuple[str, str]] = [("format", "json")]
        return f"{self.api_base}/indicator/{self.indicator_id}/data?{urlencode(params)}"

    def build_dimensions_url(self) -> str:
        """URL para o endpoint de dimensoes (resolve dim_* IDs para labels)."""
        return (
            f"{self.api_base}/indicator/{self.indicator_id}/dimensions?"
            + urlencode([("format", "json"), ("lang", "en")])
        )

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
        client = self._http_client or httpx.Client(timeout=settings.http_timeout_seconds)
        try:
            data_url = self.build_url(reference_period)
            dims_url = self.build_dimensions_url()
            log.info("cepalstat.fetch", url=data_url, indicator=self.indicator_id)

            data_resp = client.get(data_url, headers={"Accept": "application/json"})
            data_resp.raise_for_status()
            data_payload = data_resp.json()

            dims_resp = client.get(dims_url, headers={"Accept": "application/json"})
            dims_resp.raise_for_status()
            dims_payload = dims_resp.json()
        finally:
            if self._http_client is None:
                client.close()

        df = self._parse_payload(
            data_payload,
            dims_payload,
            reference_period=reference_period,
            countries=self.countries,
        )
        log.info(
            "cepalstat.fetch.parsed",
            url=data_url,
            indicator=self.indicator_id,
            rows=len(df),
            columns=len(df.columns),
        )
        return df, data_url

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    @classmethod
    def _build_dim_lookup(
        cls, dims_payload: dict[str, Any]
    ) -> tuple[dict[int, dict[int, str]], dict[int, str]]:
        """Constroi (lookup_member_label_per_dim, dim_id_to_purpose).

        purpose: classifica a dimensao por nome em 'year' / 'sex' / 'country'
        / 'other' para mapear para colunas canonicas do schema.
        """
        body = dims_payload.get("body") if isinstance(dims_payload, dict) else None
        dimensions = (body or {}).get("dimensions") or []
        member_labels: dict[int, dict[int, str]] = {}
        purpose: dict[int, str] = {}
        for dim in dimensions:
            try:
                dim_id = int(dim.get("id"))
            except (TypeError, ValueError):
                continue
            name = str(dim.get("name", "")).lower()
            if "year" in name:
                purpose[dim_id] = "year"
            elif "sex" in name or "gender" in name:
                purpose[dim_id] = "sex"
            elif "country" in name or "area" in name or "region" in name:
                purpose[dim_id] = "country"
            else:
                purpose[dim_id] = "other"
            members: dict[int, str] = {}
            for m in dim.get("members") or []:
                try:
                    mid = int(m.get("id"))
                except (TypeError, ValueError):
                    continue
                members[mid] = str(m.get("name", ""))
            member_labels[dim_id] = members
        return member_labels, purpose

    @classmethod
    def _parse_payload(
        cls,
        data_payload: dict[str, Any],
        dims_payload: dict[str, Any] | None = None,
        *,
        reference_period: str | int | None = None,
        countries: list[str] | None = None,
    ) -> pd.DataFrame:
        """Achata payload + resolve dim_* IDs em colunas canonicas."""
        body = data_payload.get("body") if isinstance(data_payload, dict) else None
        # Compatibilidade com formato legado (data no top-level).
        if not body:
            records = (data_payload.get("data") if isinstance(data_payload, dict) else None) or []
            metadata: dict[str, Any] = {}
        else:
            records = body.get("data") or []
            metadata = body.get("metadata") or {}

        if not isinstance(records, list):
            raise ValueError(
                f"CEPALSTAT: campo 'data' deveria ser lista; recebido: {type(records).__name__}"
            )
        if not records:
            return pd.DataFrame(columns=list(cls.DATA_FIELDS))

        df = pd.DataFrame(records)

        # Resolve dim_* via lookup.
        member_labels: dict[int, dict[int, str]] = {}
        purpose: dict[int, str] = {}
        if dims_payload:
            member_labels, purpose = cls._build_dim_lookup(dims_payload)

        # Aplica labels e mapeia dimensoes-chave para colunas canonicas.
        for col in list(df.columns):
            if not col.startswith("dim_"):
                continue
            try:
                dim_id = int(col[len("dim_"):])
            except ValueError:
                continue
            labels = member_labels.get(dim_id, {})
            if not labels:
                continue
            resolved = df[col].map(lambda v, _labels=labels: _labels.get(int(v)) if pd.notna(v) else None)
            role = purpose.get(dim_id, "other")
            if role == "year":
                df["year"] = pd.to_numeric(resolved, errors="coerce").astype("Int64")
            elif role == "sex":
                df["sex"] = resolved
            elif role == "country":
                # ISO3 ja vem na coluna `iso3`; o label do nome do pais e
                # complementar.
                df["country_name"] = resolved
            else:
                # Preserva como `dim_<id>_label` para auditoria.
                df[f"dim_{dim_id}_label"] = resolved

        # Mapeia coluna `iso3` (vinda do payload) para `country_iso3` canonico.
        if "iso3" in df.columns:
            df["country_iso3"] = df["iso3"].astype("string").str.upper()
        else:
            df["country_iso3"] = pd.NA

        # Tipagem do `value`.
        if "value" in df.columns:
            df["value"] = pd.to_numeric(df["value"], errors="coerce")

        # Anota indicator_id e indicator_name a partir do metadata (uniforme).
        df["indicator_id"] = str(metadata.get("indicator_id", "") or "")
        df["indicator_name"] = str(metadata.get("indicator_name", "") or "")

        # Filtros pos-processamento.
        if "year" in df.columns and reference_period is not None:
            start, end = cls._period_bounds(reference_period)
            if start is not None:
                df = df[df["year"] >= start]
            if end is not None:
                df = df[df["year"] <= end]
        if countries and "country_iso3" in df.columns:
            df = df[df["country_iso3"].isin(countries)]

        # Garante colunas canonicas mesmo se ausentes.
        for field in cls.DATA_FIELDS:
            if field not in df.columns:
                df[field] = pd.NA

        ordered = list(cls.DATA_FIELDS)
        remaining = [c for c in df.columns if c not in ordered]
        return df[ordered + remaining].reset_index(drop=True)


# ----------------------------------------------------------------------
# Conveniencias para indicadores-chave de educacao na CEPALSTAT
# ----------------------------------------------------------------------
def make_analfabetismo_15m_collector(**kwargs: Any) -> CepalstatCollector:
    """Indicador 53 — Illiteracy rate by sex, age group and area (LATAM)."""
    return CepalstatCollector(indicator_id="53", **kwargs)


def make_alfabetizacao_15m_collector(**kwargs: Any) -> CepalstatCollector:
    """Indicador 2236 — Literacy rate of population aged 15+, by sex (LATAM)."""
    return CepalstatCollector(indicator_id="2236", **kwargs)


def make_gasto_publico_educacao_collector(**kwargs: Any) -> CepalstatCollector:
    """Indicador 460 — Public expenditure on education (LATAM)."""
    return CepalstatCollector(indicator_id="460", **kwargs)
