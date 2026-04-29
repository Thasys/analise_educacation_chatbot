"""Middleware: adiciona X-Request-ID em todas as requests/responses.

Bind do request_id no contexto do structlog para que logs do service e
do router carreguem o ID, permitindo rastrear a request inteira.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Gera UUID se ausente; bind no contextvars do structlog."""

    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(self.HEADER) or str(uuid.uuid4())
        # Disponivel para handlers via request.state.request_id
        request.state.request_id = request_id

        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response: Response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")

        response.headers[self.HEADER] = request_id
        return response
