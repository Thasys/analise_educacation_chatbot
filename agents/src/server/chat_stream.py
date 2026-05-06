"""Router POST /api/chat/stream — Server-Sent Events do master flow.

Estrategia:
  1. Cliente faz POST com `{question: str}`.
  2. Servidor abre `StreamingResponse(media_type="text/event-stream")`.
  3. `run_master` roda em executor (`asyncio.to_thread`) com callback
     que coloca eventos numa `asyncio.Queue`.
  4. Generator async drena a queue e formata como linhas SSE
     (`event: <type>\\ndata: <json>\\n\\n`).
  5. Quando `run_master` retorna, emitimos `event: final_answer` final
     e fechamos a stream.

Erros sao capturados e emitidos como `event: error`. A conexao SSE
NUNCA propaga exception nao tratada.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.crews import run_master
from src.server.schemas import ChatStreamRequest


log = structlog.get_logger(__name__)

router = APIRouter()


# Sentinela usada para sinalizar fim da stream.
_END_OF_STREAM = object()


def _format_sse(event_type: str, data: dict[str, Any]) -> str:
    """Formata um evento SSE conforme espec W3C.

    Cada evento tem 2 linhas obrigatorias seguidas de linha em branco:
        event: <tipo>
        data: <json>
        <linha em branco>
    """
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


async def _stream_master_flow(request: ChatStreamRequest) -> AsyncGenerator[str, None]:
    """Async generator que executa run_master e emite SSE por evento."""
    # Queue thread-safe via run_coroutine_threadsafe — obtemos loop atual.
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()

    def on_event(event: dict[str, Any]) -> None:
        # Chamado da thread do executor; usamos call_soon_threadsafe
        # para enfileirar do main loop.
        loop.call_soon_threadsafe(queue.put_nowait, event)

    async def _run_in_executor() -> None:
        try:
            await asyncio.to_thread(
                run_master, request.question, on_event=on_event
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("server.chat_stream.run_master_failed")
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "error", "error": str(exc), "ts": 0.0},
            )
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, _END_OF_STREAM)

    task = asyncio.create_task(_run_in_executor())
    try:
        while True:
            event = await queue.get()
            if event is _END_OF_STREAM:
                break
            event_type = event.get("type", "unknown")
            yield _format_sse(event_type, event)
    finally:
        if not task.done():
            task.cancel()


@router.post("/api/chat/stream")
async def chat_stream(body: ChatStreamRequest) -> StreamingResponse:
    """Inicia o fluxo do master crew e emite eventos SSE."""
    log.info("server.chat_stream.request", question=body.question[:120])
    return StreamingResponse(
        _stream_master_flow(body),
        media_type="text/event-stream",
        headers={
            # Headers recomendados para SSE atravessar proxies e nao bufferizar.
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
