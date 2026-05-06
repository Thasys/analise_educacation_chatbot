"""Sprint 5.4 — testes de viz_tools (helpers + MakePlotlySpecTool)."""

from __future__ import annotations

import json

import pytest

from src.tools import (
    MakePlotlySpecTool,
    make_plotly_bar_horizontal,
    make_plotly_bar_vertical,
    make_plotly_line_multi,
)
from src.tools.viz_tools import COLOR_BR


# ----------------------------------------------------------------------
# Helpers puros — bar horizontal
# ----------------------------------------------------------------------


def test_bar_horizontal_destaca_brasil():
    rows = [
        {"country_iso3": "FIN", "value": 6.68},
        {"country_iso3": "BRA", "value": 5.77},
        {"country_iso3": "MEX", "value": 4.50},
    ]
    fig = make_plotly_bar_horizontal(rows, title="Gasto 2020")
    assert fig["data"][0]["type"] == "bar"
    assert fig["data"][0]["orientation"] == "h"
    # Sorted desc -> FIN, BRA, MEX
    assert fig["data"][0]["y"] == ["FIN", "BRA", "MEX"]
    colors = fig["data"][0]["marker"]["color"]
    bra_idx = fig["data"][0]["y"].index("BRA")
    assert colors[bra_idx] == COLOR_BR
    assert fig["layout"]["title"]["text"] == "Gasto 2020"


def test_bar_horizontal_empty_rows():
    fig = make_plotly_bar_horizontal([], title="Vazio")
    assert fig["data"] == []
    assert fig["layout"]["title"]["text"] == "Vazio"


def test_bar_horizontal_filters_null_values():
    rows = [
        {"country_iso3": "BRA", "value": 5.77},
        {"country_iso3": "URY", "value": None},
    ]
    fig = make_plotly_bar_horizontal(rows)
    assert fig["data"][0]["y"] == ["BRA"]


# ----------------------------------------------------------------------
# Helpers puros — bar vertical
# ----------------------------------------------------------------------


def test_bar_vertical_basico():
    rows = [
        {"country_iso3": "BRA", "value": 5.77},
        {"country_iso3": "FIN", "value": 6.68},
    ]
    fig = make_plotly_bar_vertical(rows, title="Comparacao")
    assert fig["data"][0]["x"] == ["BRA", "FIN"]
    assert fig["data"][0]["y"] == [5.77, 6.68]
    bra_idx = fig["data"][0]["x"].index("BRA")
    assert fig["data"][0]["marker"]["color"][bra_idx] == COLOR_BR


# ----------------------------------------------------------------------
# Helpers puros — line multi
# ----------------------------------------------------------------------


def test_line_multi_uma_serie():
    rows = [
        {"year": 2018, "source": "worldbank", "value": 6.09},
        {"year": 2019, "source": "worldbank", "value": 5.87},
        {"year": 2020, "source": "worldbank", "value": 5.77},
    ]
    fig = make_plotly_line_multi(rows, title="Evolucao BR")
    assert len(fig["data"]) == 1
    assert fig["data"][0]["name"] == "worldbank"
    assert fig["data"][0]["x"] == [2018, 2019, 2020]
    assert fig["data"][0]["y"] == [6.09, 5.87, 5.77]


def test_line_multi_duas_series():
    rows = [
        {"year": 2018, "source": "worldbank", "value": 6.09},
        {"year": 2018, "source": "unesco", "value": 5.91},
        {"year": 2019, "source": "worldbank", "value": 5.87},
        {"year": 2019, "source": "unesco", "value": 5.80},
    ]
    fig = make_plotly_line_multi(rows)
    assert len(fig["data"]) == 2
    names = sorted(t["name"] for t in fig["data"])
    assert names == ["unesco", "worldbank"]


def test_line_multi_empty():
    fig = make_plotly_line_multi([], title="Vazio")
    assert fig["data"] == []


# ----------------------------------------------------------------------
# MakePlotlySpecTool
# ----------------------------------------------------------------------


def test_tool_bar_horizontal():
    tool = MakePlotlySpecTool()
    raw = tool.run(
        chart_type="bar_horizontal",
        rows=[
            {"country_iso3": "BRA", "value": 5.77},
            {"country_iso3": "FIN", "value": 6.68},
        ],
        title="Gasto",
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["chart_type"] == "bar_horizontal"
    assert payload["plotly_figure"]["data"][0]["type"] == "bar"


def test_tool_line_multi():
    tool = MakePlotlySpecTool()
    raw = tool.run(
        chart_type="line_multi",
        rows=[
            {"year": 2020, "source": "worldbank", "value": 5.77},
            {"year": 2021, "source": "worldbank", "value": 5.65},
        ],
        title="Evolucao",
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["plotly_figure"]["data"][0]["mode"] == "lines+markers"


def test_tool_invalid_chart_type():
    tool = MakePlotlySpecTool()
    raw = tool.run(chart_type="pizza", rows=[{"country_iso3": "BRA", "value": 5}])
    payload = json.loads(raw)
    assert payload["ok"] is False
    assert payload["error"]["error_type"] == "validation"


def test_tool_validation_missing_required():
    tool = MakePlotlySpecTool()
    raw = tool.run(chart_type="bar_horizontal")  # rows missing
    payload = json.loads(raw)
    assert payload["ok"] is False
    assert payload["error"]["error_type"] == "validation"
