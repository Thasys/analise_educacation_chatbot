"""Coletor Censo Escolar (microdados anuais — INEP).

Pacote ZIP em https://download.inep.gov.br/microdados/microdados_censo_escolar_<YEAR>.zip
contém vários CSVs (matrícula, escola, docente, turma) + dicionários.

Este coletor baixa o ZIP e extrai um CSV específico (default: arquivo de
matrícula por escola/aluno) para Bronze.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any, ClassVar

import pandas as pd

from src.collectors.inep.inep_base import InepBulkCollector
from src.logging_config import get_logger

log = get_logger(__name__)


class CensoEscolarCollector(InepBulkCollector):
    """Coletor de uma tabela específica do Censo Escolar.

    Args:
        member_pattern: substring a procurar nos nomes dos membros do ZIP
            (case-insensitive). Default 'matricula' busca o CSV principal.
        csv_kwargs: kwargs extras para `pd.read_csv` (encoding, sep, etc.).
        url_template: override do padrão `microdados_censo_escolar_<year>.zip`.
    """

    URL_TEMPLATE: ClassVar[str] = (
        "https://download.inep.gov.br/microdados/microdados_censo_escolar_{year}.zip"
    )
    dataset: ClassVar[str] = "censo_escolar"
    DEFAULT_CSV_KWARGS: ClassVar[dict[str, Any]] = {
        "sep": ";",
        "encoding": "latin-1",
        "low_memory": False,
    }

    def __init__(
        self,
        *,
        member_pattern: str = "matricula",
        csv_kwargs: dict[str, Any] | None = None,
        url_template: str | None = None,
        **kwargs: Any,
    ) -> None:
        if url_template:
            # Hack para sobrescrever o ClassVar ao nível da instância.
            self.URL_TEMPLATE = url_template  # type: ignore[misc]
        self.member_pattern = member_pattern
        self.csv_kwargs = {**self.DEFAULT_CSV_KWARGS, **(csv_kwargs or {})}
        super().__init__(**kwargs)

    def _load_dataframe(self, local_path: Path) -> pd.DataFrame:
        target = self._select_member(local_path, self.member_pattern)
        log.info("censo_escolar.member_selected", zip=str(local_path), member=target)
        with zipfile.ZipFile(local_path) as zf:
            with zf.open(target) as fh:
                return pd.read_csv(fh, **self.csv_kwargs)

    @staticmethod
    def _select_member(zip_path: Path, pattern: str) -> str:
        with zipfile.ZipFile(zip_path) as zf:
            members = [
                m
                for m in zf.namelist()
                if not m.endswith("/")
                and pattern.lower() in m.lower()
                and m.lower().endswith(".csv")
            ]
        if not members:
            raise FileNotFoundError(
                f"Nenhum CSV correspondente ao padrão {pattern!r} dentro de {zip_path}"
            )
        # Maior arquivo é a tabela principal (heurística estável para microdados INEP).
        with zipfile.ZipFile(zip_path) as zf:
            members.sort(key=lambda m: zf.getinfo(m).file_size, reverse=True)
        return members[0]


class SaebCollector(CensoEscolarCollector):
    """Coletor do SAEB (microdados bienais)."""

    URL_TEMPLATE: ClassVar[str] = (
        "https://download.inep.gov.br/microdados/microdados_saeb_{year}.zip"
    )
    dataset: ClassVar[str] = "saeb"


class EnemCollector(CensoEscolarCollector):
    """Coletor do ENEM (microdados anuais)."""

    URL_TEMPLATE: ClassVar[str] = (
        "https://download.inep.gov.br/microdados/microdados_enem_{year}.zip"
    )
    dataset: ClassVar[str] = "enem"
