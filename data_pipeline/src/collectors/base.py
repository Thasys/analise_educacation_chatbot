"""Classe base de coletores.

Todo coletor da camada Bronze:
  1. Resolve uma URL/recurso para um período de referência.
  2. Retorna um DataFrame em `fetch()`.
  3. A `collect()` da base cuida de escrever na Bronze e logar a execução.

Subclasses só precisam implementar `fetch()` e declarar `source` e `dataset`.

Atualizado 2026-05-14 (#7 do DRY pass): a base ganhou
`_http_fetch_json(url)` e `_http_fetch_paginated(...)` para encapsular o
ciclo de vida do `httpx.Client` + logging consistente que estava
duplicado em 7 coletores REST. Subclasses HTTP devem usar esses metodos
em vez de gerenciar `httpx.Client` manualmente.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, ClassVar

import httpx
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

    # ------------------------------------------------------------------
    # Helpers HTTP compartilhados (#7 do DRY pass)
    # ------------------------------------------------------------------
    def _http_fetch_json(
        self,
        url: str,
        *,
        accept: str = "application/json",
        http_client: httpx.Client | None = None,
    ) -> Any:
        """GET de uma URL, decodificando JSON com gestao de Client.

        Encapsula o `httpx.Client` + try/finally + raise_for_status que
        estava duplicado em 7 coletores REST. Cuidados:

        - Se `http_client` for passado (caso tipico em testes com
          `MockTransport`), nao fechamos o client — quem injetou cuida do
          ciclo de vida.
        - Caso contrario, criamos um Client com timeout das settings e
          fechamos no final.
        - O `Accept` default e JSON, mas pode ser sobrescrito (ex.: OECD
          quer `application/vnd.sdmx.data+json;version=2.0.0`).
        """
        client = http_client or httpx.Client(timeout=settings.http_timeout_seconds)
        try:
            response = client.get(url, headers={"Accept": accept})
            response.raise_for_status()
            return response.json()
        finally:
            if http_client is None:
                client.close()

    def _http_fetch_paginated(
        self,
        first_url: str,
        *,
        next_link_fn: Callable[[Any], str | None],
        records_fn: Callable[[Any, str], list[dict[str, Any]]],
        accept: str = "application/json",
        http_client: httpx.Client | None = None,
        max_pages: int = 200,
        log_event: str = "http.fetch_paginated",
    ) -> list[dict[str, Any]]:
        """Acumula registros seguindo `nextLink` ate `max_pages`.

        Args:
            first_url: URL da primeira pagina.
            next_link_fn: dado um payload, devolve a URL da proxima pagina
                ou None quando acabou.
            records_fn: dado um payload e a URL atual, devolve a lista de
                registros da pagina (levanta ValueError se payload mal-formado).
            accept: header Accept.
            http_client: client injetado (testes); None cria um novo.
            max_pages: cap de seguranca contra loops infinitos.
            log_event: nome do evento de log por iteracao.

        Generalizacao do padrao em `WorldBankCollector._fetch_paginated`
        e `IpeaDataCollector._fetch_paginated`.
        """
        client = http_client or httpx.Client(timeout=settings.http_timeout_seconds)
        try:
            url: str | None = first_url
            records: list[dict[str, Any]] = []
            page = 0
            while url:
                page += 1
                log.info(log_event, url=url, page=page)
                response = client.get(url, headers={"Accept": accept})
                response.raise_for_status()
                payload = response.json()
                records.extend(records_fn(payload, url))
                url = next_link_fn(payload)
                if page >= max_pages:
                    log.warning(
                        f"{log_event}.cap_hit",
                        pages=page,
                        max_pages=max_pages,
                    )
                    break
            return records
        finally:
            if http_client is None:
                client.close()
