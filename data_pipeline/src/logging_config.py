"""Configuração de logging estruturado para o pipeline.

Usa `structlog` com saída JSON em produção e console legível em
desenvolvimento. Idempotente: chamar `configure_logging()` múltiplas
vezes não quebra a configuração.
"""

from __future__ import annotations

import logging
import sys

import structlog

from src.config import settings

_CONFIGURED = False


def configure_logging(level: str | None = None) -> None:
    """Configura structlog uma única vez por processo."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = (level or settings.log_level).upper()
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    is_dev = settings.environment.lower() in {"development", "dev", "local"}
    renderer = (
        structlog.dev.ConsoleRenderer(colors=True)
        if is_dev
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level, logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Retorna um logger configurado. Lazy: configura se necessário."""
    configure_logging()
    return structlog.get_logger(name) if name else structlog.get_logger()
