"""Helpers de resposta compartilhados entre routers.

Centraliza o pipeline "cronometra query -> monta DataResponse + ResponseMeta"
que estava duplicado nos 3 endpoints de /api/data. Adicionar um 4o
endpoint (ex.: /api/data/describe do MP3 do quality plan) vira ~3 linhas
em vez de copiar 15 linhas de boilerplate.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Callable

from src.schemas.common import DataResponse, ResponseMeta


@contextmanager
def measure_query_ms() -> Iterator[Callable[[], float]]:
    """Context manager que mede o tempo em milissegundos.

    Uso:
        with measure_query_ms() as elapsed:
            rows = service(...)
        return build_data_response(rows, query_ms=elapsed(), ...)
    """
    started = time.perf_counter()
    yield lambda: (time.perf_counter() - started) * 1000.0


def build_data_response(
    rows: list[dict[str, Any]],
    *,
    query_ms: float,
    sources: list[str] | None = None,
    extra: dict[str, Any] | None = None,
    empty_note: str | None = None,
) -> DataResponse:
    """Monta um `DataResponse` consistente para qualquer endpoint /api/data.

    Args:
        rows: linhas de dados (lista de dicts).
        query_ms: tempo medido via `measure_query_ms()`.
        sources: lista de fontes usadas (ex.: ['worldbank']).
        extra: campos adicionais para `meta.extra` (indicador, ano, etc.).
        empty_note: mensagem para incluir em `meta.notes` quando `rows`
            esta vazio. Use uma string explicativa; ignorada se nao vazia.

    Padroniza a regra "se vazio, adiciona nota explicativa" que estava
    duplicada nos 3 endpoints.
    """
    notes: list[str] | None = None
    if not rows and empty_note:
        notes = [empty_note]
    return DataResponse(
        data=rows,
        meta=ResponseMeta(
            total_rows=len(rows),
            query_ms=round(query_ms, 2),
            sources=sources,
            notes=notes,
            extra=extra,
        ),
    )
