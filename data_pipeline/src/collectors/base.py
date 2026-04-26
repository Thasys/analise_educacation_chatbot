"""Classe base de coletores.

Todo coletor da camada Bronze:
  1. Resolve uma URL/recurso para um período de referência.
  2. Retorna um DataFrame em `fetch()`.
  3. A `collect()` da base cuida de escrever na Bronze e logar a execução.

Subclasses só precisam implementar `fetch()` e declarar `source` e `dataset`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

import pandas as pd

from src.config import settings
from src.logging_config import get_logger
from src.utils.bronze import BronzeWriteResult, BronzeWriter
from src.utils.ingestion_log import IngestionLogger

log = get_logger(__name__)


class BaseCollector(ABC):
    """Contrato comum a todos os coletores Bronze.

    Atributos de classe:
        source : nome curto da fonte (ex.: 'ibge', 'oecd', 'inep').
        dataset: identificador estável do dataset dentro da fonte.
                 Pode ser sobrescrito pelo `__init__` da subclasse.
    """

    source: ClassVar[str]
    dataset: ClassVar[str] = ""

    def __init__(
        self,
        *,
        bronze_writer: BronzeWriter | None = None,
        ingestion_logger: IngestionLogger | None = None,
    ) -> None:
        if not getattr(self, "source", ""):
            raise ValueError(
                f"Subclasse {type(self).__name__} precisa definir `source` "
                "como atributo de classe."
            )
        self.bronze = bronze_writer or BronzeWriter(settings.bronze_root)
        self.ingestion_logger = ingestion_logger

    # ------------------------------------------------------------------
    # Contrato a implementar
    # ------------------------------------------------------------------
    @abstractmethod
    def fetch(
        self,
        *,
        reference_period: str | int,
        **kwargs: Any,
    ) -> tuple[pd.DataFrame, str]:
        """Busca dados na fonte e devolve (DataFrame, URL_de_origem).

        Implementações devem ser puras: sem efeitos colaterais em filesystem
        ou banco; só I/O de rede contra a fonte.
        """

    # ------------------------------------------------------------------
    # Pipeline de coleta
    # ------------------------------------------------------------------
    def collect(
        self,
        *,
        reference_period: str | int,
        **kwargs: Any,
    ) -> BronzeWriteResult:
        """Orquestra fetch → bronze → log."""
        ds = self._effective_dataset()
        log.info(
            "collector.start",
            source=self.source,
            dataset=ds,
            reference_period=str(reference_period),
        )

        run_id: int | None = None
        if self.ingestion_logger:
            run_id = self.ingestion_logger.start_run(
                source=self.source,
                dataset=ds,
                reference_period=str(reference_period),
                source_url="(pending)",
            )

        try:
            df, source_url = self.fetch(reference_period=reference_period, **kwargs)
            result = self.bronze.write(
                df,
                source=self.source,
                dataset=ds,
                reference_period=reference_period,
                source_url=source_url,
            )
        except Exception as exc:
            log.error(
                "collector.failed",
                source=self.source,
                dataset=ds,
                reference_period=str(reference_period),
                error=str(exc),
            )
            if self.ingestion_logger and run_id is not None:
                self.ingestion_logger.finish_run(
                    run_id, status="failed", error_message=str(exc)
                )
            raise

        log.info(
            "collector.success",
            source=self.source,
            dataset=ds,
            reference_period=str(reference_period),
            rows=result.row_count,
            path=result.parquet_path,
        )
        if self.ingestion_logger and run_id is not None:
            self.ingestion_logger.finish_run(
                run_id,
                status="success",
                rows_ingested=result.row_count,
                output_path=result.parquet_path,
                source_url=result.source_url,
                metadata=result.to_dict(),
            )
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _effective_dataset(self) -> str:
        ds = getattr(self, "dataset", "") or type(self).dataset
        if not ds:
            raise ValueError(
                f"Coletor {type(self).__name__} não definiu `dataset`."
            )
        return ds
