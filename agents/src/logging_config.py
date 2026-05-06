"""Configuracao de logging estruturado para o servico de agentes.

Usa structlog com saida console legivel em desenvolvimento e JSON em
producao. Idempotente: chamar configure_logging() multiplas vezes nao
quebra a configuracao.
"""

from __future__ import annotations

import logging
import sys

import structlog

from src.config import settings

_CONFIGURED = False


def configure_logging(level: str | None = None) -> None:
    """Configura structlog uma unica vez por processo."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = (level or settings.log_level).upper()
    # stderr (nao stdout) para nao misturar logs com saida estruturada
    # do CLI/scripts (ex.: `python -m src.cli --json-only`).
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
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
        # PrintLoggerFactory default escreve em stdout; mandamos para
        # stderr para nao misturar com saida de dados (CLI --json-only).
        # Usamos sys.__stderr__ (referencia permanente ao stderr do
        # processo) em vez de sys.stderr, que pode ser substituido por
        # pytest capsys e ficar invalido apos teste finalizar.
        logger_factory=structlog.PrintLoggerFactory(file=sys.__stderr__),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    configure_logging()
    return structlog.get_logger(name) if name else structlog.get_logger()
