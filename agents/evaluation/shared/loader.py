"""Carga + validacao dos YAMLs de golden.

Schema de cada item esta documentado no cabecalho dos YAMLs em
`agents/evaluation/golden/`. Aqui materializamos uma dataclass minima
para evitar `dict[str, Any]` espalhado pelos runners.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml


GoldenKind = Literal["factual", "comparative", "adversarial"]


@dataclass
class GoldenItem:
    """Item normalizado do golden dataset.

    Campos vazios/None significam "nao aplicavel para esta variante"
    (ex.: itens adversariais raramente tem `expected_value`).
    """

    id: str
    kind: GoldenKind
    query: str

    # Factual / comparativo
    expected_value: float | None = None
    expected_brazil: float | None = None
    expected_oecd_avg: float | None = None
    expected_other: dict[str, float] = field(default_factory=dict)
    tolerance_pct: float = 5.0
    unit: str | None = None

    # Fontes esperadas (lista de tags canonicas)
    sources_required: list[str] = field(default_factory=list)
    primary_source: str | None = None
    doi: str | None = None

    # Adversarial
    category: str | None = None
    expected_behavior: str | None = None
    guardrail_expected: str | None = None
    reason: str | None = None
    inject_malformed_figure: bool = False
    context_hint: str | None = None
    # TCC (orientacoes_metodologicas 2026-05-21)
    verification_method: str = "semantic"
    acceptance_criteria: dict = field(default_factory=dict)

    # Metadata
    notes: str | None = None
    verified: bool = False
    bloom_level: str | None = None  # remember | understand | analyze | ...


def _load_yaml(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path}: esperava lista YAML, achou {type(data).__name__}")
    return data


def _build_factual(d: dict[str, Any]) -> GoldenItem:
    return GoldenItem(
        id=d["id"],
        kind="factual",
        query=d["query"],
        expected_value=d.get("expected_value"),
        tolerance_pct=float(d.get("tolerance_pct", 5.0)),
        unit=d.get("unit"),
        primary_source=d.get("primary_source"),
        doi=d.get("doi"),
        notes=d.get("notes"),
        verified=bool(d.get("_verified", False)),
        bloom_level=d.get("bloom_level"),
    )


def _build_comparative(d: dict[str, Any]) -> GoldenItem:
    expected_other_raw = d.get("expected_other") or {}
    expected_other: dict[str, float] = {}
    if isinstance(expected_other_raw, dict):
        for k, v in expected_other_raw.items():
            try:
                expected_other[str(k)] = float(v)
            except (TypeError, ValueError):
                continue
    return GoldenItem(
        id=d["id"],
        kind="comparative",
        query=d["query"],
        expected_brazil=d.get("expected_brazil"),
        expected_oecd_avg=d.get("expected_oecd_avg"),
        expected_other=expected_other,
        tolerance_pct=float(d.get("tolerance_pct", 5.0)),
        unit=d.get("unit"),
        sources_required=list(d.get("sources_required") or []),
        primary_source=d.get("primary_source"),
        notes=d.get("notes"),
        verified=bool(d.get("_verified", False)),
        bloom_level=d.get("bloom_level"),
    )


def _build_adversarial(d: dict[str, Any]) -> GoldenItem:
    return GoldenItem(
        id=d["id"],
        kind="adversarial",
        query=d["query"],
        category=d.get("category"),
        expected_behavior=d.get("expected_behavior"),
        guardrail_expected=d.get("guardrail_expected"),
        reason=d.get("reason"),
        inject_malformed_figure=bool(d.get("inject_malformed_figure", False)),
        context_hint=d.get("context_hint"),
        verification_method=str(d.get("verification_method") or "semantic"),
        acceptance_criteria=dict(d.get("acceptance_criteria") or {}),
    )


def load_golden(golden_dir: Path) -> list[GoldenItem]:
    """Carrega TODOS os YAMLs do diretorio (factuais + comparativos + adversariais)."""
    items: list[GoldenItem] = []
    for raw in _load_yaml(golden_dir / "queries_factuais.yaml"):
        items.append(_build_factual(raw))
    for raw in _load_yaml(golden_dir / "queries_comparativas.yaml"):
        items.append(_build_comparative(raw))
    for raw in _load_yaml(golden_dir / "adversarial.yaml"):
        items.append(_build_adversarial(raw))
    return items


def load_adversarial(adversarial_yaml: Path) -> list[GoldenItem]:
    """Carrega apenas o conjunto adversarial (usado por `run_red_team.py`)."""
    return [_build_adversarial(raw) for raw in _load_yaml(adversarial_yaml)]
