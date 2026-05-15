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

Atualizado 2026-05-14 (DRY #10 + QW1 do quality assessment):

- Funcao paramétrica `_build_figure` extrai o pipeline comum aos 3
  templates (filter null, sort, extract labels/values, montar trace).
  Os 3 `make_plotly_*` viram thin wrappers — eliminando duplicacao e
  garantindo que LLM nunca toque em arrays de numeros (MP2).
- `_validate_figure` valida tipos antes do dict sair: arrays de numero
  precisam ser `list`, nao string serializada. Causa raiz documentada no
  quality-assessment 2026-05-14 secao 2.1 ("LLM emitiu y como string").
"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field

from src.tools._base import SafeTool


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
# Pipeline parametrico compartilhado (#10 do DRY pass)
# ----------------------------------------------------------------------


def _extract_xy(
    rows: list[dict[str, Any]],
    *,
    value_field: str,
    label_field: str,
    sort_descending: bool = False,
) -> tuple[list[str], list[float], list[str]]:
    """Filtra rows com valor not-null, extrai (labels, values, colors).

    Helper compartilhado pelos 3 templates de figure. Retorna 3 listas
    paralelas: labels (str), values (float) e colors (str hex). Brasil
    fica em terracota quando aparece como label.
    """
    items = [r for r in rows if r.get(value_field) is not None]
    if sort_descending:
        items.sort(key=lambda r: r[value_field], reverse=True)
    labels = [str(r.get(label_field, "?")) for r in items]
    values = [float(r[value_field]) for r in items]
    colors = [_color_for(label) for label in labels]
    return labels, values, colors


def _validate_figure(fig: dict[str, Any]) -> str | None:
    """Valida que arrays de numeros sao listas (nao strings serializadas).

    Implementa QW1 do quality-assessment 2026-05-14: o LLM as vezes emite
    `"y": "[4.7, 5.2, 6.8]"` (string Python literal) em vez de
    `"y": [4.7, 5.2, 6.8]` (lista JSON). Plotly.js nao renderiza no
    primeiro caso. Aqui devolvemos uma mensagem de erro nao-vazia para
    `SafeTool.run` converter em `_validation_error_payload`.

    Retorna None se OK, mensagem se invalido.
    """
    data = fig.get("data")
    if not isinstance(data, list):
        return "figure.data deve ser lista (recebeu " + type(data).__name__ + ")"
    for i, trace in enumerate(data):
        if not isinstance(trace, dict):
            return f"figure.data[{i}] deve ser dict"
        for axis in ("x", "y"):
            val = trace.get(axis)
            if val is None:
                continue
            if not isinstance(val, list):
                return (
                    f"figure.data[{i}].{axis} deve ser lista de "
                    f"numero/string (recebeu {type(val).__name__})"
                )
    return None


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
    labels, values, colors = _extract_xy(
        rows,
        value_field=value_field,
        label_field=label_field,
        sort_descending=sort_descending,
    )
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
    labels, values, colors = _extract_xy(
        rows, value_field=value_field, label_field=label_field
    )
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
    title: str = Field(default="")
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


class MakePlotlySpecTool(SafeTool):
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
        # QW1: valida tipos antes de devolver. Se algum array vier como
        # string, devolve erro estruturado em vez de figure quebrado.
        err = _validate_figure(fig)
        if err:
            return json.dumps(
                {"ok": False, "error": {"error_type": "validation", "message": err}}
            )
        return json.dumps({"ok": True, "chart_type": chart_type, "plotly_figure": fig})
