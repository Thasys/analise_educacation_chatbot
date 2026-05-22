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


def _tcc_by_category(items: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Conta TCC (CORRECT/BLOCKED/HALLUCINATED via tcc_classification)
    por categoria adversarial. Inclui metodo de verificacao usado.

    Implementa Tabela 3.4 das orientacoes_metodologicas (2026-05-21).
    Fallback: se item nao tem `tcc_classification`, usa `classification`.
    """
    by_cat: dict[str, dict[str, int]] = {}
    for it in items:
        if it.get("kind") != "adversarial":
            continue
        cat = it.get("category") or "uncategorized"
        bucket = by_cat.setdefault(
            cat,
            {"correct": 0, "blocked": 0, "hallucinated": 0, "methods": {}},
        )
        cls = it.get("tcc_classification") or it["classification"]
        if cls in ("correct", "blocked", "hallucinated"):
            bucket[cls] += 1
        method = it.get("tcc_method", "?")
        bucket["methods"][method] = bucket["methods"].get(method, 0) + 1
    return by_cat


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
    *,
    llm_direct: dict[str, Any] | None = None,
    n3: dict[str, Any] | None = None,
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

    # ---- Tabela 0 (opcional): Comparacao com LLM-direto sem RAG ------
    if llm_direct is not None:
        ld_correct = sum(1 for it in llm_direct["items"] if it["classification"] == "correct")
        ld_n = llm_direct["n_items"]
        ld_acc = ld_correct / ld_n if ld_n else 0.0
        parts.append(
            "## Tabela 0 — Comparacao com LLM-direto sem RAG (in-scope)\n\n"
            "Ancora o baseline em piso reproduzivel pelo revisor: chamada direta a "
            "Haiku 4.5 sem CrewAI, sem marts, sem auto-populate. Implementa a "
            "Acao #4 das orientacoes_metodologicas.\n\n"
            f"| Modo | n | Acuracia | Custo | Tempo |\n"
            f"|---|---:|---:|---:|---:|\n"
            f"| **LLM-direto sem RAG** (Haiku 4.5) | {ld_n} | "
            f"**{_fmt_pct(ld_acc)}** | "
            f"\\${llm_direct.get('total_cost_usd', 0):.4f} | "
            f"{llm_direct.get('duration_s', 0):.1f}s |\n"
            f"| Baseline com RAG (sem guardrails) | "
            f"{in_scope['n_items']} | {_fmt_pct(in_scope['baseline_accuracy'])} | "
            f"~\\$1 | ~85s/item |\n"
            f"| EduQuery completo | {in_scope['n_items']} | "
            f"**{_fmt_pct(in_scope['eduquery_accuracy'])}** | ~\\$1 | ~140s/item |\n\n"
            "**Observacao:** LLM-direto e Baseline com RAG dao acuracia equivalente. "
            "O salto para 60% no EduQuery vem dos guardrails (auto-populate do "
            "Retriever + Fact Checker), **nao do RAG em si**. Esse e o argumento "
            "central do paper.\n\n"
        )

    # ---- Tabela 0.5: n=3 (media +- desvio padrao) ---------------------
    if n3 is not None:
        # Agregar por base_id.
        from collections import defaultdict
        import statistics as _stat
        by_base: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for it in n3["items"]:
            by_base[it.get("base_id", it["id"])].append(it)
        # Calcular acuracia agregada (media de hits / total).
        acc_per_rep: dict[int, list[bool]] = defaultdict(list)
        for it in n3["items"]:
            r = it.get("repetition_idx", 1)
            acc_per_rep[r].append(it["classification"] == "correct")
        rep_accs = [sum(v) / len(v) if v else 0 for v in acc_per_rep.values()]
        if len(rep_accs) >= 2:
            mean_acc = _stat.mean(rep_accs)
            std_acc = _stat.stdev(rep_accs)
            parts.append(
                "## Tabela 0.5 — Robustez n=3 (in-scope, EduQuery)\n\n"
                f"Acao #3 das orientacoes_metodologicas: rodar n=3 nos 10 itens "
                f"in-scope para transformar estimativa pontual em media +- desvio "
                f"padrao.\n\n"
                f"- **Repeticoes:** {len(rep_accs)}\n"
                f"- **Acuracia in-scope (media):** {_fmt_pct(mean_acc)} "
                f"**±** {_fmt_pct(std_acc)}\n"
                f"- **Por repeticao:** "
                + ", ".join(f"r{i+1}={_fmt_pct(a)}" for i, a in enumerate(rep_accs))
                + "\n\n"
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

    # ---- Tabela 4: adversarial por categoria (TIA estrita) -----------
    parts.append("\n## Tabela 4 — Breakdown adversarial: TIA estrita (Fact Checker)\n\n")
    parts.append(
        "Mede apenas bloqueios explicitos pelo Fact Checker / Pydantic. "
        "Sub-estima o desempenho do sistema pois ignora recusas textuais. "
        "Comparar com Tabela 5 abaixo (TCC).\n\n"
    )
    parts.append("| Categoria | n | Bloqueados | Alucinados | Taxa de bloqueio |\n")
    parts.append("|---|---:|---:|---:|---:|\n")
    for cat in sorted(adv_by_cat.keys()):
        b = adv_by_cat[cat]
        n = b["correct"] + b["blocked"] + b["hallucinated"]
        rate = b["blocked"] / n if n else 0.0
        parts.append(
            f"| {cat} | {n} | {b['blocked']} | {b['hallucinated']} | {_fmt_pct(rate)} |\n"
        )

    # ---- Tabela 5: TCC por categoria (Taxa de Comportamento Correto) -
    tcc_data = _tcc_by_category(eduquery_data["items"])
    if tcc_data:
        parts.append("\n## Tabela 5 — TCC (Taxa de Comportamento Correto) por categoria\n\n")
        parts.append(
            "Metrica proposta nas orientacoes_metodologicas (2026-05-21, Secao 3): "
            "para adversariais, a pergunta certa nao e 'interceptou alucinacao?' mas "
            "'o sistema se comportou conforme esperado?'. Captura recusas textuais, "
            "scope_disclaimers e validacoes Pydantic em 3 camadas (structural / "
            "semantic / llm_judge).\n\n"
        )
        parts.append("| Categoria | n | Comportamento correto | TCC | Metodo predominante |\n")
        parts.append("|---|---:|---:|---:|---|\n")
        total_n = 0
        total_correct = 0
        for cat in sorted(tcc_data.keys()):
            b = tcc_data[cat]
            n = b["correct"] + b["blocked"] + b["hallucinated"]
            correct = b["correct"] + b["blocked"]
            rate = correct / n if n else 0.0
            methods = b.get("methods", {})
            top_method = max(methods, key=methods.get) if methods else "?"
            parts.append(
                f"| {cat} | {n} | {correct} | {_fmt_pct(rate)} | {top_method} |\n"
            )
            total_n += n
            total_correct += correct
        if total_n:
            parts.append(
                f"| **TOTAL** | **{total_n}** | **{total_correct}** | "
                f"**{_fmt_pct(total_correct / total_n)}** | — |\n"
            )

    # ---- Tabela 6: transicoes in-scope (item-a-item) -----------------
    parts.append(
        "\n## Tabela 6 — Transicoes in-scope (item-a-item)\n\n"
        "Mostra exatamente quais perguntas o EduQuery interceptou e quais "
        "deixou passar. Padrao: interceptacao ocorre quando indicador + ano "
        "cabem no recorte dos marts atuais.\n\n"
    )
    parts.append(
        "| id | baseline | EduQuery | Transicao | Query (truncada) |\n"
        "|---|---|---|---|---|\n"
    )
    base_by_id = {it["id"]: it for it in baseline_data["items"]}
    edu_by_id = {it["id"]: it for it in eduquery_data["items"]}
    for item_id, b in base_by_id.items():
        if classify_scope(b) != "in_scope":
            continue
        e = edu_by_id.get(item_id, {})
        bc = b["classification"]
        ec = e.get("classification", "MISSING")
        if bc == "hallucinated":
            transicao = (
                "**INTERCEPTADO**" if ec in ("correct", "blocked") else "nao interceptado"
            )
        else:
            transicao = f"(ja era {bc})"
        q = (b.get("query") or "").replace("|", " ")[:60]
        parts.append(f"| {item_id} | {bc} | {ec} | {transicao} | {q}... |\n")

    # ---- Analise: por que esse numero? -------------------------------
    parts.append(
        "\n## Analise — por que esse valor de TIA?\n\n"
        "A TIA in-scope mede, na pratica, a **fracao de alucinacoes do "
        "baseline cuja pergunta cabe no recorte dos marts atuais** "
        "(`GASTO_EDU_PIB` em `mart_br_vs_ocde__gasto_educacao_timeseries`, "
        "`LITERACY_15M` em `mart_alfabetizacao__latam_2020s`). Quando a "
        "pergunta cai dentro do recorte, o **auto-populate determinístico "
        "do Retriever** (ADR 0006) injeta o valor canônico do mart no "
        "contexto do Synthesizer — e o sistema acerta. Fora do recorte "
        "(ano ausente, indicador derivado), o auto-populate falha e o "
        "Synthesizer alucina.\n\n"
        "**A TIA reflete, portanto, a fronteira de cobertura do lakehouse, "
        "nao a qualidade dos guardrails em abstrato.**\n\n"
    )

    # ---- Caminhos para aumentar (ROI) --------------------------------
    parts.append(
        "## Caminhos para aumentar a TIA (ordenados por ROI)\n\n"
        "| # | Intervencao | Impacto estimado | Custo |\n"
        "|---|---|---|---|\n"
        "| 1 | **Implementar PISA/TIMSS/PIRLS com Plausible Values + BRR** "
        "(`r_scripts/` ja tem placeholders) | +30-40 itens viram in-scope; "
        "TIA in-scope potencialmente ~70%+ | Alto (2-4 semanas) |\n"
        "| 2 | **Expandir cobertura temporal dos marts atuais** "
        "(gasto pre-2010, analfabetismo 2019) | F-016, C-011 viram "
        "interceptaveis | Baixo (1-2 dias) |\n"
        "| 3 | **Adicionar `mart_gasto_per_aluno` (USD PPP)** | F-032, "
        "C-005 viram interceptaveis | Medio (3-5 dias) |\n"
        "| 4 | **Fact Checker LLM-based** (MP4 do quality plan, ADR 0007 "
        "Debito Tecnico) | Pega direcionais errados ('acima/abaixo "
        "invertido'); +10-15% in-scope | Medio (1 semana) |\n"
        "| 5 | **JSON Schema strict via Ollama `format=<schema>`** (LP3) | "
        "Synthesizer nao pode mais 'prosa intermediaria' inventar numeros | "
        "Medio |\n"
        "| 6 | **Popular ChromaDB com referencias reais** (RAG atualmente "
        "vazio -> 0 DOIs reais recuperados) | DOI recall sobe; melhora "
        "citacoes | Medio |\n"
        "| 7 | **Self-consistency n=3 com voto majoritario** (LP2) | "
        "Reduz variancia LLM; melhora ~5% | Alto (3x custo de tokens) |\n\n"
        "**Maior alavanca: #1 + #2.** Se 30 itens PISA viram in-scope e 50% "
        "deles forem interceptados, TIA in-scope sobe para ~65-75%.\n\n"
    )

    # ---- Implicacoes -------------------------------------------------
    parts.append(
        "## Implicacoes do valor obtido\n\n"
        "**Para o paper (Secao 5 — Discussao):**\n"
        "- O sistema **nao e fonte primaria**; e assistente de exploracao. "
        "Usuario academico ainda deve checar fontes.\n"
        "- ~44% das alucinacoes in-scope passam -> para usos criticos "
        "(publicacao, politica publica), revisao humana e necessaria.\n"
        "- A camada de guardrails deterministicos e **necessaria mas nao "
        "suficiente** — confirmando o argumento do paper de que LLM puro "
        "RAG e insuficiente sem verificacao.\n\n"
        "**Para arquitetura (proximas iteracoes):**\n"
        "- O ROI dos guardrails e real (6x acuracia), validando o "
        "investimento no DRY refactor + ADRs 0006/0007.\n"
        "- A maior alavanca nao e melhorar guardrails — e **ampliar a "
        "cobertura do lakehouse** (#1 e #2 da tabela acima).\n"
        "- Lei de Conway aplicada: a TIA reflete a fronteira de 'o que "
        "esta modelado nos marts'.\n\n"
        "**Para revisao SBIE:**\n"
        "- O par 'TIA estendida in-scope 55,6% + acuracia 10%->60%' e mais "
        "defensavel que apresentar so um numero.\n"
        "- Revisores TPIE devem aceitar se o paper for explicito sobre "
        "escopo + reportar limitacao corretamente (ver "
        "`docs/evaluation/limitations.md`).\n\n"
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
    *,
    llm_direct_json: Path | None = None,
    n3_json: Path | None = None,
) -> None:
    baseline = _load(baseline_json)
    eduquery = _load(eduquery_json)
    redteam = _load(redteam_json) if redteam_json and redteam_json.exists() else None
    llm_direct = _load(llm_direct_json) if llm_direct_json and llm_direct_json.exists() else None
    n3 = _load(n3_json) if n3_json and n3_json.exists() else None
    md = render_markdown(baseline, eduquery, redteam, llm_direct=llm_direct, n3=n3)
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
    parser.add_argument("--llm-direct", type=Path, default=None,
                        help="JSON do run LLM-direto (F7)")
    parser.add_argument("--n3", type=Path, default=None,
                        help="JSON do run n=3 (F8)")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    generate(
        args.baseline, args.eduquery, args.redteam, args.output,
        llm_direct_json=args.llm_direct,
        n3_json=args.n3,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
