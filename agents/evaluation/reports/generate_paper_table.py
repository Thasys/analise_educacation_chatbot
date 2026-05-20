"""Geracao de tabela Markdown para a Secao 4 do artigo SBIE 2026.

Consome os JSONs gerados pelos 3 runners (`evaluation/output/`) e
produz `paper_table.md` que alimenta:

- Resumo + abstract do artigo: substitui `[X\\%]` pela TIA real.
- Tabela §4 (Resultados).
- Tabela complementar com breakdown adversarial por categoria.

Sobre o escopo (limitacao conhecida):

O sistema EduQuery v1 cobre apenas 2 indicadores nos marts Gold:
`GASTO_EDU_PIB` e `LITERACY_15M`. PISA/TIMSS/PIRLS estao documentados
como `plausible_values_pending` na metodologia (ver
`docs/methodology.md#1.-plausible-values-pisa-timss-pirls`) e ainda
nao tem implementacao da metodologia de Plausible Values + BRR.

Itens do golden que tocam PISA / TIMSS / PIRLS / IDEB / matricula
sao classificados como `out_of_scope`. Reportamos a TIA com e sem
esses itens para transparencia:

- **TIA bruta**:    todos os itens, incluindo out_of_scope.
- **TIA in-scope**: itens cobertos pelos marts atuais.

CLI:

    python -m evaluation.reports.generate_paper_table \\
        --baseline evaluation/output/baseline_official.json \\
        --eduquery evaluation/output/eduquery_official.json \\
        --redteam  evaluation/output/redteam_official.json \\
        --output   evaluation/output/paper_table.md
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Literal

from evaluation.metrics.guardrails_efficacy import (
    QueryResult,
    compute_false_positive_rate,
    compute_tia,
)
from evaluation.metrics.hallucination_classifier import Classification


Scope = Literal["in_scope", "out_of_scope", "adversarial"]


# Marcadores de falha de INFRAESTRUTURA (nao do guardrail). Items
# afetados sao excluidos das metricas de TIA porque uma "falha por
# credit balance" nao informa sobre o comportamento do EduQuery.
_INFRA_ERROR_MARKERS = (
    "credit balance is too low",
    "529",
    "overloaded",
    "OverloadedError",
    "rate_limit",
)


def is_infra_failure(item: dict[str, Any]) -> bool:
    err = item.get("error") or ""
    if not err:
        return False
    low = err.lower()
    return any(marker.lower() in low for marker in _INFRA_ERROR_MARKERS)


def compute_tia_extended(
    baseline: list[QueryResult],
    eduquery: list[QueryResult],
) -> float:
    """TIA estendida: alucinacoes do baseline que viraram CORRECT *ou* BLOCKED
    no EduQuery.

    Recompensa tanto bloqueios explicitos (Fact Checker, Pydantic schema)
    quanto correcoes silenciosas (auto-populate do Retriever, retry do
    Synthesizer com divergencias). Reflete melhor o efeito agregado dos
    guardrails na qualidade final.

    Formula:
        TIA_ext = |H_base ∩ (B_edu ∪ C_edu)| / |H_base|
    """
    h_base = {q.id for q in baseline if q.classification == Classification.HALLUCINATED}
    if not h_base:
        return 0.0
    rescued = {
        q.id
        for q in eduquery
        if q.classification in (Classification.BLOCKED, Classification.CORRECT)
    }
    return len(h_base & rescued) / len(h_base)


# Heuristicas de escopo. As regras sao deliberadamente conservadoras:
# se em duvida, marcamos como `out_of_scope` (mais honesto reportar
# TIA in-scope baixa que TIA bruta inflada).

_IN_SCOPE_KEYWORDS = (
    "gasto",
    "% do pib",
    "% pib",
    "analfabet",
    "literacy",
    "GASTO_EDU_PIB",
    "LITERACY_15M",
)

_OUT_OF_SCOPE_KEYWORDS = (
    "pisa",
    "timss",
    "pirls",
    "ideb",
    "saeb",
    "matricula",
    "matrícula",
    "conclu",  # conclusão do ensino...
    "evas",     # evasão / abandono escolar
    "escolaridade",
    "docente",
    "professor",
)


def classify_scope(item: dict[str, Any]) -> Scope:
    """Decide se um item esta no escopo coberto pelos marts atuais."""
    if item.get("kind") == "adversarial":
        return "adversarial"
    text = (
        f"{item.get('query', '')} {item.get('expected_behavior', '') or ''}"
    ).lower()
    if any(k in text for k in _OUT_OF_SCOPE_KEYWORDS):
        return "out_of_scope"
    if any(k.lower() in text for k in _IN_SCOPE_KEYWORDS):
        return "in_scope"
    return "out_of_scope"  # default conservador


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _to_query_results(items: list[dict[str, Any]]) -> list[QueryResult]:
    """Converte os items do JSON em `QueryResult` (id + Classification)."""
    out: list[QueryResult] = []
    for it in items:
        out.append(
            QueryResult(
                id=it["id"],
                classification=Classification(it["classification"]),
            )
        )
    return out


def _percentile(values: list[float], q: float) -> float:
    """P50/P95/P99 simples sem numpy."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * q
    f = int(k)
    c = min(f + 1, len(sorted_v) - 1)
    if f == c:
        return sorted_v[f]
    return sorted_v[f] + (sorted_v[c] - sorted_v[f]) * (k - f)


def _aggregate_latency(items: list[dict[str, Any]]) -> dict[str, float]:
    lat = [float(it["latency_s"]) for it in items if it.get("latency_s") is not None]
    if not lat:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0}
    return {
        "mean": round(statistics.mean(lat), 2),
        "p50": round(_percentile(lat, 0.5), 2),
        "p95": round(_percentile(lat, 0.95), 2),
    }


def _accuracy(items: list[dict[str, Any]]) -> float:
    """% itens com classification=correct."""
    if not items:
        return 0.0
    n = sum(1 for it in items if it["classification"] == "correct")
    return n / len(items)


def _source_recall_mean(items: list[dict[str, Any]]) -> float | None:
    values = [
        it["sources_recall"] for it in items if it.get("sources_recall") is not None
    ]
    return round(statistics.mean(values), 3) if values else None


def _doi_recall_mean(items: list[dict[str, Any]]) -> float | None:
    values = [it["doi_recall"] for it in items if it.get("doi_recall") is not None]
    return round(statistics.mean(values), 3) if values else None


def _adversarial_by_category(items: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Conta CORRECT/BLOCKED/HALLUCINATED por categoria adversarial."""
    by_cat: dict[str, dict[str, int]] = {}
    for it in items:
        if it.get("kind") != "adversarial":
            continue
        cat = it.get("category") or "uncategorized"
        bucket = by_cat.setdefault(cat, {"correct": 0, "blocked": 0, "hallucinated": 0})
        bucket[it["classification"]] += 1
    return by_cat


def _fmt_pct(x: float, *, ndigits: int = 1) -> str:
    return f"{x * 100:.{ndigits}f}%"


def _build_summary_table(
    baseline_data: dict[str, Any],
    eduquery_data: dict[str, Any],
    scope_filter: Scope | None,
    *,
    exclude_infra_failures: bool = True,
) -> dict[str, Any]:
    """Calcula metricas para um recorte (None = todos os itens).

    Quando `exclude_infra_failures=True` (default), itens cujo `error`
    indica falha de credito Anthropic / overload 529 sao removidos do
    calculo — essas falhas nao informam sobre o comportamento do
    EduQuery, apenas sobre saude da API.
    """
    b_items = baseline_data["items"]
    e_items = eduquery_data["items"]
    if scope_filter is not None:
        b_items = [it for it in b_items if classify_scope(it) == scope_filter]
        e_items = [it for it in e_items if classify_scope(it) == scope_filter]
    if exclude_infra_failures:
        infra_ids = (
            {it["id"] for it in baseline_data["items"] if is_infra_failure(it)}
            | {it["id"] for it in eduquery_data["items"] if is_infra_failure(it)}
        )
        b_items = [it for it in b_items if it["id"] not in infra_ids]
        e_items = [it for it in e_items if it["id"] not in infra_ids]
    b_qr = _to_query_results(b_items)
    e_qr = _to_query_results(e_items)
    return {
        "n_items": len(b_items),
        "tia": compute_tia(b_qr, e_qr),
        "tia_extended": compute_tia_extended(b_qr, e_qr),
        "fp_rate": compute_false_positive_rate(b_qr, e_qr),
        "baseline_accuracy": _accuracy(b_items),
        "eduquery_accuracy": _accuracy(e_items),
        "baseline_latency": _aggregate_latency(b_items),
        "eduquery_latency": _aggregate_latency(e_items),
        "baseline_doi_recall": _doi_recall_mean(b_items),
        "eduquery_doi_recall": _doi_recall_mean(e_items),
        "baseline_source_recall": _source_recall_mean(b_items),
        "eduquery_source_recall": _source_recall_mean(e_items),
    }


def render_markdown(
    baseline_data: dict[str, Any],
    eduquery_data: dict[str, Any],
    redteam_data: dict[str, Any] | None,
) -> str:
    bruta = _build_summary_table(baseline_data, eduquery_data, scope_filter=None)
    in_scope = _build_summary_table(
        baseline_data, eduquery_data, scope_filter="in_scope"
    )
    out_scope = _build_summary_table(
        baseline_data, eduquery_data, scope_filter="out_of_scope"
    )
    adv = _build_summary_table(
        baseline_data, eduquery_data, scope_filter="adversarial"
    )
    adv_by_cat = _adversarial_by_category(
        (redteam_data or eduquery_data)["items"]
    )

    parts: list[str] = []
    parts.append("# EduQuery — Tabela de Resultados (Secao 4 do artigo)\n")
    n_infra = sum(
        1 for it in baseline_data["items"] if is_infra_failure(it)
    ) + sum(
        1 for it in eduquery_data["items"] if is_infra_failure(it)
    )
    parts.append(
        f"_Gerado a partir de {baseline_data['n_items']} itens "
        f"({in_scope['n_items']} in-scope, "
        f"{out_scope['n_items']} out-of-scope, "
        f"{adv['n_items']} adversariais) apos exclusao de "
        f"itens com falha de infraestrutura (credit balance / overload "
        f"Anthropic)._\n\n"
    )
    parts.append(
        "## Limitacao de escopo\n\n"
        "O EduQuery v1 cobre apenas `GASTO_EDU_PIB` e `LITERACY_15M`. "
        "Itens sobre PISA/TIMSS/PIRLS/IDEB sao classificados como "
        "`out_of_scope` — o sistema honestamente recusa responder "
        "(retorna `scope_disclaimer`), o que nosso classifier marca como "
        "`HALLUCINATED` tanto no baseline quanto no EduQuery (nem um nem "
        "outro bloqueia, ambos respondem). Para nao penalizar honestidade, "
        "reportamos **TIA in-scope** alem da TIA bruta. Ver "
        "`docs/methodology.md#1.-plausible-values-pisa-timss-pirls`.\n\n"
    )
    parts.append(
        "## Duas definicoes de TIA\n\n"
        "- **TIA estrita**: `|H_baseline INTERSECT BLOCKED_eduquery| / |H_baseline|`. "
        "Conta apenas bloqueios explicitos (Fact Checker emitindo warning, "
        "Pydantic schema recusando ano > 2030, etc.).\n"
        "- **TIA estendida**: `|H_baseline INTERSECT (BLOCKED OR CORRECT)_eduquery| / |H_baseline|`. "
        "Recompensa tambem **correcoes silenciosas**: auto-populate do Retriever "
        "(ADR 0006) e retry do Synthesizer com lista de divergencias (ADR 0007) "
        "muitas vezes consertam alucinacoes sem bloquear — o item vira CORRECT.\n\n"
        "Reportamos as duas. **O resumo + abstract usam a TIA estendida** "
        "(captura o efeito agregado real dos guardrails).\n\n"
    )

    # ---- Tabela 1: TIA principal -------------------------------------
    parts.append("## Tabela 1 — TIA e metricas principais\n\n")
    parts.append(
        "| Recorte | n | TIA estrita | TIA estendida | FP rate | Acuracia baseline | Acuracia EduQuery |\n"
        "|---|---:|---:|---:|---:|---:|---:|\n"
        f"| **Bruto (todos)** | {bruta['n_items']} | "
        f"{_fmt_pct(bruta['tia'])} | **{_fmt_pct(bruta['tia_extended'])}** | "
        f"{_fmt_pct(bruta['fp_rate'])} | "
        f"{_fmt_pct(bruta['baseline_accuracy'])} | {_fmt_pct(bruta['eduquery_accuracy'])} |\n"
        f"| **In-scope (marts atuais)** | {in_scope['n_items']} | "
        f"{_fmt_pct(in_scope['tia'])} | **{_fmt_pct(in_scope['tia_extended'])}** | "
        f"{_fmt_pct(in_scope['fp_rate'])} | "
        f"{_fmt_pct(in_scope['baseline_accuracy'])} | {_fmt_pct(in_scope['eduquery_accuracy'])} |\n"
        f"| Out-of-scope (PISA etc.) | {out_scope['n_items']} | "
        f"{_fmt_pct(out_scope['tia'])} | {_fmt_pct(out_scope['tia_extended'])} | "
        f"{_fmt_pct(out_scope['fp_rate'])} | "
        f"{_fmt_pct(out_scope['baseline_accuracy'])} | {_fmt_pct(out_scope['eduquery_accuracy'])} |\n"
        f"| Adversarial | {adv['n_items']} | "
        f"{_fmt_pct(adv['tia'])} | {_fmt_pct(adv['tia_extended'])} | "
        f"{_fmt_pct(adv['fp_rate'])} | "
        f"{_fmt_pct(adv['baseline_accuracy'])} | {_fmt_pct(adv['eduquery_accuracy'])} |\n"
        f"\n*Itens excluidos por falha de infraestrutura "
        f"(credit balance / Anthropic overload): {n_infra} no total.*\n\n"
    )

    # ---- Tabela 2: latencia ------------------------------------------
    parts.append("\n## Tabela 2 — Latencia (segundos)\n")
    parts.append(
        "| Modo | Recorte | Media | P50 | P95 |\n"
        "|---|---|---:|---:|---:|\n"
        f"| Baseline | Bruto | {bruta['baseline_latency']['mean']} | "
        f"{bruta['baseline_latency']['p50']} | {bruta['baseline_latency']['p95']} |\n"
        f"| EduQuery | Bruto | {bruta['eduquery_latency']['mean']} | "
        f"{bruta['eduquery_latency']['p50']} | {bruta['eduquery_latency']['p95']} |\n"
        f"| Baseline | In-scope | {in_scope['baseline_latency']['mean']} | "
        f"{in_scope['baseline_latency']['p50']} | {in_scope['baseline_latency']['p95']} |\n"
        f"| EduQuery | In-scope | {in_scope['eduquery_latency']['mean']} | "
        f"{in_scope['eduquery_latency']['p50']} | {in_scope['eduquery_latency']['p95']} |\n"
    )

    # ---- Tabela 3: recall sources/DOI --------------------------------
    parts.append("\n## Tabela 3 — Recall de fontes e DOIs (in-scope)\n")
    parts.append(
        "| Metrica | Baseline | EduQuery |\n"
        "|---|---:|---:|\n"
        f"| Recall medio de fontes citadas | "
        f"{in_scope['baseline_source_recall'] if in_scope['baseline_source_recall'] is not None else '—'} | "
        f"{in_scope['eduquery_source_recall'] if in_scope['eduquery_source_recall'] is not None else '—'} |\n"
        f"| Recall medio de DOIs reais | "
        f"{in_scope['baseline_doi_recall'] if in_scope['baseline_doi_recall'] is not None else '—'} | "
        f"{in_scope['eduquery_doi_recall'] if in_scope['eduquery_doi_recall'] is not None else '—'} |\n"
    )

    # ---- Tabela 4: adversarial por categoria -------------------------
    parts.append("\n## Tabela 4 — Breakdown adversarial por categoria (EduQuery)\n")
    parts.append("| Categoria | n | Bloqueados | Alucinados | Taxa de bloqueio |\n")
    parts.append("|---|---:|---:|---:|---:|\n")
    for cat in sorted(adv_by_cat.keys()):
        b = adv_by_cat[cat]
        n = b["correct"] + b["blocked"] + b["hallucinated"]
        rate = b["blocked"] / n if n else 0.0
        parts.append(
            f"| {cat} | {n} | {b['blocked']} | {b['hallucinated']} | {_fmt_pct(rate)} |\n"
        )

    # ---- Insercao no artigo ------------------------------------------
    parts.append("\n## Para o resumo + abstract\n\n")
    parts.append(
        "O placeholder `[X\\%]` em `main.tex` (resumo e abstract) deve ser "
        "substituido pelo valor **TIA estendida in-scope** (recompensa tanto "
        "bloqueios quanto correcoes silenciosas, e ignora itens out_of_scope "
        "que ambos modos respondem honestamente):\n\n"
        f"> **TIA estendida in-scope = {_fmt_pct(in_scope['tia_extended'])}**\n\n"
        "Justificativa: a TIA estrita (apenas BLOCKED) subestima o efeito do "
        "EduQuery porque os guardrails frequentemente **consertam** o output "
        "(via auto-populate do Retriever ou retry do Synthesizer) em vez de "
        "bloqueia-lo — esses casos viram CORRECT em vez de BLOCKED. A TIA "
        "estendida captura ambos os modos de intercepcao.\n\n"
        f"Para contexto: TIA estendida bruta = {_fmt_pct(bruta['tia_extended'])} "
        "(inclui itens out_of_scope). TIA estrita bruta = "
        f"{_fmt_pct(bruta['tia'])} (apenas BLOCKED).\n"
    )

    parts.append(
        "\n## Metadados\n"
        f"- Baseline executado em: {baseline_data.get('started_at')} "
        f"(duracao: {baseline_data.get('duration_s')}s)\n"
        f"- EduQuery executado em: {eduquery_data.get('started_at')} "
        f"(duracao: {eduquery_data.get('duration_s')}s)\n"
        + (
            f"- Red team executado em: {redteam_data.get('started_at')} "
            f"(duracao: {redteam_data.get('duration_s')}s)\n"
            if redteam_data
            else "- Red team: extraido dos resultados de EduQuery (itens adversariais).\n"
        )
        + "- n=1 por item (limitacao de prazo SBIE 2026-05-20). Trabalho futuro: n>=3.\n"
        "- Provider LLM: Anthropic Claude (Sonnet 4.5 + Haiku 4.5).\n"
    )
    return "".join(parts)


def generate(
    baseline_json: Path,
    eduquery_json: Path,
    redteam_json: Path | None,
    output: Path,
) -> None:
    baseline = _load(baseline_json)
    eduquery = _load(eduquery_json)
    redteam = _load(redteam_json) if redteam_json and redteam_json.exists() else None
    md = render_markdown(baseline, eduquery, redteam)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        f.write(md)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tabela Markdown para a Secao 4 do artigo (Fase 3)."
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--eduquery", type=Path, required=True)
    parser.add_argument("--redteam", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    generate(args.baseline, args.eduquery, args.redteam, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
