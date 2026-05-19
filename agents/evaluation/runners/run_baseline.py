"""Runner BASELINE — pipeline RAG SEM guardrails (Fase 2).

Roda `master_flow.run_master(question, no_guardrails=True)` sobre
todos os itens do golden. Desativa:

- Retriever auto-populate (ADR 0006)
- Filtro de DOIs placeholder no Citation Agent
- Fact Checker pos-Synthesizer + retry (ADR 0007)

O JSON de saida e o **denominador** da TIA (itens HALLUCINATED no
baseline) e o **divisor** dos falsos positivos (itens CORRECT no
baseline que o EduQuery bloqueia indevidamente).

CLI:

    python -m evaluation.runners.run_baseline \\
        --golden agents/evaluation/golden \\
        --output agents/evaluation/output/baseline.json \\
        --limit 5     # opcional
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from evaluation.shared.loader import load_golden
from evaluation.shared.runner import execute


def run(golden_dir: Path, output: Path, *, limit: int | None = None) -> None:
    items = load_golden(golden_dir)
    execute(
        items,
        mode="baseline",
        no_guardrails=True,
        output=output,
        limit=limit,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="EduQuery — baseline RAG sem guardrails."
    )
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    run(args.golden, args.output, limit=args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
