"""Runner RED TEAM — foco em `adversarial.yaml` (Fase 2).

Roda o pipeline com guardrails ON sobre o conjunto adversarial. Para
cada item, classifica se o `expected_behavior` (block / refuse /
scope_disclaimer / ignore_injection / ...) foi cumprido.

CLI:

    python -m evaluation.runners.run_red_team \\
        --golden agents/evaluation/golden/adversarial.yaml \\
        --output agents/evaluation/output/redteam.json \\
        --limit 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from evaluation.shared.loader import load_adversarial
from evaluation.shared.runner import execute


def run(
    adversarial_yaml: Path,
    output: Path,
    *,
    limit: int | None = None,
) -> None:
    items = load_adversarial(adversarial_yaml)
    execute(
        items,
        mode="red_team",
        no_guardrails=False,
        output=output,
        limit=limit,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="EduQuery — red teaming sobre adversarial.yaml."
    )
    parser.add_argument("--golden", type=Path, required=True, dest="adversarial_yaml")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    run(args.adversarial_yaml, args.output, limit=args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
