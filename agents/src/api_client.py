"""Cliente HTTP para o FastAPI gateway (Fase 4).

`EduGatewayClient` e o unico canal pelo qual tools/agentes leem dados
da camada Gold. Encapsula:
  - serializacao Pydantic -> JSON
  - retry simples para erros transientes (5xx + 429)
  - timeout configuravel (settings.gateway_timeout_seconds)
  - propagacao de X-Request-ID para tracing cross-service

A regra critica do CLAUDE.md ("agentes NAO escrevem SQL livre") e
honrada arquiteturalmente aqui: este e o unico ponto de acesso aos
dados, e ele so fala com endpoints REST validados.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import httpx
import structlog

from src.config import settings
from src.schemas import (
    CompareArgs,
    DataResponse,
    GatewayError,
    RankingArgs,
    TimeseriesArgs,
)


log = structlog.get_logger(__name__)


_RETRY_STATUS = {429, 500, 502, 503, 504}


class EduGatewayClient:
    """Cliente sincrono para `http://<gateway>/api/data/*`."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = (base_url or settings.gateway_base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.gateway_timeout_seconds
        self.max_retries = (
            max_retries if max_retries is not None else settings.gateway_max_retries
        )
        # Transport injetado pelos testes via httpx.MockTransport.
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            transport=transport,
            headers={"Accept": "application/json", "User-Agent": "edu-agents/0.1"},
        )

    # -- ciclo de vida ------------------------------------------------

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "EduGatewayClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- transporte interno -------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Executa request com retry; devolve dict do JSON da resposta.

        Levanta `httpx.HTTPStatusError` apenas em 4xx nao-retryable
        (validation, not_found). Em sucesso retorna dict cru.
        """
        rid = request_id or str(uuid.uuid4())
        headers = {"X-Request-ID": rid}
        attempt = 0
        last_exc: Exception | None = None

        while attempt <= self.max_retries:
            attempt += 1
            try:
                started = time.perf_counter()
                response = self._client.request(
                    method, path, json=json, headers=headers
                )
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                log.debug(
                    "agents.gateway.request",
                    method=method,
                    path=path,
                    status=response.status_code,
                    attempt=attempt,
                    elapsed_ms=round(elapsed_ms, 2),
                    request_id=rid,
                )
                if response.status_code in _RETRY_STATUS and attempt <= self.max_retries:
                    backoff = 0.25 * (2 ** (attempt - 1))
                    log.warning(
                        "agents.gateway.retry",
                        status=response.status_code,
                        attempt=attempt,
                        backoff_s=backoff,
                    )
                    time.sleep(backoff)
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError:
                # 4xx (exceto 429) — nao adianta retry.
                raise
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt > self.max_retries:
                    break
                backoff = 0.25 * (2 ** (attempt - 1))
                log.warning(
                    "agents.gateway.retry_transport",
                    error=str(exc),
                    attempt=attempt,
                    backoff_s=backoff,
                )
                time.sleep(backoff)

        # Esgotou retries.
        assert last_exc is not None
        raise last_exc

    # -- endpoints ----------------------------------------------------

    def catalog(self, *, request_id: str | None = None) -> DataResponse:
        """GET /api/data/catalog -> lista de marts Gold."""
        payload = self._request("GET", "/api/data/catalog", request_id=request_id)
        return DataResponse.model_validate(payload)

    def timeseries(
        self, args: TimeseriesArgs, *, request_id: str | None = None
    ) -> DataResponse:
        """POST /api/data/timeseries -> serie temporal de um indicador-pais."""
        payload = self._request(
            "POST",
            "/api/data/timeseries",
            json=args.model_dump(exclude_none=True),
            request_id=request_id,
        )
        return DataResponse.model_validate(payload)

    def compare(
        self, args: CompareArgs, *, request_id: str | None = None
    ) -> DataResponse:
        """POST /api/data/compare -> comparacao N paises ano-fonte."""
        payload = self._request(
            "POST",
            "/api/data/compare",
            json=args.model_dump(exclude_none=True),
            request_id=request_id,
        )
        return DataResponse.model_validate(payload)

    def ranking(
        self, args: RankingArgs, *, request_id: str | None = None
    ) -> DataResponse:
        """POST /api/data/ranking -> top-N paises em um indicador."""
        payload = self._request(
            "POST",
            "/api/data/ranking",
            json=args.model_dump(exclude_none=True),
            request_id=request_id,
        )
        return DataResponse.model_validate(payload)

    # -- helpers para tools (capturam erro como GatewayError) ---------

    def safe_call(
        self,
        method: str,
        *args: Any,
        request_payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> DataResponse | GatewayError:
        """Chama um metodo (catalog/timeseries/compare/ranking) capturando
        erros HTTP em `GatewayError` estruturado.

        Usado pelas tools para devolver erros ao agente em formato
        determinado, em vez de quebrar a crew com excecao.
        """
        try:
            fn = getattr(self, method)
            return fn(*args, **kwargs)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            etype = (
                "validation"
                if status == 422
                else "not_found"
                if status == 404
                else "rate_limited"
                if status == 429
                else "unknown"
            )
            try:
                detail = exc.response.json().get("detail")
            except ValueError:
                detail = exc.response.text[:500]
            return GatewayError(
                error_type=etype,
                status_code=status,
                message=str(detail) if detail else f"HTTP {status}",
                request_payload=request_payload,
            )
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            return GatewayError(
                error_type="network",
                status_code=None,
                message=f"{type(exc).__name__}: {exc}",
                suggestion="Verifique se o gateway esta em http://localhost:8000.",
                request_payload=request_payload,
            )
