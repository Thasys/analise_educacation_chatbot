"""Runner LLM-DIRETO sem RAG — terceira coluna do baseline.

Implementa a Acao #4 das orientacoes_metodologicas
(2026-05-21, Secao 6): "Adicionar coluna de comparacao: LLM direto
sem RAG (Haiku, prompt direto) nos 10 itens in-scope. Ancora o
baseline em algo reproduzivel pelo revisor."

Diferenca em relacao a `run_baseline.py`:
- `run_baseline.py` desliga guardrails MAS mantem todo o pipeline
  CrewAI (Retriever, Statistician, Synthesizer, Citation). E um
  baseline COM RAG mas sem guardrails.
- `run_llm_direct.py` chama o LLM DIRETAMENTE com a query do golden,
  sem CrewAI, sem marts, sem RAG. E o piso absoluto de qualidade —
  o que o LLM sabe "de cabeca" sem qualquer infraestrutura de dados.

CLI:
    python -m evaluation.runners.run_llm_direct \\
        --golden evaluation/golden \\
        --output evaluation/output/llm_direct.json \\
        --limit 10              # apenas in-scope ate Fase 1 da F7
        --model claude-haiku-4-5-20251001
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from evaluation.metrics.hallucination_classifier import (
    Classification,
    ResponseUnderTest,
    classify_response,
)
from evaluation.shared.loader import GoldenItem, load_golden
from evaluation.shared.parser import best_match, extract_numbers
from evaluation.reports.generate_paper_table import classify_scope


logger = logging.getLogger(__name__)


# Pricing Haiku 4.5 (estimativa).
_HAIKU_INPUT_PER_MTOK_USD = 0.80
_HAIKU_OUTPUT_PER_MTOK_USD = 4.00


_PROMPT_TEMPLATE = """Voce e um assistente de pesquisa em educacao comparada. Responda \
a pergunta abaixo de forma direta e factual, com o valor numerico se aplicavel.

Pergunta: {query}

Forneca a resposta de forma objetiva. Se nao souber, diga claramente que nao tem o dado."""


def _direct_call(query: str, *, model: str) -> tuple[str | None, dict, str | None]:
    """Faz chamada direta ao Anthropic. Retorna (text, usage, error)."""
    try:
        import anthropic  # type: ignore[import-not-found]
    except ImportError as e:
        return None, {}, f"anthropic_sdk_missing: {e}"

    client = anthropic.Anthropic()
    prompt = _PROMPT_TEMPLATE.format(query=query)
    try:
        resp = client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:  # noqa: BLE001
        return None, {}, str(e)

    text = resp.content[0].text if resp.content else ""
    usage = {
        "input_tokens": getattr(resp.usage, "input_tokens", 0) if resp.usage else 0,
        "output_tokens": getattr(resp.usage, "output_tokens", 0) if resp.usage else 0,
    }
    return text, usage, None


def _classify_item(item: GoldenItem, markdown: str) -> tuple[Classification, float | None]:
    if item.kind not in ("factual", "comparative"):
        return Classification.HALLUCINATED, None
    expected = (
        item.expected_value if item.kind == "factual" else item.expected_brazil
    )
    if expected is None:
        return Classification.HALLUCINATED, None
    numbers = extract_numbers(markdown)
    actual = best_match(numbers, expected, tolerance_pct=item.tolerance_pct)
    resp = ResponseUnderTest(
        item_id=item.id,
        actual_value=actual,
        expected_value=expected,
        tolerance_pct=item.tolerance_pct,
        blocked=False,
        expected_behavior=None,
    )
    return classify_response(resp), actual


def run(
    golden_dir: Path,
    output: Path,
    *,
    only_in_scope: bool = True,
    limit: int | None = None,
    model: str = "claude-haiku-4-5-20251001",
) -> dict:
    items = load_golden(golden_dir)
    if only_in_scope:
        items = [
            it for it in items
            if it.kind in ("factual", "comparative")
            and classify_scope({
                "kind": it.kind,
                "query": it.query,
                "expected_behavior": it.expected_behavior,
            }) == "in_scope"
        ]
    if limit is not None:
        items = items[:limit]

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    results = []
    total_cost = 0.0

    for i, item in enumerate(items, 1):
        item_t0 = time.perf_counter()
        markdown, usage, error = _direct_call(item.query, model=model)
        item_latency = time.perf_counter() - item_t0

        cost = (
            usage.get("input_tokens", 0) / 1_000_000 * _HAIKU_INPUT_PER_MTOK_USD
            + usage.get("output_tokens", 0) / 1_000_000 * _HAIKU_OUTPUT_PER_MTOK_USD
        )
        total_cost += cost

        cls, actual = _classify_item(item, markdown or "")
        record = {
            "id": item.id,
            "kind": item.kind,
            "query": item.query,
            "expected_value": item.expected_value if item.kind == "factual" else item.expected_brazil,
            "actual_value": actual,
            "tolerance_pct": item.tolerance_pct,
            "classification": cls.value,
            "latency_s": round(item_latency, 3),
            "markdown": markdown or "",
            "cost_usd": round(cost, 5),
            "usage": usage,
            "error": error,
        }
        results.append(record)
        print(
            f"[{i}/{len(items)}] {item.id} class={cls.value} "
            f"actual={actual} cost=${cost:.4f}"
        )

    payload = {
        "mode": "llm_direct",
        "model": model,
        "started_at": started_at,
        "duration_s": round(time.perf_counter() - t0, 2),
        "n_items": len(results),
        "total_cost_usd": round(total_cost, 5),
        "items": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTotal: {len(results)} itens, custo total ${total_cost:.4f}")
    print(f"Salvo em: {output}")
    return payload


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Baseline LLM-direto: chama Haiku/Sonnet diretamente sem CrewAI nem marts."
    )
    p.add_argument("--golden", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--model", default="claude-haiku-4-5-20251001")
    p.add_argument("--all-items", action="store_true",
                   help="Roda em todos os items (nao so in-scope).")
    args = p.parse_args(argv)
    run(args.golden, args.output, only_in_scope=not args.all_items,
        limit=args.limit, model=args.model)
    return 0


if __name__ == "__main__":
    sys.exit(main())
