"""Fixtures compartilhadas para testes do servico de agentes.

A maioria dos testes roda offline com `httpx.MockTransport`; nenhum
requer DuckDB local nem chave Anthropic. Os testes "live" (Sprint 5.6)
ficam marcados com `@pytest.mark.live` e so rodam com `-m live`.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import httpx
import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "live: testes E2E que requerem ANTHROPIC_API_KEY e gateway up. Skip por default.",
    )


@pytest.fixture(autouse=True)
def _force_anthropic_provider_for_tests(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests de agentes/tools assumem provider=anthropic (mock_llm_call patcheia AnthropicCompletion).

    Em desenvolvimento o .env pode estar com provider=ollama (rodando local)
    e modelos locais como `mistral-nemo:12b`. Aqui forcamos um par
    provider+modelos que o CrewAI aceita nativamente; o mock_llm_call
    intercepta antes de qualquer chamada real, entao a chave nunca eh usada.

    NAO aplicamos override em `tests/test_config.py`, `tests/test_llm.py`,
    `tests/test_cli.py` etc., porque esses testes validam justamente o
    comportamento do provider (Ollama, etc.) e configuram o env eles mesmos.
    """
    # Limita a aplicar override apenas em testes que precisam do mock.
    path = str(request.node.fspath).replace("\\", "/")
    if "/tests/agents/" not in path and "/tests/tools/" not in path:
        return
    monkeypatch.setenv("AGENTS_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-noop")
    monkeypatch.setenv("AGENTS_LLM_SMART_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("AGENTS_LLM_FAST_MODEL", "claude-haiku-4-5-20251001")
    monkeypatch.setenv("AGENTS_LLM_API_BASE", "")
    # Settings ja foi importado antes da fixture; precisamos sobrescrever
    # o singleton para que `make_llm` leia os valores corretos.
    from src import config

    monkeypatch.setattr(config.settings, "llm_provider", "anthropic", raising=False)
    monkeypatch.setattr(
        config.settings, "llm_smart_model", "claude-sonnet-4-6", raising=False
    )
    monkeypatch.setattr(
        config.settings, "llm_fast_model", "claude-haiku-4-5-20251001", raising=False
    )
    monkeypatch.setattr(config.settings, "llm_api_base", None, raising=False)


# ----------------------------------------------------------------------
# Mock transport para o gateway HTTP
# ----------------------------------------------------------------------


@pytest.fixture
def mock_llm_call(monkeypatch: pytest.MonkeyPatch):
    """Substitui `crewai.LLM.call` por uma stub configuravel.

    Uso:
        def test_x(mock_llm_call):
            mock_llm_call(by_role={
                "Orchestrator de roteamento educacional":
                    '{"flow":"data","profile":"researcher",...}',
                "Extrator de entidades educacionais":
                    '{"indicator":"GASTO_EDU_PIB","countries":["BRA","FIN"],...}',
            })

    A stub identifica o agente pelo `from_agent.role` (kwarg passado pela
    Crew) e devolve a string JSON correspondente. Cair em
    fallback `default` se nenhum role bater.
    """
    captured: dict[str, list[Any]] = {"calls": []}

    def _setup(
        *,
        by_role: dict[str, str] | None = None,
        default: str | None = None,
    ):
        responses = by_role or {}

        def fake_call(self, messages, **kwargs):
            from_agent = kwargs.get("from_agent")
            role = getattr(from_agent, "role", None)
            captured["calls"].append({"role": role, "messages": messages})
            if role and role in responses:
                return responses[role]
            if default is not None:
                return default
            raise AssertionError(
                f"mock_llm_call: nenhuma resposta configurada para role={role!r}. "
                f"Configurados: {list(responses)}"
            )

        # `crewai.LLM(...)` e factory que retorna a classe nativa
        # apropriada (AnthropicCompletion p/ provider anthropic). Cada
        # subclasse tem seu proprio override de `call`. Patcheamos a
        # classe nativa real usada por `make_llm()`.
        from crewai import LLM
        from crewai.llms.providers.anthropic.completion import AnthropicCompletion

        monkeypatch.setattr(LLM, "call", fake_call)
        monkeypatch.setattr(AnthropicCompletion, "call", fake_call)
        return captured

    return _setup


@pytest.fixture
def rag_client_in_memory(request):
    """RagClient em memoria com StubEmbedding e seeds carregados.

    Cada chamada cria uma colecao com nome UNICO (derivado do nome do
    teste) para garantir isolamento — chromadb 1.1.1 EphemeralClient
    compartilha tenant default entre instancias.
    """
    import uuid
    from pathlib import Path

    from src.rag.client import RagClient, StubEmbedding
    from src.rag.ingest import ingest_manifest

    unique_name = f"edu_lit_{uuid.uuid4().hex[:12]}"
    client = RagClient(
        embedding_fn=StubEmbedding(),
        in_memory=True,
        collection_name=unique_name,
    )
    manifest = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "rag"
        / "seeds"
        / "manifest.yaml"
    )
    ingest_manifest(manifest, client=client)
    return client


@pytest.fixture
def gateway_handler_factory() -> Callable[..., httpx.MockTransport]:
    """Fabrica de MockTransport configuravel.

    Uso tipico nos testes:

        def test_catalog(gateway_handler_factory):
            transport = gateway_handler_factory({
                ("GET", "/api/data/catalog"): {
                    "status": 200,
                    "json": {"data": [...], "meta": {"total_rows": 5}},
                },
            })
            client = EduGatewayClient(transport=transport)
            ...
    """

    def _build(
        routes: dict[tuple[str, str], dict[str, Any]],
        *,
        default_status: int = 404,
    ) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            key = (request.method, request.url.path)
            spec = routes.get(key)
            if spec is None:
                return httpx.Response(
                    default_status,
                    json={"detail": f"unmocked route {key}"},
                )
            status = spec.get("status", 200)
            json_body = spec.get("json")
            if json_body is None:
                return httpx.Response(status)
            return httpx.Response(status, json=json_body)

        return httpx.MockTransport(handler)

    return _build


@pytest.fixture
def sample_catalog_payload() -> dict[str, Any]:
    """Payload representativo de GET /api/data/catalog (5 marts)."""
    return {
        "data": [
            {
                "name": "mart_alfabetizacao__latam_2020s",
                "schema_name": "main_marts",
                "row_count": 38,
                "column_count": 12,
                "description": "Taxa de alfabetizacao 15+ para Brasil + LATAM, 2020-2024.",
                "tags": ["gold", "alfabetizacao"],
            },
            {
                "name": "mart_br_vs_ocde__gasto_educacao_timeseries",
                "schema_name": "main_marts",
                "row_count": 491,
                "column_count": 18,
                "description": "Gasto publico em educacao (% PIB) BR + 38 OCDE, 2010-2023.",
                "tags": ["gold", "gasto"],
            },
            {
                "name": "mart_indicadores__rankings_recente",
                "schema_name": "main_marts",
                "row_count": 134,
                "column_count": 10,
                "description": "Rankings cross-indicador no ano mais recente.",
                "tags": ["gold", "rankings"],
            },
        ],
        "meta": {
            "total_rows": 3,
            "query_ms": 27.5,
            "sources": None,
            "notes": None,
            "extra": None,
        },
    }


@pytest.fixture
def sample_timeseries_payload() -> dict[str, Any]:
    """Payload de POST /api/data/timeseries (BRA gasto, 2018-2022)."""
    return {
        "data": [
            {"year": 2018, "source": "worldbank", "value": 6.09},
            {"year": 2019, "source": "worldbank", "value": 5.87},
            {"year": 2020, "source": "worldbank", "value": 5.77},
            {"year": 2021, "source": "worldbank", "value": 5.65},
            {"year": 2022, "source": "worldbank", "value": 5.62},
        ],
        "meta": {
            "total_rows": 5,
            "query_ms": 4.8,
            "sources": ["worldbank"],
            "notes": None,
            "extra": {
                "indicator": "GASTO_EDU_PIB",
                "country_iso3": "BRA",
                "year_start": 2018,
                "year_end": 2022,
            },
        },
    }


@pytest.fixture
def sample_compare_payload() -> dict[str, Any]:
    """Payload de POST /api/data/compare (BRA/FIN/USA/MEX 2020 gasto)."""
    return {
        "data": [
            {"country_iso3": "BRA", "country_name": "Brazil", "value": 5.77},
            {"country_iso3": "FIN", "country_name": "Finland", "value": 6.68},
            {"country_iso3": "MEX", "country_name": "Mexico", "value": 4.50},
            {"country_iso3": "USA", "country_name": "United States", "value": 6.05},
        ],
        "meta": {
            "total_rows": 4,
            "query_ms": 5.2,
            "sources": ["worldbank"],
            "notes": None,
            "extra": {
                "indicator": "GASTO_EDU_PIB",
                "year": 2020,
                "source": "worldbank",
                "comparison_stats": {
                    "min": 4.50, "max": 6.68, "mean": 5.75,
                    "median": 5.91, "countries_with_data": 4,
                },
            },
        },
    }
