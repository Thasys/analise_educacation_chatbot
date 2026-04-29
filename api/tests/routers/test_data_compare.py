"""Testes do endpoint POST /api/data/compare."""

from __future__ import annotations


def test_compare_3_countries_gasto_returns_data_and_stats(client) -> None:
    r = client.post(
        "/api/data/compare",
        json={
            "indicator": "GASTO_EDU_PIB",
            "countries": ["BRA", "FIN", "USA"],
            "year": 2020,
            "source": "worldbank",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total_rows"] == 3
    stats = body["meta"]["extra"]["comparison_stats"]
    assert stats["countries_with_data"] == 3
    assert stats["min"] < stats["max"]
    iso3s = {row["country_iso3"] for row in body["data"]}
    assert iso3s == {"BRA", "FIN", "USA"}


def test_compare_invalid_country_in_list_returns_422(client) -> None:
    r = client.post(
        "/api/data/compare",
        json={
            "indicator": "GASTO_EDU_PIB",
            "countries": ["BRA", "FI"],  # FI tem 2 letras
            "year": 2020,
            "source": "worldbank",
        },
    )
    assert r.status_code == 422


def test_compare_year_out_of_range_returns_422(client) -> None:
    r = client.post(
        "/api/data/compare",
        json={
            "indicator": "GASTO_EDU_PIB",
            "countries": ["BRA"],
            "year": 1800,
            "source": "worldbank",
        },
    )
    assert r.status_code == 422


def test_compare_empty_countries_returns_422(client) -> None:
    r = client.post(
        "/api/data/compare",
        json={
            "indicator": "GASTO_EDU_PIB",
            "countries": [],
            "year": 2020,
            "source": "worldbank",
        },
    )
    assert r.status_code == 422
