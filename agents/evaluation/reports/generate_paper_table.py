"""Geracao de tabela Markdown para a Secao 4 do artigo.

STATUS: Fase 1 = stub. Implementacao real na Fase 3.

Consome os 3 JSONs gerados em `agents/evaluation/output/` e produz:

- `paper_table.md`: tabela com colunas Baseline | EduQuery | Delta
  para Acuracia, Recall DOI, FP, Latencia e TIA.
- Breakdown por categoria adversarial (tabela complementar).

Esses numeros substituem `[X\\%]` no `resumo` e `abstract` do
`main.tex` (repo do artigo).

CLI:

    python -m agents.evaluation.reports.generate_paper_table \\
        --baseline agents/evaluation/output/baseline.json \\
        --eduquery agents/evaluation/output/eduquery.json \\
        --redteam  agents/evaluation/output/redteam.json \\
        --output   agents/evaluation/output/paper_table.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def generate(
    baseline_json: Path,
    eduquery_json: Path,
    redteam_json: Path,
    output: Path,
) -> None:
    """Gera `paper_table.md` consolidando as 3 saidas dos runners.

    Raises:
        NotImplementedError: stub Fase 1.
    """
    # TODO(fase3): carregar os 3 JSONs.
    # TODO(fase3): calcular metricas via agents.evaluation.metrics.
    # TODO(fase3): formatar Markdown table (Acuracia | Recall DOI | FP | Latencia | TIA).
    # TODO(fase3): breakdown adversarial por categoria.
    raise NotImplementedError(
        "generate_paper_table.py: stub Fase 1. Implementar na Fase 3."
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tabela Markdown para a Secao 4 do artigo (Fase 3)."
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--eduquery", type=Path, required=True)
    parser.add_argument("--redteam", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    generate(args.baseline, args.eduquery, args.redteam, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
