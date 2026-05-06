"""Sprint 5.2 — testes das 4 tools de dados.

Cada tool e validada isoladamente com `EduGatewayClient` apontando para
um `httpx.MockTransport`. As tools devolvem JSON string que o LLM
consumiria; aqui parseamos pra validar estrutura.
"""

from __future__ import annotations

import json

import pytest

from src.api_client import EduGatewayClient
from src.tools import (
    DataCatalogTool,
    DataCompareTool,
    DataRankingTool,
    DataTimeseriesTool,
    build_data_tools,
)


# ----------------------------------------------------------------------
# build_data_tools
# ----------------------------------------------------------------------


def test_build_data_tools_returns_4_tools(gateway_handler_factory):
    transport = gateway_handler_factory({})
    client = EduGatewayClient(transport=transport)
    tools = build_data_tools(client=client)
    names = [t.name for t in tools]
    assert names == ["data_catalog", "data_timeseries", "data_compare", "data_ranking"]


def test_tools_share_injected_client(gateway_handler_factory):
    transport = gateway_handler_factory({})
    client = EduGatewayClient(transport=transport)
    build_data_tools(client=client)
    assert DataCatalogTool._client_override is client
    assert DataCompareTool._client_override is client


# ----------------------------------------------------------------------
# data_catalog
# ----------------------------------------------------------------------


def test_catalog_tool_returns_ok_payload(
    gateway_handler_factory, sample_catalog_payload
):
    transport = gateway_handler_factory(
        {("GET", "/api/data/catalog"): {"status": 200, "json": sample_catalog_payload}}
    )
    client = EduGatewayClient(transport=transport)
    tools = build_data_tools(client=client)
    raw = tools[0].run()
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert len(payload["data"]) == 3
    assert payload["meta"]["total_rows"] == 3


# ----------------------------------------------------------------------
# data_timeseries
# ----------------------------------------------------------------------


def test_timeseries_tool_happy_path(gateway_handler_factory, sample_timeseries_payload):
    transport = gateway_handler_factory(
        {
            ("POST", "/api/data/timeseries"): {
                "status": 200,
                "json": sample_timeseries_payload,
            }
        }
    )
    client = EduGatewayClient(transport=transport)
    tools = build_data_tools(client=client)
    timeseries = next(t for t in tools if t.name == "data_timeseries")
    raw = timeseries.run(
        indicator="GASTO_EDU_PIB",
        country_iso3="BRA",
        year_start=2018,
        year_end=2022,
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["meta"]["total_rows"] == 5
    assert payload["data"][0]["year"] == 2018


def test_timeseries_tool_invalid_iso3_returns_validation_error(
    gateway_handler_factory,
):
    """Pydantic levanta ValidationError ANTES do gateway: tool captura
    e devolve JSON com error_type=validation."""
    transport = gateway_handler_factory({})
    client = EduGatewayClient(transport=transport)
    tools = build_data_tools(client=client)
    timeseries = next(t for t in tools if t.name == "data_timeseries")
    raw = timeseries.run(
        indicator="GASTO_EDU_PIB",
        country_iso3="br",  # minuscula -> falha pattern
        year_start=2018,
        year_end=2022,
    )
    payload = json.loads(raw)
    assert payload["ok"] is False
    assert payload["error"]["error_type"] == "validation"


# ----------------------------------------------------------------------
# data_compare
# ----------------------------------------------------------------------


def test_compare_tool_happy_path(gateway_handler_factory, sample_compare_payload):
    transport = gateway_handler_factory(
        {("POST", "/api/data/compare"): {"status": 200, "json": sample_compare_payload}}
    )
    client = EduGatewayClient(transport=transport)
    tools = build_data_tools(client=client)
    compare = next(t for t in tools if t.name == "data_compare")
    raw = compare.run(
        indicator="GASTO_EDU_PIB",
        countries=["BRA", "FIN", "USA", "MEX"],
        year=2020,
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["meta"]["total_rows"] == 4
    assert payload["meta"]["extra"]["comparison_stats"]["mean"] == pytest.approx(5.75)


def test_compare_tool_validation_error_no_countries(gateway_handler_factory):
    transport = gateway_handler_factory({})
    client = EduGatewayClient(transport=transport)
    tools = build_data_tools(client=client)
    compare = next(t for t in tools if t.name == "data_compare")
    raw = compare.run(indicator="GASTO_EDU_PIB", countries=[], year=2020)
    payload = json.loads(raw)
    assert payload["ok"] is False
    assert payload["error"]["error_type"] == "validation"


def test_compare_tool_propagates_gateway_404(gateway_handler_factory):
    transport = gateway_handler_factory(
        {
            ("POST", "/api/data/compare"): {
                "status": 404,
                "json": {"detail": "no rows for combination"},
            }
        }
    )
    client = EduGatewayClient(transport=transport)
    tools = build_data_tools(client=client)
    compare = next(t for t in tools if t.name == "data_compare")
    raw = compare.run(
        indicator="GASTO_EDU_PIB",
        countries=["BRA"],
        year=1990,
        source="cepalstat",
    )
    payload = json.loads(raw)
    assert payload["ok"] is False
    assert payload["error"]["error_type"] == "not_found"
    assert payload["error"]["status_code"] == 404


# ----------------------------------------------------------------------
# data_ranking
# ----------------------------------------------------------------------


def test_ranking_tool_happy_path(gateway_handler_factory):
    payload = {
        "data": [
            {"rank": 1, "country_iso3": "SWE", "country_name": "Sweden", "value": 7.32},
            {"rank": 2, "country_iso3": "ISL", "country_name": "Iceland", "value": 7.31},
            {"rank": 3, "country_iso3": "FIN", "country_name": "Finland", "value": 6.38},
        ],
        "meta": {
            "total_rows": 3,
            "query_ms": 6.1,
            "sources": ["worldbank"],
            "extra": {
                "indicator": "GASTO_EDU_PIB",
                "year_used": 2022,
                "grouping": "oecd",
                "total_in_grouping": 26,
                "showing": 3,
            },
        },
    }
    transport = gateway_handler_factory(
        {("POST", "/api/data/ranking"): {"status": 200, "json": payload}}
    )
    client = EduGatewayClient(transport=transport)
    tools = build_data_tools(client=client)
    ranking = next(t for t in tools if t.name == "data_ranking")
    raw = ranking.run(indicator="GASTO_EDU_PIB", grouping="oecd", limit=3)
    out = json.loads(raw)
    assert out["ok"] is True
    assert out["data"][0]["rank"] == 1
    assert out["meta"]["extra"]["year_used"] == 2022


def test_ranking_tool_invalid_grouping(gateway_handler_factory):
    transport = gateway_handler_factory({})
    client = EduGatewayClient(transport=transport)
    tools = build_data_tools(client=client)
    ranking = next(t for t in tools if t.name == "data_ranking")
    raw = ranking.run(indicator="GASTO_EDU_PIB", grouping="not_a_real_group")
    payload = json.loads(raw)
    assert payload["ok"] is False
    assert payload["error"]["error_type"] == "validation"
