"""Runner EDUQUERY — pipeline completo (com guardrails) (Fase 2).

Diferenca em relacao a `run_baseline.py`: executa o pipeline com Fact
Checker e auto-populate do Retriever ativos (caminho de producao).
E o numerador da TIA (itens BLOCKED aqui que estavam HALLUCINATED no
baseline).

CLI:

    python -m evaluation.runners.run_eduquery \\
        --golden agents/evaluation/golden \\
        --output agents/evaluation/output/eduquery.json \\
        --limit 5
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
        mode="eduquery",
        no_guardrails=False,
        output=output,
        limit=limit,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="EduQuery — pipeline completo com guardrails."
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
