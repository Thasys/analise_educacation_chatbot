"""Testes do endpoint POST /api/data/ranking."""

from __future__ import annotations


def test_ranking_oecd_gasto_returns_top_n(client) -> None:
    r = client.post(
        "/api/data/ranking",
        json={
            "indicator": "GASTO_EDU_PIB",
            "grouping": "oecd",
            "source": "worldbank",
            "limit": 5,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total_rows"] == 5
    # rank deve ser sequencial 1..5
    ranks = [row["rank"] for row in body["data"]]
    assert ranks == [1, 2, 3, 4, 5]
    # Ordenacao decrescente por valor
    values = [row["value"] for row in body["data"]]
    assert values == sorted(values, reverse=True)
    # Heuristica de ano: pegou o ano mais coberto, nao um sparse
    year_used = body["meta"]["extra"]["year_used"]
    total = body["meta"]["extra"]["total_in_grouping"]
    assert year_used >= 2018
    assert total >= 20


def test_ranking_latam_alfab_recente(client) -> None:
    r = client.post(
        "/api/data/ranking",
        json={
            "indicator": "LITERACY_15M",
            "year": 2020,
            "grouping": "latam",
            "source": "unesco",
            "limit": 3,
        },
    )
    assert r.status_code == 200
    body = r.json()
    iso3s = [row["country_iso3"] for row in body["data"]]
    # ARG e URY devem estar no topo (literacy >99%)
    assert "ARG" in iso3s
    assert "URY" in iso3s


def test_ranking_unknown_combination_returns_404(client) -> None:
    """Combinacao indicador+fonte+grouping sem dados deve dar 404."""
    r = client.post(
        "/api/data/ranking",
        json={
            "indicator": "GASTO_EDU_PIB",
            "grouping": "africa_mena",
            "source": "ipea",  # IPEA so tem BRA
            "limit": 5,
        },
    )
    assert r.status_code == 404


def test_ranking_limit_out_of_range_returns_422(client) -> None:
    r = client.post(
        "/api/data/ranking",
        json={
            "indicator": "GASTO_EDU_PIB",
            "grouping": "oecd",
            "source": "worldbank",
            "limit": 9999,  # > 200
        },
    )
    assert r.status_code == 422
