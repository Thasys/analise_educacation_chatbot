"""Coletor IBGE SIDRA — tabelas de educação da PNAD Contínua.

A API SIDRA expõe agregados estatísticos do IBGE em REST puro. A URL é
construída como caminho posicional:

    /values/t/{tabela}/{nivel_territorial}/{codigos}/v/{variaveis}/p/{periodos}[/{classificacoes}]

A resposta JSON é uma lista onde a primeira posição é uma "linha-cabeçalho"
com rótulos descritivos (ex.: "Valor", "Unidade da Federação") associados às
mesmas chaves curtas (V, D1N, D1C…) presentes nas linhas de dados subsequentes.

Tabela default deste coletor: **7136** — Taxa de analfabetismo das pessoas de
15 anos ou mais de idade (PNAD Contínua, módulo Educação anual).

Doc oficial: https://apisidra.ibge.gov.br/
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
import pandas as pd

from src.collectors.base import BaseCollector
from src.config import settings
from src.logging_config import get_logger

log = get_logger(__name__)


class SidraEducacaoCollector(BaseCollector):
    """Coletor genérico para tabelas SIDRA de educação.

    Args:
        table_id: número da tabela SIDRA (ex.: 7136).
        territorial_level: nível territorial — 'n1' (Brasil), 'n3' (UF),
            'n6' (município), etc.
        territorial_codes: 'all' ou lista separada por vírgulas (ex.: '11,12').
        variables: 'all' ou códigos separados por vírgulas.
        classifications: trecho opcional após o período (ex.: 'c2/4,5'),
            para aplicar filtros de classificação.
        api_base: override do endpoint (default: settings.ibge_sidra_api_base).
    """

    source: ClassVar[str] = "ibge"

    def __init__(
        self,
        table_id: int,
        *,
        territorial_level: str = "n1",
        territorial_codes: str = "all",
        variables: str = "all",
        classifications: str | None = None,
        api_base: str | None = None,
        http_client: httpx.Client | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.table_id = int(table_id)
        self.territorial_level = territorial_level
        self.territorial_codes = territorial_codes
        self.variables = variables
        self.classifications = classifications
        self.api_base = (api_base or settings.ibge_sidra_api_base).rstrip("/")
        self._http_client = http_client
        self.dataset = f"sidra_{self.table_id}"

    # ------------------------------------------------------------------
    # URL building
    # ------------------------------------------------------------------
    def build_url(self, period: str | int) -> str:
        path = (
            f"/values/t/{self.table_id}"
            f"/{self.territorial_level}/{self.territorial_codes}"
            f"/v/{self.variables}"
            f"/p/{period}"
        )
        if self.classifications:
            path += f"/{self.classifications.lstrip('/')}"
        return f"{self.api_base}{path}"

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
        log.info("sidra.fetch", url=url, table=self.table_id, period=str(reference_period))

        client = self._http_client or httpx.Client(timeout=settings.http_timeout_seconds)
        try:
            response = client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            payload = response.json()
        finally:
            if self._http_client is None:
                client.close()

        df = self._parse_payload(payload)
        log.info(
            "sidra.fetch.parsed",
            url=url,
            rows=len(df),
            columns=len(df.columns),
        )
        return df, url

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_payload(payload: list[dict[str, Any]]) -> pd.DataFrame:
        """Transforma o JSON SIDRA em DataFrame com nomes legíveis.

        Estratégia: payload[0] mapeia chaves curtas (V, D1N, NN, ...) para
        rótulos descritivos. Linhas restantes carregam os dados. Renomeamos
        as colunas pelos rótulos do header — essa é a forma "Bronze" canônica
        (preserva a fidelidade da fonte com nomes interpretáveis).
        """
        if not payload:
            return pd.DataFrame()
        if len(payload) == 1:
            # Apenas o header — sem linhas de dados.
            return pd.DataFrame(columns=list(payload[0].values()))

        header, *rows = payload
        df = pd.DataFrame(rows)
        rename_map = {col: header[col] for col in df.columns if col in header}
        df = df.rename(columns=rename_map)
        return df


# Conveniência: instâncias pré-configuradas para tabelas-chave do PNAD Contínua
# Educação. Importar diretamente em flows é mais explícito que strings mágicas.
def make_pnad_continua_t7136(**kwargs: Any) -> SidraEducacaoCollector:
    """Tabela 7136 — Taxa de analfabetismo (PNAD Contínua Educação anual)."""
    return SidraEducacaoCollector(table_id=7136, **kwargs)
