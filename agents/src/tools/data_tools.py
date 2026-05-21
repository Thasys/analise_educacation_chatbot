"""Tools CrewAI que consomem os endpoints do FastAPI gateway (Fase 4).

Cada tool e wrapper fino sobre o `EduGatewayClient`:

1. Recebe args validados pelo CrewAI via `args_schema` (Pydantic v2).
2. Chama o client HTTP que faz POST/GET com retry e propaga
   `X-Request-ID`.
3. Retorna JSON serializado para o LLM (string compacta).
4. Em erro estruturado (`GatewayError`), serializa o erro com hint de
   correcao — o agente decide o proximo passo.

`SafeTool` (em `_base.py`) captura o `ValueError` que CrewAI BaseTool.run
levanta quando os args nao batem com `args_schema` — convertendo em JSON
de erro (em vez de quebrar o loop CrewAI).

Estrategia de cliente compartilhado: `_client_override` em ClassVar
(setada por `build_data_tools(client=...)`). Em producao, ausente; cada
instancia cria seu proprio `EduGatewayClient` com defaults.

Atualizado 2026-05-14 (#2 do DRY pass): as tools `timeseries`, `compare`
e `ranking` eram quase identicas. Agora herdam de `_EndpointTool` que
recebe `endpoint` e `args_model` como ClassVar. Adicionar uma 4a tool
(ex.: `data_describe` do MP3) e trivial.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

from crewai.tools import BaseTool
from pydantic import BaseModel

from src.api_client import EduGatewayClient
from src.schemas import (
    CompareArgs,
    DataResponse,
    GatewayError,
    RankingArgs,
    TimeseriesArgs,
)
from src.tools._base import SafeTool, instantiate_with_shared_client


# ----------------------------------------------------------------------
# Schemas auxiliares
# ----------------------------------------------------------------------


class _NoArgs(BaseModel):
    """Schema vazio para tools sem argumentos (catalog)."""


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _serialize_response(resp: DataResponse | GatewayError) -> str:
    """Serializa resposta da tool para a janela de contexto do LLM.

    Mantemos JSON compacto (sem indentacao) para economizar tokens.
    Estrutura:
      sucesso -> {"ok": true, "data": [...], "meta": {...}}
      erro    -> {"ok": false, "error": {...}}
    """
    if isinstance(resp, GatewayError):
        return json.dumps({"ok": False, "error": resp.model_dump()})
    return json.dumps(
        {"ok": True, "data": resp.data, "meta": resp.meta.model_dump(exclude_none=True)}
    )


def _client_for_tool(tool_cls: type[BaseTool]) -> EduGatewayClient:
    """Resolve o EduGatewayClient da tool — injetado em testes via
    `ToolClass._client_override`, ou cria um novo em producao."""
    override = getattr(tool_cls, "_client_override", None)
    return override if override is not None else EduGatewayClient()


# ----------------------------------------------------------------------
# Base — _EndpointTool
# ----------------------------------------------------------------------


class _EndpointTool(SafeTool):
    """Base para tools que sao thin wrappers sobre um endpoint do gateway.

    Subclasses declaram `endpoint` (nome usado por `safe_call`) e
    `args_model` (BaseModel a instanciar a partir dos kwargs). O `_run`
    fica generico — adicionar uma nova tool eh ~10 linhas (subclasse com
    name, description, args_schema, endpoint, args_model).
    """

    endpoint: ClassVar[str] = ""
    args_model: ClassVar[type[BaseModel]] = BaseModel

    _client_override: ClassVar[EduGatewayClient | None] = None

    def _run(self, **kwargs: Any) -> str:
        args = type(self).args_model(**kwargs)
        client = _client_for_tool(type(self))
        resp = client.safe_call(
            type(self).endpoint,
            args,
            request_payload=args.model_dump(exclude_none=True),
        )
        return _serialize_response(resp)


# ----------------------------------------------------------------------
# Tool 1: data_catalog (sem args, mantem _run proprio)
# ----------------------------------------------------------------------


class DataCatalogTool(SafeTool):
    name: str = "data_catalog"
    description: str = (
        "Lista todos os marts Gold publicados na camada analitica do sistema. "
        "Use quando precisar descobrir quais datasets estao disponiveis "
        "antes de chamar uma tool especifica. Sem argumentos. "
        "Retorna JSON com lista de marts (name, description, row_count, tags)."
    )
    args_schema: type[BaseModel] = _NoArgs

    _client_override: ClassVar[EduGatewayClient | None] = None

    def _run(self, **_kwargs: Any) -> str:
        client = _client_for_tool(type(self))
        resp = client.safe_call("catalog", request_payload={})
        return _serialize_response(resp)


# ----------------------------------------------------------------------
# Tool 2: data_timeseries
# ----------------------------------------------------------------------


class DataTimeseriesTool(_EndpointTool):
    name: str = "data_timeseries"
    description: str = (
        "Serie temporal de um indicador para UM pais (multi-fonte). "
        "Argumentos: indicator (GASTO_EDU_PIB | LITERACY_15M | "
        "IDEB_AI | IDEB_AF | IDEB_EM), country_iso3 (3 letras maiusculas; "
        "para IDEB_* use 'BRA'), year_start (>=1990), year_end (<=2030). "
        "Use quando o usuario perguntar evolucao temporal de um pais "
        "especifico. Retorna lista de pontos (year, source, value)."
    )
    args_schema: type[BaseModel] = TimeseriesArgs

    endpoint: ClassVar[str] = "timeseries"
    args_model: ClassVar[type[BaseModel]] = TimeseriesArgs


# ----------------------------------------------------------------------
# Tool 3: data_compare
# ----------------------------------------------------------------------


class DataCompareTool(_EndpointTool):
    name: str = "data_compare"
    description: str = (
        "Comparacao de N paises (1-50) em UM indicador para UM ano. "
        "Argumentos: indicator, countries (lista de ISO-3, ex.: ['BRA','FIN']), "
        "year (1990-2030), source (default worldbank). Use quando o usuario "
        "perguntar 'BR vs <paises>' ou 'comparar <paises> em <ano>'. "
        "Retorna 1 linha por pais + estatisticas (min, max, mean, median)."
    )
    args_schema: type[BaseModel] = CompareArgs

    endpoint: ClassVar[str] = "compare"
    args_model: ClassVar[type[BaseModel]] = CompareArgs

    def _run(self, **kwargs: Any) -> str:
        # Validacao 1-50 paises aqui (schema perdeu min_length/max_length
        # por compat GBNF Ollama). Mantem o contrato com o usuario do tool.
        countries = kwargs.get("countries") or []
        if not (1 <= len(countries) <= 50):
            raise ValueError(
                f"countries precisa ter 1-50 paises (recebeu {len(countries)})."
            )
        return super()._run(**kwargs)


# ----------------------------------------------------------------------
# Tool 4: data_ranking
# ----------------------------------------------------------------------


class DataRankingTool(_EndpointTool):
    name: str = "data_ranking"
    description: str = (
        "Ranking de paises em um indicador, opcionalmente filtrado por grupo. "
        "Argumentos: indicator, year (None = ano mais coberto), grouping "
        "(oecd | latam | brics | ... | None=global), source, limit (1-200). "
        "Use quando o usuario pedir 'top N paises em <indicador>' ou ranking "
        "dentro de um grupo. Retorna lista ranqueada (rank, country, value) + "
        "year_used (resolvido automaticamente)."
    )
    args_schema: type[BaseModel] = RankingArgs

    endpoint: ClassVar[str] = "ranking"
    args_model: ClassVar[type[BaseModel]] = RankingArgs


# ----------------------------------------------------------------------
# Factory — instancia as 4 tools compartilhando um client opcional
# ----------------------------------------------------------------------


def build_data_tools(
    client: EduGatewayClient | None = None,
) -> list[BaseTool]:
    """Retorna as 4 tools de dados, opcionalmente com client compartilhado.

    Em producao, basta `build_data_tools()` — cada tool cria seu cliente
    com defaults das settings. Em testes, passe `client=mock_client`; o
    helper grava o override em ClassVar antes de instanciar as tools.
    """
    return instantiate_with_shared_client(
        [DataCatalogTool, DataTimeseriesTool, DataCompareTool, DataRankingTool],
        client,
    )
