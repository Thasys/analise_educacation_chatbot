"""CLI dev — `python -m src.cli "<pergunta>"`.

Ponto de entrada simples para validar o master_flow fora do frontend.
Imprime o markdown da resposta + sumario JSON de visualizacoes,
citacoes, fontes e warnings. Util para debugging local e para a suite
live (Sprint 5.6).

Uso:

    cd agents
    .venv/Scripts/python -m src.cli "Como BR se compara com FIN em gasto educacional 2022?"

Saida no stdout. Exit code 0 em sucesso, 1 em erro.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import structlog

from src.config import settings
from src.crews import run_master
from src.logging_config import configure_logging


log = structlog.get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.cli",
        description=(
            "Roda o master flow do sistema de agentes sobre uma pergunta "
            "em linguagem natural e imprime a resposta final."
        ),
    )
    parser.add_argument(
        "question",
        help="Pergunta em linguagem natural (use aspas se houver espacos).",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Imprime APENAS o JSON do FinalAnswer (sem markdown formatado).",
    )
    parser.add_argument(
        "--gateway",
        default=None,
        help=f"Override do gateway base URL (default: {settings.gateway_base_url}).",
    )
    return parser


def _print_final(final: Any, *, json_only: bool) -> None:
    if json_only:
        print(json.dumps(final.model_dump(), ensure_ascii=False, indent=2))
        return

    print()
    print("=" * 78)
    print(final.markdown)
    print("=" * 78)
    print()

    if final.citations:
        print("REFERENCIAS:")
        for c in final.citations:
            authors = ", ".join(c.authors[:3]) if c.authors else "?"
            doi = f" doi:{c.doi}" if c.doi else ""
            print(f"  - {authors} ({c.year}). {c.title}.{doi}")
        print()

    if final.visualizations:
        viz = final.visualizations[0]
        print(f"VISUALIZACAO: {viz.chart_type} — {viz.title}")
        print(f"  data points: {len(viz.plotly_figure.get('data', []))}")
        print(f"  sources:     {viz.sources}")
        print()

    if final.warnings:
        print("AVISOS:")
        for w in final.warnings:
            print(f"  ! {w}")
        print()

    if final.follow_up_suggestions:
        print("PARA APROFUNDAR:")
        for s in final.follow_up_suggestions:
            print(f"  > {s}")
        print()

    print(
        f"[meta] perfil={final.profile_used} fluxo={final.flow_used} "
        f"sources={final.sources_cited}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    configure_logging()

    if not settings.has_anthropic_key:
        print(
            "ERRO: ANTHROPIC_API_KEY ausente ou placeholder. Configure no .env "
            "antes de rodar o master_flow.",
            file=sys.stderr,
        )
        return 1

    log.info("cli.start", question=args.question[:120], gateway=args.gateway)
    try:
        final = run_master(args.question)
        _print_final(final, json_only=args.json_only)
        return 0
    except Exception as exc:
        log.exception("cli.error", error=str(exc))
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
