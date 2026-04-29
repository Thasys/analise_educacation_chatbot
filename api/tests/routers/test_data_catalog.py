"""Testes do endpoint GET /api/data/catalog."""

from __future__ import annotations


def test_catalog_returns_list_of_marts(client) -> None:
    r = client.get("/api/data/catalog")
    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["total_rows"] >= 5  # 5 marts publicados


def test_catalog_includes_known_marts(client) -> None:
    r = client.get("/api/data/catalog")
    names = {item["name"] for item in r.json()["data"]}
    assert "mart_br_vs_ocde__gasto_educacao_timeseries" in names
    assert "mart_alfabetizacao__latam_2020s" in names
    assert "mart_indicadores__rankings_recente" in names


def test_catalog_items_have_row_count(client) -> None:
    r = client.get("/api/data/catalog")
    for item in r.json()["data"]:
        assert "row_count" in item
        assert item["row_count"] > 0
        assert "tags" in item


def test_catalog_returns_request_id_header(client) -> None:
    r = client.get("/api/data/catalog")
    assert "X-Request-ID" in r.headers
    assert len(r.headers["X-Request-ID"]) > 10  # UUID-ish
