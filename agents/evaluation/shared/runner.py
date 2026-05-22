"""Core de execucao da bateria — laco compartilhado pelos 3 runners.

Cada runner (`run_baseline.py`, `run_eduquery.py`, `run_red_team.py`)
e thin: parseia CLI, decide o subconjunto de itens, e delega aqui.

Saida JSON estavel (consumida por `reports/generate_paper_table.py`):

    {
        "mode": "baseline" | "eduquery" | "red_team",
        "started_at": "2026-05-19T14:32:00Z",
        "duration_s": 1234.5,
        "n_items": 80,
        "items": [
            {
                "id": "F-001",
                "kind": "factual",
                "query": "...",
                "expected_value": 379,
                "actual_value": 380.5 | null,
                "tolerance_pct": 5,
                "blocked": false,
                "expected_behavior": null | "block" | ...,
                "category": null | "doi_fishing" | ...,
                "classification": "correct" | "hallucinated" | "blocked",
                "latency_s": 12.34,
                "markdown": "...",
                "n_citations": 3,
                "warnings": [...],
                "sources_recall": 1.0 | null,
                "doi_recall": 1.0 | null,
                "error": null | "..."
            },
            ...
        ]
    }
"""

from __future__ import annotations

import json
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from evaluation.metrics.hallucination_classifier import (
    Classification,
    ResponseUnderTest,
    classify_response,
)
from evaluation.metrics.source_coverage import compute_source_recall
from evaluation.metrics.doi_validity import compute_doi_recall
from evaluation.shared.loader import GoldenItem
from evaluation.shared.parser import best_match, extract_numbers


log = structlog.get_logger(__name__)


def _extract_actual_value(markdown: str, item: GoldenItem) -> float | None:
    """Heuristica para tirar 1 numero da resposta, dado o `expected` do item."""
    numbers = extract_numbers(markdown)
    if item.kind == "factual" and item.expected_value is not None:
        return best_match(numbers, item.expected_value, tolerance_pct=item.tolerance_pct)
    if item.kind == "comparative" and item.expected_brazil is not None:
        return best_match(
            numbers, item.expected_brazil, tolerance_pct=item.tolerance_pct
        )
    # Adversariais sem expected_value: retorna o primeiro numero, util
    # apenas para diagnostico (a classificacao depende de `blocked`).
    return numbers[0] if numbers else None


def _classify(item: GoldenItem, *, actual: float | None, blocked: bool) -> Classification:
    expected = item.expected_value
    if item.kind == "comparative":
        expected = item.expected_brazil
    return classify_response(
        ResponseUnderTest(
            item_id=item.id,
            actual_value=actual,
            expected_value=expected,
            tolerance_pct=item.tolerance_pct,
            blocked=blocked,
            expected_behavior=item.expected_behavior,
        )
    )


_BLOCKING_BEHAVIORS = frozenset(
    {
        "block",
        "block_or_disclaim",
        "block_figure",
        "refuse",
        "scope_disclaimer",
        "ignore_injection",
    }
)


def _detect_blocked(final: Any, warnings: list[str]) -> bool:
    """Heuristica para detectar bloqueio pelo guardrail no FinalAnswer.

    Em EduQuery, o Fact Checker NAO levanta excecao — ele adiciona um
    `warning` ao FinalAnswer dizendo "Fact-check: N valores no markdown
    nao correspondem ao dado real". A presenca desse warning conta
    como "bloqueado" para a TIA: o sistema sinalizou ao usuario que
    a resposta tem numeros divergentes.

    No baseline (no_guardrails=True), esse warning nunca aparece;
    `blocked` sera sempre False.
    """
    for w in warnings:
        if "fact-check" in w.lower():
            return True
    return False


def _is_error_a_block(error: str | None, item: GoldenItem) -> bool:
    """Erros de validacao Pydantic / pipeline failure contam como bloqueio
    quando o item adversarial esperava bloqueio.

    Caso concreto: item A-001 ("PISA 2050") faz o Pydantic do schema de
    entities recusar `year=2050` (constraint `le=2030`). O pipeline aborta;
    o sistema NAO inventou um numero. Para a TIA, isso e interceptacao
    valida quando o expected_behavior pedia block.
    """
    if not error:
        return False
    if item.expected_behavior not in _BLOCKING_BEHAVIORS:
        return False
    # Validacao Pydantic, ValueError de schema, ou recusa explicita em log.
    error_lower = error.lower()
    return any(
        marker in error_lower
        for marker in (
            "validationerror",
            "should be less than",
            "should be greater than",
            "input should be",
            "less_than_equal",
            "greater_than_equal",
        )
    )


def _safe_run_master(
    question: str,
    *,
    no_guardrails: bool,
    gateway_client: Any | None,
    rag_client: Any | None,
) -> tuple[Any | None, str | None]:
    """Invoca `run_master` capturando erros sem derrubar o laco."""
    from src.crews.master_flow import run_master  # import tardio: cara

    try:
        return run_master(
            question,
            gateway_client=gateway_client,
            rag_client=rag_client,
            no_guardrails=no_guardrails,
        ), None
    except Exception:  # noqa: BLE001
        return None, traceback.format_exc(limit=8)


def execute(
    items: list[GoldenItem],
    *,
    mode: str,
    no_guardrails: bool,
    output: Path,
    limit: int | None = None,
    gateway_client: Any | None = None,
    rag_client: Any | None = None,
    use_cache: bool = True,
    repetitions: int = 1,
    in_scope_only: bool = False,
) -> dict[str, Any]:
    """Roda a bateria sobre `items` e persiste JSON em `output`.

    Args:
        items: lista de `GoldenItem` (factuais + comparativos +
            adversariais ou subconjunto).
        mode: rotulo do run ("baseline", "eduquery", "red_team").
        no_guardrails: True para baseline; False para EduQuery e
            red_team.
        output: caminho do JSON de saida.
        limit: se nao None, processa apenas os primeiros N itens
            (sanity check / dry-run).
        gateway_client, rag_client: opcionais; se None, defaults.

    Returns:
        O dict que foi serializado em `output`.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()

    # in_scope_only filter (F8 — n=3 sobre os 10 in-scope).
    if in_scope_only:
        from evaluation.reports.generate_paper_table import classify_scope

        items = [
            it for it in items
            if it.kind in ("factual", "comparative")
            and classify_scope({
                "kind": it.kind,
                "query": it.query,
                "expected_behavior": it.expected_behavior,
            }) == "in_scope"
        ]
    subset = items[:limit] if limit is not None else items

    # Repetitions: para n>1, replicamos cada item com sufixo `_rN` no id.
    if repetitions > 1:
        expanded = []
        for r in range(1, repetitions + 1):
            for it in subset:
                # Wrap leve para mudar o id (e desabilitar cache).
                expanded.append((it, r))
        subset_with_rep = expanded
        use_cache = False  # repetitions exigem chamadas independentes
    else:
        subset_with_rep = [(it, 1) for it in subset]

    # Cache setup (F6 do plano pos-orientacao 2026-05-21).
    import os

    cache_mod = None
    cache_key_fn = None
    if use_cache:
        from evaluation.shared import cache as cache_mod  # noqa: F811
        cache_key_fn = lambda q: cache_mod.cache_key(  # noqa: E731
            q, mode=mode,
            model_smart=os.environ.get("AGENTS_LLM_SMART_MODEL", "default"),
            model_fast=os.environ.get("AGENTS_LLM_FAST_MODEL", "default"),
        )

    log.info(
        "evaluation.runner.start",
        mode=mode,
        no_guardrails=no_guardrails,
        n_items=len(subset_with_rep),
        n_unique=len(subset),
        repetitions=repetitions,
        output=str(output),
        use_cache=use_cache,
    )

    results: list[dict[str, Any]] = []
    n_cache_hits = 0
    for i, (item, rep_idx) in enumerate(subset_with_rep, 1):
        # ---- Cache hit? ----
        if use_cache and cache_key_fn is not None:
            key = cache_key_fn(item.query)
            cached = cache_mod.get(output.parent, key)
            if cached is not None:
                results.append(cached)
                n_cache_hits += 1
                log.info(
                    "evaluation.runner.cache_hit",
                    mode=mode, i=i, of=len(subset), id=item.id, key=key,
                )
                continue

        item_t0 = time.perf_counter()
        final, error = _safe_run_master(
            item.query,
            no_guardrails=no_guardrails,
            gateway_client=gateway_client,
            rag_client=rag_client,
        )
        item_latency = time.perf_counter() - item_t0

        if final is None:
            actual: float | None = None
            markdown = ""
            warnings: list[str] = []
            n_citations = 0
            sources_recall = None
            doi_recall = None
            # Pipeline failure: se o item adversarial esperava bloqueio
            # e o erro veio da validacao Pydantic (ex.: ano fora do range),
            # consideramos isso bloqueio valido. Caso contrario, alucinacao
            # (falha tecnica sem motivo de seguranca).
            if _is_error_a_block(error, item):
                blocked = True
                classification = Classification.BLOCKED
            else:
                blocked = False
                classification = Classification.HALLUCINATED
        else:
            markdown = final.markdown or ""
            warnings = list(getattr(final, "warnings", []) or [])
            blocked = _detect_blocked(final, warnings) if not no_guardrails else False
            actual = _extract_actual_value(markdown, item)
            classification = _classify(item, actual=actual, blocked=blocked)
            n_citations = len(getattr(final, "citations", []) or [])
            sources_recall = (
                compute_source_recall(markdown, item.sources_required)
                if item.sources_required else None
            )
            cited_dois = [
                c.doi for c in (getattr(final, "citations", []) or []) if getattr(c, "doi", None)
            ]
            expected_dois = [item.doi] if item.doi else []
            doi_recall = (
                compute_doi_recall(cited_dois, expected_dois)
                if expected_dois else None
            )

        record = {
            "id": item.id if repetitions == 1 else f"{item.id}_r{rep_idx}",
            "base_id": item.id,
            "repetition_idx": rep_idx,
            "kind": item.kind,
            "query": item.query,
            "expected_value": item.expected_value if item.kind == "factual" else item.expected_brazil,
            "actual_value": actual,
            "tolerance_pct": item.tolerance_pct,
            "blocked": blocked,
            "expected_behavior": item.expected_behavior,
            "category": item.category,
            "classification": classification.value,
            "latency_s": round(item_latency, 3),
            "markdown": markdown,
            "n_citations": n_citations,
            "warnings": warnings,
            "sources_recall": sources_recall,
            "doi_recall": doi_recall,
            "error": error,
        }
        results.append(record)
        if use_cache and cache_mod is not None and cache_key_fn is not None:
            cache_mod.put(output.parent, cache_key_fn(item.query), record)
        log.info(
            "evaluation.runner.item_done",
            mode=mode,
            i=i,
            of=len(subset_with_rep),
            id=item.id,
            rep=rep_idx,
            classification=classification.value,
            latency_s=round(item_latency, 2),
        )

    duration_s = time.perf_counter() - t0
    payload = {
        "mode": mode,
        "no_guardrails": no_guardrails,
        "started_at": started_at,
        "duration_s": round(duration_s, 2),
        "n_items": len(results),
        "n_cache_hits": n_cache_hits,
        "items": results,
    }
    with output.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info(
        "evaluation.runner.done",
        mode=mode,
        n_items=len(results),
        duration_s=round(duration_s, 1),
        output=str(output),
    )
    return payload
