"""Coletor IDEB (Índice de Desenvolvimento da Educação Básica).

O IDEB é divulgado bienalmente pelo INEP em planilhas XLSX. URL típica:

    https://download.inep.gov.br/educacao_basica/portal_ideb/planilhas_para_download/
        {year}/divulgacao_anos_iniciais_municipios_{year}.xlsx

Cada planilha tem múltiplas abas; a aba relevante depende do recorte
(anos iniciais, finais, médio) e granularidade (Brasil, UF, município, escola).

Este coletor é parametrizado pela URL completa (a estrutura de nome muda a cada
ciclo) e pelo nome da aba a ler.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import pandas as pd

from src.collectors.inep.inep_base import InepBulkCollector


class IdebCollector(InepBulkCollector):
    """Coletor genérico para uma planilha XLSX do IDEB.

    Args:
        url: URL completa do XLSX (override de URL_TEMPLATE — default é vazio
            porque os nomes mudam por ciclo).
        sheet_name: nome ou índice da aba; default = 0 (primeira aba).
        skiprows: linhas a pular no topo (default 0). Planilhas IDEB costumam
            ter cabeçalho descritivo a ser pulado; ajustar conforme arquivo.
    """

    URL_TEMPLATE: ClassVar[str] = "{url}"  # placeholder; resolvido via __init__
    dataset: ClassVar[str] = "ideb"

    def __init__(
        self,
        *,
        url: str,
        sheet_name: str | int = 0,
        skiprows: int = 0,
        period_label: str | None = None,
        **kwargs: Any,
    ) -> None:
        if not url:
            raise ValueError("IdebCollector.url é obrigatório")
        # Substitui o placeholder antes da validação da base.
        self._explicit_url = url
        self.sheet_name = sheet_name
        self.skiprows = int(skiprows)
        self._period_label = period_label
        super().__init__(**kwargs)
        # `URL_TEMPLATE` herdado é apenas placeholder; sobrescrevemos build_url.

    def build_url(self, reference_period: str | int) -> str:
        return self._explicit_url

    def _load_dataframe(self, local_path: Path) -> pd.DataFrame:
        return pd.read_excel(
            local_path, sheet_name=self.sheet_name, skiprows=self.skiprows
        )
