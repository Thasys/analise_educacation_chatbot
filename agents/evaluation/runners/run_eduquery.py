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


def run(
    golden_dir: Path,
    output: Path,
    *,
    limit: int | None = None,
    repetitions: int = 1,
    in_scope_only: bool = False,
) -> None:
    items = load_golden(golden_dir)
    execute(
        items,
        mode="eduquery",
        no_guardrails=False,
        output=output,
        limit=limit,
        repetitions=repetitions,
        in_scope_only=in_scope_only,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="EduQuery — pipeline completo com guardrails."
    )
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--repetitions", type=int, default=1,
                        help="N>1 repete cada item N vezes (F8 — n=3).")
    parser.add_argument("--in-scope-only", action="store_true",
                        help="Filtra apenas itens in_scope (cobertos pelos marts).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    run(args.golden, args.output, limit=args.limit,
        repetitions=args.repetitions, in_scope_only=args.in_scope_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
