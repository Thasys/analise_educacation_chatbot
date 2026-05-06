"""Sprint 5.0 — testes do EduGatewayClient via MockTransport."""

from __future__ import annotations

import httpx
import pytest

from src.api_client import EduGatewayClient
from src.schemas import (
    CompareArgs,
    DataResponse,
    GatewayError,
    RankingArgs,
    TimeseriesArgs,
)


# ----------------------------------------------------------------------
# Happy path — cada endpoint
# ----------------------------------------------------------------------


def test_catalog_happy_path(gateway_handler_factory, sample_catalog_payload):
    transport = gateway_handler_factory(
        {("GET", "/api/data/catalog"): {"status": 200, "json": sample_catalog_payload}}
    )
    with EduGatewayClient(transport=transport) as client:
        resp = client.catalog()
    assert isinstance(resp, DataResponse)
    assert resp.meta.total_rows == 3
    assert len(resp.data) == 3
    assert any(item["name"].startswith("mart_") for item in resp.data)


def test_timeseries_happy_path(gateway_handler_factory, sample_timeseries_payload):
    transport = gateway_handler_factory(
        {
            ("POST", "/api/data/timeseries"): {
                "status": 200,
                "json": sample_timeseries_payload,
            }
        }
    )
    with EduGatewayClient(transport=transport) as client:
        resp = client.timeseries(
            TimeseriesArgs(
                indicator="GASTO_EDU_PIB",
                country_iso3="BRA",
                year_start=2018,
                year_end=2022,
            )
        )
    assert resp.meta.total_rows == 5
    assert resp.data[0]["year"] == 2018


def test_compare_happy_path(gateway_handler_factory, sample_compare_payload):
    transport = gateway_handler_factory(
        {("POST", "/api/data/compare"): {"status": 200, "json": sample_compare_payload}}
    )
    with EduGatewayClient(transport=transport) as client:
        resp = client.compare(
            CompareArgs(
                indicator="GASTO_EDU_PIB",
                countries=["BRA", "FIN", "USA", "MEX"],
                year=2020,
                source="worldbank",
            )
        )
    assert resp.meta.total_rows == 4
    assert resp.meta.extra is not None
    assert resp.meta.extra["comparison_stats"]["mean"] == pytest.approx(5.75)


def test_ranking_happy_path(gateway_handler_factory):
    payload = {
        "data": [
            {"rank": 1, "country_iso3": "SWE", "country_name": "Sweden", "value": 7.32},
            {"rank": 2, "country_iso3": "ISL", "country_name": "Iceland", "value": 7.31},
        ],
        "meta": {
            "total_rows": 2,
            "query_ms": 6.1,
            "sources": ["worldbank"],
            "extra": {
                "indicator": "GASTO_EDU_PIB",
                "year_used": 2022,
                "year_requested": None,
                "grouping": "oecd",
                "total_in_grouping": 26,
                "showing": 2,
            },
        },
    }
    transport = gateway_handler_factory(
        {("POST", "/api/data/ranking"): {"status": 200, "json": payload}}
    )
    with EduGatewayClient(transport=transport) as client:
        resp = client.ranking(
            RankingArgs(indicator="GASTO_EDU_PIB", grouping="oecd", limit=2)
        )
    assert resp.data[0]["country_iso3"] == "SWE"
    assert resp.meta.extra["year_used"] == 2022


# ----------------------------------------------------------------------
# Erros — propagacao via safe_call
# ----------------------------------------------------------------------


def test_safe_call_returns_validation_error(gateway_handler_factory):
    transport = gateway_handler_factory(
        {
            ("POST", "/api/data/compare"): {
                "status": 422,
                "json": {"detail": "year must be >= 1990"},
            }
        }
    )
    with EduGatewayClient(transport=transport) as client:
        result = client.safe_call(
            "compare",
            CompareArgs(indicator="GASTO_EDU_PIB", countries=["BRA"], year=2020),
        )
    assert isinstance(result, GatewayError)
    assert result.error_type == "validation"
    assert result.status_code == 422


def test_safe_call_returns_not_found(gateway_handler_factory):
    transport = gateway_handler_factory(
        {
            ("POST", "/api/data/ranking"): {
                "status": 404,
                "json": {"detail": "no data for indicator+source"},
            }
        }
    )
    with EduGatewayClient(transport=transport) as client:
        result = client.safe_call(
            "ranking",
            RankingArgs(indicator="GASTO_EDU_PIB", source="cepalstat"),
        )
    assert isinstance(result, GatewayError)
    assert result.error_type == "not_found"


def test_safe_call_returns_network_error():
    """Sem mock — apontando para porta morta."""
    with EduGatewayClient(
        base_url="http://127.0.0.1:1",
        timeout=0.5,
        max_retries=0,
    ) as client:
        result = client.safe_call("catalog")
    assert isinstance(result, GatewayError)
    assert result.error_type == "network"


# ----------------------------------------------------------------------
# Retry logic — 503 -> 200
# ----------------------------------------------------------------------


def test_retry_on_503_then_success(sample_catalog_payload):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, json={"detail": "temporary"})
        return httpx.Response(200, json=sample_catalog_payload)

    transport = httpx.MockTransport(handler)
    with EduGatewayClient(transport=transport, max_retries=2) as client:
        resp = client.catalog()
    assert calls["n"] == 2
    assert resp.meta.total_rows == 3


# ----------------------------------------------------------------------
# Validacao Pydantic dos args (ANTES de chegar ao gateway)
# ----------------------------------------------------------------------


def test_compare_args_rejects_invalid_iso3():
    with pytest.raises(ValueError):
        CompareArgs(indicator="GASTO_EDU_PIB", countries=["br"], year=2020)


def test_timeseries_args_rejects_inverted_years():
    with pytest.raises(ValueError):
        TimeseriesArgs(
            indicator="GASTO_EDU_PIB",
            country_iso3="BRA",
            year_start=2022,
            year_end=2018,
        )


def test_ranking_args_default_limit_20():
    args = RankingArgs(indicator="LITERACY_15M")
    assert args.limit == 20
    assert args.source == "worldbank"


def test_request_id_propagated():
    captured = {"rid": None}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["rid"] = request.headers.get("X-Request-ID")
        return httpx.Response(
            200, json={"data": [], "meta": {"total_rows": 0}}
        )

    transport = httpx.MockTransport(handler)
    with EduGatewayClient(transport=transport) as client:
        client.catalog(request_id="test-rid-123")
    assert captured["rid"] == "test-rid-123"
