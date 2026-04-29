"""Rate limiter SlowAPI.

Default 60 req/min por IP. Pode ser desabilitado em desenvolvimento via
`API_RATELIMIT_DISABLED=true`. Limites por rota aplicados via decorador
`@limiter.limit("XX/period")` nos routers.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import settings


def _key_func(request) -> str:
    """Identifica o cliente. Quando rate limiting esta desabilitado,
    todos compartilham a mesma chave (efetivamente desativando)."""
    if settings.api_ratelimit_disabled:
        return "ratelimit-disabled"
    return get_remote_address(request)


limiter = Limiter(
    key_func=_key_func,
    default_limits=[settings.api_ratelimit_default],
    enabled=not settings.api_ratelimit_disabled,
)
