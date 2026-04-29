"""Testes do endpoint POST /api/data/timeseries."""

from __future__ import annotations


def test_timeseries_bra_gasto_returns_multiple_sources(client) -> None:
    r = client.post(
        "/api/data/timeseries",
        json={
            "indicator": "GASTO_EDU_PIB",
            "country_iso3": "BRA",
            "year_start": 2018,
            "year_end": 2022,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total_rows"] > 0
    sources = set(body["meta"]["sources"])
    assert {"worldbank", "unesco"}.issubset(sources)


def test_timeseries_filter_by_source_subset(client) -> None:
    r = client.post(
        "/api/data/timeseries",
        json={
            "indicator": "GASTO_EDU_PIB",
            "country_iso3": "BRA",
            "year_start": 2020,
            "year_end": 2022,
            "sources": ["worldbank"],
        },
    )
    assert r.status_code == 200
    sources = {row["source"] for row in r.json()["data"]}
    assert sources == {"worldbank"}


def test_timeseries_invalid_indicator_returns_422(client) -> None:
    r = client.post(
        "/api/data/timeseries",
        json={
            "indicator": "INVALID_INDICATOR",
            "country_iso3": "BRA",
            "year_start": 2018,
            "year_end": 2020,
        },
    )
    assert r.status_code == 422


def test_timeseries_invalid_country_iso3_returns_422(client) -> None:
    r = client.post(
        "/api/data/timeseries",
        json={
            "indicator": "GASTO_EDU_PIB",
            "country_iso3": "br",  # lowercase nao bate com pattern ^[A-Z]{3}$
            "year_start": 2018,
            "year_end": 2020,
        },
    )
    assert r.status_code == 422


def test_timeseries_year_end_before_start_returns_422(client) -> None:
    r = client.post(
        "/api/data/timeseries",
        json={
            "indicator": "GASTO_EDU_PIB",
            "country_iso3": "BRA",
            "year_start": 2020,
            "year_end": 2015,  # invalido
        },
    )
    assert r.status_code == 422


def test_timeseries_country_with_no_data_returns_empty_with_note(client) -> None:
    """ZZZ nao existe -- response 200, data=[], notes preenchido."""
    r = client.post(
        "/api/data/timeseries",
        json={
            "indicator": "GASTO_EDU_PIB",
            "country_iso3": "ZZZ",
            "year_start": 2018,
            "year_end": 2020,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["data"] == []
    assert body["meta"]["total_rows"] == 0
    assert body["meta"]["notes"] is not None
