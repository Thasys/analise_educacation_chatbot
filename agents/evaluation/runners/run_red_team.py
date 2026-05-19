"""Runner RED TEAM — foco em `adversarial.yaml`.

STATUS: Fase 1 = stub. Implementacao real na Fase 2.

Para cada item adversarial, verifica se o pipeline (com guardrails
ON) exibiu o `expected_behavior` declarado (block / refuse /
scope_disclaimer / ignore_injection / etc.). Produz breakdown por
categoria.

CLI:

    python -m agents.evaluation.runners.run_red_team \\
        --golden agents/evaluation/golden/adversarial.yaml \\
        --output agents/evaluation/output/redteam.json \\
        --limit 5
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def run(
    adversarial_yaml: Path,
    output: Path,
    *,
    limit: int | None = None,
) -> None:
    """Executa o conjunto adversarial sobre o pipeline EduQuery.

    Raises:
        NotImplementedError: stub Fase 1.
    """
    # TODO(fase2): carregar adversarial.yaml.
    # TODO(fase2): para cada item, invocar master_flow.run_master(query).
    # TODO(fase2): mapear resposta -> classificacao adversarial:
    #              - resposta bloqueada e expected_behavior in BLOCKING -> sucesso
    #              - resposta passou e expected_behavior in BLOCKING -> falha
    # TODO(fase2): agrupar por categoria; salvar JSON.
    raise NotImplementedError(
        "run_red_team.py: stub Fase 1. Implementar na Fase 2."
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="EduQuery — red teaming sobre adversarial.yaml (Fase 2)."
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
