"""Base compartilhada para tools CrewAI deste projeto.

`SafeTool` captura erros de validacao do `args_schema` (Pydantic) que o
CrewAI BaseTool.run() levantaria como `ValueError`, devolvendo um JSON
estruturado de erro. Sem isso, o loop CrewAI quebraria; com isso, o LLM
pode ler o erro, corrigir os args e tentar de novo.

Tambem oferece dois opcionais para guardrails de qualidade:

- `output_validator`: callable que recebe o `dict`/`str` retornado por
  `_run` e devolve `None` se OK ou uma string de erro se invalido. Quando
  invalido, a tool serializa erro `validation` em vez de devolver o
  payload quebrado. Pre-requisito para QW1 (validar `plotly_figure`) e
  QW3 (validar consistencia numerica).

Mantemos `_validation_error_payload` aqui para evitar import circular
com `data_tools.py`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Callable, ClassVar, TypeVar

from crewai.tools import BaseTool

T = TypeVar("T", bound=BaseTool)


def _validation_error_payload(message: str) -> str:
    """JSON de erro estruturado usado em todas as tools."""
    return json.dumps(
        {"ok": False, "error": {"error_type": "validation", "message": message}}
    )


class SafeTool(BaseTool):
    """BaseTool com handler uniforme para ValueError + output validator opcional.

    Subclasses podem definir `output_validator` como ClassVar (ou
    instancia) para inspecionar a string retornada por `_run` antes de
    devolve-la ao agente. Se o validator retornar uma mensagem nao-vazia,
    a tool substitui o output por `_validation_error_payload(...)`.
    """

    # Validator opcional. Se None, comportamento e identico ao do
    # BaseTool padrao (apenas captura ValueError).
    output_validator: ClassVar[Callable[[str], str | None] | None] = None

    def run(self, *args: Any, **kwargs: Any) -> Any:
        try:
            raw = super().run(*args, **kwargs)
        except ValueError as exc:
            return _validation_error_payload(str(exc))
        validator = type(self).output_validator
        if validator is not None and isinstance(raw, str):
            err = validator(raw)
            if err:
                return _validation_error_payload(err)
        return raw


# ----------------------------------------------------------------------
# Factory helper compartilhado (#4 do DRY pass)
# ----------------------------------------------------------------------


def instantiate_with_shared_client(
    tool_classes: Sequence[type[T]],
    client: object | None,
) -> list[T]:
    """Instancia tools propagando um cliente compartilhado (HTTP, RAG, ...).

    Substitui o padrao repetido em `build_data_tools` e `build_rag_tools`:

        if client is not None:
            ToolA._client_override = client
            ToolB._client_override = client
            ...
        return [ToolA(), ToolB(), ...]

    Toda nova tool exigia atualizar o ClassVar + a factory. Agora basta
    incluir a classe na sequencia.
    """
    if client is not None:
        for cls in tool_classes:
            cls._client_override = client  # type: ignore[attr-defined]
    return [cls() for cls in tool_classes]
