"""Classe base para coletores INEP que dependem de bulk download.

Diferente das fontes REST (IBGE SIDRA, World Bank, IPEADATA, …), o INEP
não expõe API: distribui microdados em pacotes ZIP/Excel a cada divulgação
oficial. Este módulo padroniza o pipeline:

    1. Resolver a URL do arquivo para o ano de referência.
    2. Baixar (com cache) via `BulkDownloader`.
    3. Extrair → DataFrame via `_load_dataframe()` (subclasse).
    4. `BaseCollector.collect()` cuida do resto (Bronze + audit log).

Cada subclasse define `URL_TEMPLATE` (string `.format(year=...)`) e o método
`_load_dataframe(local_path)`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import pandas as pd

from src.collectors.base import BaseCollector
from src.config import settings
from src.logging_config import get_logger
from src.utils.bulk_downloader import BulkDownloader

log = get_logger(__name__)


class InepBulkCollector(BaseCollector):
    """Base para coletores INEP que baixam um arquivo por ano de referência.

    Subclasse precisa definir:
        URL_TEMPLATE: ClassVar[str]    # formatado com {year}
        dataset:      ClassVar[str]    # ex.: 'censo_escolar', 'ideb'
        _load_dataframe(local_path: Path) -> pd.DataFrame
    """

    source: ClassVar[str] = "inep"
    URL_TEMPLATE: ClassVar[str] = ""

    def __init__(
        self,
        *,
        cache_root: Path | str | None = None,
        downloader: BulkDownloader | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if not getattr(self, "URL_TEMPLATE", ""):
            raise ValueError(
                f"{type(self).__name__}.URL_TEMPLATE precisa ser definido."
            )
        cache_path = Path(cache_root) if cache_root else (settings.data_root / "_cache" / "inep")
        self.downloader = downloader or BulkDownloader(cache_path)

    # ------------------------------------------------------------------
    # URL resolution
    # ------------------------------------------------------------------
    def build_url(self, reference_period: str | int) -> str:
        return self.URL_TEMPLATE.format(year=int(reference_period))

    # ------------------------------------------------------------------
    # Fetch (download + extract)
    # ------------------------------------------------------------------
    def fetch(
        self,
        *,
        reference_period: str | int,
        **kwargs: Any,
    ) -> tuple[pd.DataFrame, str]:
        url = self.build_url(reference_period)
        log.info(
            "inep.fetch",
            source=self.source,
            dataset=self._effective_dataset(),
            url=url,
            year=int(reference_period),
        )
        download = self.downloader.download(url)
        df = self._load_dataframe(download.local_path)
        log.info(
            "inep.fetch.parsed",
            url=url,
            local_path=str(download.local_path),
            sha256=download.sha256,
            rows=len(df),
            columns=len(df.columns),
        )
        return df, url

    # ------------------------------------------------------------------
    # Para subclasses
    # ------------------------------------------------------------------
    def _load_dataframe(self, local_path: Path) -> pd.DataFrame:
        raise NotImplementedError
