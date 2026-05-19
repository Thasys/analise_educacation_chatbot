"""Runner BASELINE — pipeline RAG SEM guardrails.

STATUS: Fase 1 = stub. Implementacao real na Fase 2 (apos autorizacao).

O baseline e o denominador da TIA: rodamos o mesmo conjunto de golden
sobre o pipeline SEM Fact Checker e SEM auto-populate do Retriever
(ADRs 0006 e 0007 documentam estes guardrails). A diferenca de
classificacao entre baseline e eduquery e a interceptacao.

Plano de implementacao (Fase 2):

1. Carregar YAMLs de `--golden`.
2. Para cada item:
   - Invocar `master_flow.run_master(query=item.query, no_guardrails=True)`
     (a flag `no_guardrails` ainda nao existe; refactor minimo deve
     adicionar — discutir com autor antes).
   - Extrair valor numerico da resposta (regex semelhante ao
     `check_numeric_consistency`).
   - Comparar com `expected_value` -> classificar via
     `hallucination_classifier.classify_response`.
3. Serializar resultados em JSON na pasta `--output`.

CLI:

    python -m agents.evaluation.runners.run_baseline \\
        --golden agents/evaluation/golden \\
        --output agents/evaluation/output/baseline.json \\
        --limit 5    # opcional: sanity check
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def run(
    golden_dir: Path,
    output: Path,
    *,
    limit: int | None = None,
) -> None:
    """Executa o pipeline baseline sobre todos os itens do golden.

    Raises:
        NotImplementedError: Fase 1 deixa apenas o stub e a CLI.
    """
    # TODO(fase2): carregar YAMLs via `_load_golden(golden_dir)`.
    # TODO(fase2): para cada item, chamar master_flow com guardrails OFF.
    # TODO(fase2): classificar resposta e salvar JSON em `output`.
    raise NotImplementedError(
        "run_baseline.py: stub Fase 1. Implementar na Fase 2 com "
        "autorizacao explicita (vide docs/evaluation/prompt-execucao-completo.md)."
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="EduQuery — baseline RAG sem guardrails (Fase 2)."
    )
    parser.add_argument(
        "--golden",
        type=Path,
        required=True,
        help="Diretorio com YAMLs de golden datasets.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Arquivo JSON de saida com classificacoes por item.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Quantidade maxima de itens (sanity check).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    run(args.golden, args.output, limit=args.limit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
