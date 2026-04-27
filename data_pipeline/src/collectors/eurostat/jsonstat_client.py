"""Coletor Eurostat — Statistics API v1.0 em JSON-stat 2.0.

Endpoint REST oficial:

    GET {base}/data/{dataset_code}?{dim1}={code}&{dim2}={code}&...

Exemplos de filtros:
    geo=BE&geo=DE          (lista de países — múltiplos pares chave=valor)
    time=2020&time=2021    (anos)
    sinceTimePeriod=2010   (range — start)
    untilTimePeriod=2023   (range — end)

JSON-stat 2.0 (resumido):

    {
      "version": "2.0",
      "class": "dataset",
      "label": "...",
      "source": "Eurostat",
      "id": ["freq","unit","isced11","sex","age","geo","time"],
      "size": [1, 1, 8, 3, 1, 3, 4],
      "dimension": {
        "<dim_id>": {
          "label": "...",
          "category": {
            "index": {"<code>": 0, "<code>": 1, ...},
            "label": {"<code>": "human label", ...}
          }
        }, ...
      },
      "value": [10.5, 11.2, ...] | {"0": 10.5, "5": 13.4}
      "status": {"0": "p", "1": "e"}    // opcional
    }

`value` pode vir como array denso (`null` para missing) ou dicionário esparso
mapeando o índice linear → valor.

A coordenada multidimensional `(c0, c1, …, ck)` mapeia ao índice linear via
*row-major* (estilo C): `i = c0 * (s1*s2*…*sk) + c1 * (s2*…*sk) + … + ck`.

Doc: https://ec.europa.eu/eurostat/online-help/api
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
import pandas as pd

from src.collectors.base import BaseCollector
from src.config import settings
from src.logging_config import get_logger

log = get_logger(__name__)


class EurostatCollector(BaseCollector):
    """Coletor de um dataset Eurostat via JSON-stat 2.0.

    Args:
        dataset_code: código do dataset (ex.: 'educ_uoe_enrt01').
        filters: dicionário {dimensao: valor | lista}. Cada par vira
            `?dim=valor` na URL; listas viram múltiplos pares (`?geo=BE&geo=DE`).
        api_base: override do endpoint (default: settings.eurostat_api_base).
        http_client: injeção opcional para testes.
    """

    source: ClassVar[str] = "eurostat"

    def __init__(
        self,
        dataset_code: str,
        *,
        filters: dict[str, Any] | None = None,
        api_base: str | None = None,
        http_client: httpx.Client | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if not dataset_code:
            raise ValueError("dataset_code não pode ser vazio")
        self.dataset_code = dataset_code
        self.filters = dict(filters or {})
        self.api_base = (api_base or settings.eurostat_api_base).rstrip("/")
        self._http_client = http_client
        self.dataset = f"dataset_{dataset_code.lower()}"

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------
    def build_url(self, period: str | int | None = None) -> str:
        """Monta URL com filtros + período opcional via since/untilTimePeriod.

        `period` aceita None / 'all' / ano único / 'AAAA-AAAA'.
        Período sempre tem prioridade sobre `time` em `filters`.
        """
        path = f"/data/{self.dataset_code}"
        params: list[tuple[str, str]] = []
        for dim, value in self.filters.items():
            if dim == "time" and period is not None:
                continue  # período é controlado pelo argumento
            for v in self._as_list(value):
                params.append((dim, str(v)))
        for key, val in self._period_params(period):
            params.append((key, str(val)))
        if not params:
            return f"{self.api_base}{path}"
        # urlencode com sequência de pares preserva múltiplas ocorrências.
        from urllib.parse import urlencode

        return f"{self.api_base}{path}?{urlencode(params)}"

    @staticmethod
    def _as_list(value: Any) -> list[Any]:
        if isinstance(value, (list, tuple, set)):
            return list(value)
        return [value]

    @staticmethod
    def _period_params(period: str | int | None) -> list[tuple[str, int]]:
        if period is None:
            return []
        text = str(period).strip()
        if not text or text.lower() == "all":
            return []
        if "-" in text:
            start, end = text.split("-", 1)
            return [
                ("sinceTimePeriod", int(start)),
                ("untilTimePeriod", int(end)),
            ]
        year = int(text)
        return [("time", year)]

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
            log.info("eurostat.fetch", url=url, dataset=self.dataset_code)
            response = client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
        finally:
            if self._http_client is None:
                client.close()

        df = self.parse_jsonstat(payload)
        log.info(
            "eurostat.fetch.parsed",
            url=url,
            dataset=self.dataset_code,
            rows=len(df),
            columns=len(df.columns),
        )
        return df, url

    # ------------------------------------------------------------------
    # JSON-stat 2.0 parsing
    # ------------------------------------------------------------------
    @staticmethod
    def parse_jsonstat(payload: dict[str, Any]) -> pd.DataFrame:
        """Achata cube JSON-stat 2.0 em DataFrame longo.

        Saída: uma linha por célula populada do cube, com colunas iguais aos
        ids das dimensões + OBS_VALUE (numérico). Quando `status` está
        presente, vira a coluna `OBS_STATUS`.
        Células nulas (`value[i] is None`) são puladas.
        """
        ids: list[str] = list(payload.get("id") or [])
        size: list[int] = list(payload.get("size") or [])
        dimension = payload.get("dimension") or {}
        value = payload.get("value")
        status = payload.get("status")

        if not ids or not size or value is None:
            return pd.DataFrame(columns=(ids or []) + ["OBS_VALUE"])

        # Para cada dimensão, lista de codes ordenados pelo `index`.
        codes_per_dim: list[list[str]] = []
        for dim_id in ids:
            spec = dimension.get(dim_id) or {}
            category = spec.get("category") or {}
            index = category.get("index") or {}
            if isinstance(index, dict):
                ordered = sorted(index.items(), key=lambda kv: int(kv[1]))
                codes = [code for code, _ in ordered]
            elif isinstance(index, list):
                codes = list(index)
            else:
                codes = []
            codes_per_dim.append(codes)

        # Strides row-major para decompor índice linear em coordenadas.
        strides: list[int] = [1] * len(size)
        for i in range(len(size) - 2, -1, -1):
            strides[i] = strides[i + 1] * size[i + 1]
        total = strides[0] * size[0] if size else 0

        def decode(idx: int) -> dict[str, Any]:
            cell: dict[str, Any] = {}
            for dim_pos, dim_id in enumerate(ids):
                coord = (idx // strides[dim_pos]) % size[dim_pos]
                codes = codes_per_dim[dim_pos]
                cell[dim_id] = codes[coord] if coord < len(codes) else None
            return cell

        rows: list[dict[str, Any]] = []
        if isinstance(value, dict):
            iterator = (
                (int(k), v) for k, v in value.items() if v is not None
            )
        elif isinstance(value, list):
            iterator = (
                (i, v) for i, v in enumerate(value) if v is not None
            )
        else:
            iterator = iter(())

        for i, val in iterator:
            row = decode(i)
            row["OBS_VALUE"] = val
            if isinstance(status, dict) and str(i) in status:
                row["OBS_STATUS"] = status[str(i)]
            elif isinstance(status, list) and i < len(status):
                row["OBS_STATUS"] = status[i]
            rows.append(row)

        if not rows:
            cols = ids + ["OBS_VALUE"]
            return pd.DataFrame(columns=cols)

        df = pd.DataFrame(rows)
        if "OBS_VALUE" in df.columns:
            df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
        # Bloqueio de borda: se o payload tem status mas zero células válidas,
        # ainda garantimos a coluna para schema previsível.
        if status is not None and "OBS_STATUS" not in df.columns:
            df["OBS_STATUS"] = pd.NA
        # Ordena colunas: dimensões na ordem do `id`, depois value e status.
        ordered = [c for c in ids if c in df.columns] + [
            c for c in ["OBS_VALUE", "OBS_STATUS"] if c in df.columns
        ]
        remaining = [c for c in df.columns if c not in ordered]
        return df[ordered + remaining]


# ----------------------------------------------------------------------
# Conveniências para datasets-chave de educação
# ----------------------------------------------------------------------
def make_enrolment_collector(**kwargs: Any) -> EurostatCollector:
    """educ_uoe_enrt01 — alunos matriculados por nível ISCED."""
    return EurostatCollector(dataset_code="educ_uoe_enrt01", **kwargs)


def make_education_expenditure_collector(**kwargs: Any) -> EurostatCollector:
    """educ_uoe_fine01 — despesa em educação por fonte e categoria."""
    return EurostatCollector(dataset_code="educ_uoe_fine01", **kwargs)


def make_early_school_leavers_collector(**kwargs: Any) -> EurostatCollector:
    """edat_lfse_14 — abandono escolar precoce (% 18-24 anos)."""
    return EurostatCollector(dataset_code="edat_lfse_14", **kwargs)
