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
    # SDMX-JSON 2.0 parsing
    # ------------------------------------------------------------------
    @staticmethod
    def parse_sdmx_json(payload: dict[str, Any]) -> pd.DataFrame:
        """Achata um payload SDMX-JSON 2.0 em DataFrame longo.

        Estrutura esperada:
            payload["data"]["structures"][0]["dimensions"]["series"]
                                              ["observation"]
                                            ["attributes"]["observation"]
            payload["data"]["dataSets"][0]["series"]
                                          [<series_key>]["observations"]

        Cada série gera uma linha por observação. Atributos da observação são
        anexados como colunas extras (`<attr_id>`).
        """
        data = payload.get("data") or payload  # tolera payloads sem "data" wrapper
        structures = data.get("structures") or []
        datasets = data.get("dataSets") or []
        if not structures or not datasets:
            return pd.DataFrame(columns=["TIME_PERIOD", "OBS_VALUE"])

        structure = structures[0]
        series_dims = structure.get("dimensions", {}).get("series", []) or []
        obs_dims = structure.get("dimensions", {}).get("observation", []) or []
        obs_attrs = structure.get("attributes", {}).get("observation", []) or []

        series_dim_ids = [d.get("id", f"DIM_{i}") for i, d in enumerate(series_dims)]
        obs_dim_ids = [d.get("id", f"OBS_{i}") for i, d in enumerate(obs_dims)]
        obs_attr_ids = [a.get("id", f"ATTR_{i}") for i, a in enumerate(obs_attrs)]

        series_value_lookups = [
            [v.get("id") for v in (d.get("values") or [])] for d in series_dims
        ]
        obs_value_lookups = [
            [v.get("id") for v in (d.get("values") or [])] for d in obs_dims
        ]
        obs_attr_lookups = [
            [v.get("id") for v in (a.get("values") or [])] for a in obs_attrs
        ]

        rows: list[dict[str, Any]] = []
        series_map = datasets[0].get("series") or {}
        for series_key, series_payload in series_map.items():
            series_indices = [int(x) for x in str(series_key).split(":") if x != ""]
            series_values = {
                series_dim_ids[i]: series_value_lookups[i][idx]
                if i < len(series_value_lookups) and idx < len(series_value_lookups[i])
                else None
                for i, idx in enumerate(series_indices)
            }
            observations = series_payload.get("observations") or {}
            for obs_key, obs_payload in observations.items():
                obs_indices = [int(x) for x in str(obs_key).split(":") if x != ""]
                obs_values = {
                    obs_dim_ids[i]: obs_value_lookups[i][idx]
                    if i < len(obs_value_lookups) and idx < len(obs_value_lookups[i])
                    else None
                    for i, idx in enumerate(obs_indices)
                }

                value = obs_payload[0] if obs_payload else None
                attr_values: dict[str, Any] = {}
                for i, attr_id in enumerate(obs_attr_ids):
                    raw_idx = obs_payload[i + 1] if i + 1 < len(obs_payload) else None
                    if raw_idx is None or raw_idx == "":
                        attr_values[attr_id] = None
                    else:
                        try:
                            idx = int(raw_idx)
                            lookup = obs_attr_lookups[i] if i < len(obs_attr_lookups) else []
                            attr_values[attr_id] = lookup[idx] if idx < len(lookup) else None
                        except (TypeError, ValueError):
                            attr_values[attr_id] = raw_idx

                rows.append(
                    {**series_values, **obs_values, "OBS_VALUE": value, **attr_values}
                )

        if not rows:
            cols = series_dim_ids + obs_dim_ids + ["OBS_VALUE"] + obs_attr_ids
            return pd.DataFrame(columns=cols or ["TIME_PERIOD", "OBS_VALUE"])

        df = pd.DataFrame(rows)
        # Tipagem mínima: OBS_VALUE numérico, TIME_PERIOD como string (preserva
        # codificações 2020-Q1, 2020-S1, 2020 etc.).
        if "OBS_VALUE" in df.columns:
            df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
        return df


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
