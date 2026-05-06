"""Visualization tools — geracao de specs Plotly a partir dos dados.

Produzimos figure dicts validos para Plotly.js (campos `data`, `layout`).
O frontend Next.js (Fase 6) renderiza via `react-plotly.js` sem
transformacao adicional.

Templates suportados nesta sprint:
  - bar_horizontal: ranking de N paises em UM indicador.
  - bar_vertical: comparacao discreta de poucos paises.
  - line_multi: serie temporal (1 pais multi-fonte OU multi-pais 1 fonte).

Cores: paleta consistente com tema do CLAUDE.md
("ribbed" — neutros + destaque BR em vermelho terra-cota).
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, ClassVar, Literal

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


# ----------------------------------------------------------------------
# Paleta
# ----------------------------------------------------------------------

COLOR_BR = "#c0392b"          # destaque Brasil (terracota)
COLOR_OECD = "#2c3e50"        # azul escuro neutro
COLOR_NEUTRAL = "#7f8c8d"     # cinza para demais
COLOR_PALETTE = [
    "#2c3e50", "#16a085", "#8e44ad", "#d35400",
    "#27ae60", "#2980b9", "#c0392b", "#f39c12",
]


def _color_for(country_iso3: str, default: str = COLOR_NEUTRAL) -> str:
    if country_iso3 == "BRA":
        return COLOR_BR
    return default


# ----------------------------------------------------------------------
# Helpers puros — geram figure dicts
# ----------------------------------------------------------------------


def make_plotly_bar_horizontal(
    rows: list[dict[str, Any]],
    *,
    value_field: str = "value",
    label_field: str = "country_iso3",
    title: str = "",
    x_axis_title: str = "",
    sort_descending: bool = True,
) -> dict[str, Any]:
    """Bar horizontal: paises no eixo Y, valores no X. Brasil destacado.

    Aceita `rows` como lista de dicts. Ordena pelo `value_field` se
    `sort_descending`.
    """
    if not rows:
        return _empty_figure(title or "Sem dados")
    items = [r for r in rows if r.get(value_field) is not None]
    items.sort(key=lambda r: r[value_field], reverse=sort_descending)
    labels = [str(r.get(label_field, "?")) for r in items]
    values = [float(r[value_field]) for r in items]
    colors = [_color_for(label) for label in labels]
    return {
        "data": [
            {
                "type": "bar",
                "orientation": "h",
                "x": values,
                "y": labels,
                "marker": {"color": colors},
                "hovertemplate": "%{y}: %{x:.2f}<extra></extra>",
            }
        ],
        "layout": {
            "title": {"text": title},
            "xaxis": {"title": {"text": x_axis_title}, "zeroline": True},
            "yaxis": {"automargin": True, "autorange": "reversed"},
            "margin": {"l": 80, "r": 30, "t": 60, "b": 60},
            "showlegend": False,
        },
    }


def make_plotly_bar_vertical(
    rows: list[dict[str, Any]],
    *,
    value_field: str = "value",
    label_field: str = "country_iso3",
    title: str = "",
    y_axis_title: str = "",
) -> dict[str, Any]:
    """Bar vertical para comparacoes discretas (3-8 paises)."""
    if not rows:
        return _empty_figure(title or "Sem dados")
    items = [r for r in rows if r.get(value_field) is not None]
    labels = [str(r.get(label_field, "?")) for r in items]
    values = [float(r[value_field]) for r in items]
    colors = [_color_for(label) for label in labels]
    return {
        "data": [
            {
                "type": "bar",
                "x": labels,
                "y": values,
                "marker": {"color": colors},
                "hovertemplate": "%{x}: %{y:.2f}<extra></extra>",
            }
        ],
        "layout": {
            "title": {"text": title},
            "xaxis": {"title": {"text": ""}},
            "yaxis": {"title": {"text": y_axis_title}},
            "margin": {"l": 60, "r": 30, "t": 60, "b": 60},
            "showlegend": False,
        },
    }


def make_plotly_line_multi(
    rows: list[dict[str, Any]],
    *,
    value_field: str = "value",
    x_field: str = "year",
    series_field: str = "source",
    title: str = "",
    y_axis_title: str = "",
) -> dict[str, Any]:
    """Line chart multi-serie. Cada valor distinto de `series_field`
    vira uma linha (ex.: 1 linha por fonte ou 1 por pais).
    """
    if not rows:
        return _empty_figure(title or "Sem dados")
    series: dict[str, list[tuple[Any, float]]] = defaultdict(list)
    for r in rows:
        if r.get(value_field) is None:
            continue
        key = str(r.get(series_field, "?"))
        series[key].append((r.get(x_field), float(r[value_field])))
    traces = []
    for i, (name, points) in enumerate(sorted(series.items())):
        points.sort(key=lambda p: p[0])
        x_vals = [p[0] for p in points]
        y_vals = [p[1] for p in points]
        color = _color_for(name) if name == "BRA" else COLOR_PALETTE[i % len(COLOR_PALETTE)]
        traces.append(
            {
                "type": "scatter",
                "mode": "lines+markers",
                "name": name,
                "x": x_vals,
                "y": y_vals,
                "line": {"color": color, "width": 2},
                "marker": {"size": 6},
                "hovertemplate": f"{name} %{{x}}: %{{y:.2f}}<extra></extra>",
            }
        )
    return {
        "data": traces,
        "layout": {
            "title": {"text": title},
            "xaxis": {"title": {"text": x_field}, "tickformat": "d"},
            "yaxis": {"title": {"text": y_axis_title}},
            "legend": {"orientation": "h", "y": -0.2},
            "margin": {"l": 60, "r": 30, "t": 60, "b": 80},
        },
    }


def _empty_figure(title: str) -> dict[str, Any]:
    return {
        "data": [],
        "layout": {
            "title": {"text": title},
            "annotations": [
                {
                    "text": "Nenhum dado disponivel.",
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "font": {"size": 14, "color": "#7f8c8d"},
                }
            ],
        },
    }


# ----------------------------------------------------------------------
# Tool CrewAI
# ----------------------------------------------------------------------


class MakePlotlySpecArgs(BaseModel):
    """Argumentos da MakePlotlySpecTool."""

    chart_type: Literal["bar_horizontal", "bar_vertical", "line_multi"] = Field(
        ..., description="Template de chart a aplicar."
    )
    rows: list[dict[str, Any]] = Field(
        ..., description="Linhas de dados (cada dict tem value_field + label_field)."
    )
    title: str = Field(default="", max_length=200)
    value_field: str = Field(default="value")
    label_field: str = Field(default="country_iso3")
    x_field: str = Field(
        default="year", description="Apenas para line_multi: campo do eixo X."
    )
    series_field: str = Field(
        default="source",
        description="Apenas para line_multi: campo que separa series.",
    )
    axis_title: str = Field(default="", description="Titulo do eixo de valores.")


class MakePlotlySpecTool(BaseTool):
    """Gera figure dict Plotly a partir de rows + chart_type."""

    name: str = "make_plotly_spec"
    description: str = (
        "Gera um Plotly figure dict (data + layout) a partir de uma lista "
        "de rows. Templates: bar_horizontal (ranking N paises), "
        "bar_vertical (comparacao discreta), line_multi (serie temporal "
        "multi-fonte ou multi-pais). Brasil eh destacado em vermelho "
        "terra-cota automaticamente."
    )
    args_schema: type[BaseModel] = MakePlotlySpecArgs

    _client_override: ClassVar[None] = None

    def run(self, *args: Any, **kwargs: Any) -> Any:
        try:
            return super().run(*args, **kwargs)
        except ValueError as exc:
            return json.dumps(
                {"ok": False, "error": {"error_type": "validation", "message": str(exc)}}
            )

    def _run(
        self,
        chart_type: str,
        rows: list[dict[str, Any]],
        title: str = "",
        value_field: str = "value",
        label_field: str = "country_iso3",
        x_field: str = "year",
        series_field: str = "source",
        axis_title: str = "",
    ) -> str:
        if chart_type == "bar_horizontal":
            fig = make_plotly_bar_horizontal(
                rows,
                value_field=value_field,
                label_field=label_field,
                title=title,
                x_axis_title=axis_title,
            )
        elif chart_type == "bar_vertical":
            fig = make_plotly_bar_vertical(
                rows,
                value_field=value_field,
                label_field=label_field,
                title=title,
                y_axis_title=axis_title,
            )
        elif chart_type == "line_multi":
            fig = make_plotly_line_multi(
                rows,
                value_field=value_field,
                x_field=x_field,
                series_field=series_field,
                title=title,
                y_axis_title=axis_title,
            )
        else:
            return json.dumps(
                {"ok": False, "error": {"error_type": "validation",
                                         "message": f"chart_type desconhecido: {chart_type}"}}
            )
        return json.dumps({"ok": True, "chart_type": chart_type, "plotly_figure": fig})
