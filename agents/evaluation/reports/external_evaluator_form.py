"""Gerador da planilha de avaliacao externa (validade de conteudo).

Implementa a Fase B.1 do prompt `prompt-analises-pos-resultados.md` e a
Acao #1 da Tabela 2.1 do PDF do orientador (avaliador externo dos
gabaritos). Seleciona 5 itens in-scope + 5 adversariais cobrindo
categorias diversas e gera CSV (UTF-8 BOM, abre direto no Excel) e XLSX.

O avaliador externo preenche, por item:
- representativa_1a5: a pergunta e razoavel/representativa? (1-5)
- gabarito_correto: o expected_value/comportamento esta certo contra a
  fonte primaria? (sim/nao/incerto)
- comportamento_faz_sentido_1a5: so adversariais (1-5)
- comentario: texto livre

CLI:
    python -m evaluation.reports.external_evaluator_form \\
        --golden evaluation/golden \\
        --output evaluation/output/external_evaluator_form.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from evaluation.shared.loader import GoldenItem, load_golden

# 5 itens in-scope representativos (factuais + comparativos cobertos pelos
# marts atuais) e 5 adversariais de categorias distintas.
DEFAULT_IN_SCOPE = ("F-015", "F-017", "C-001", "C-010", "C-017")
DEFAULT_ADVERSARIAL_CATEGORIES = (
    "adversarial_numbers",
    "prompt_injection",
    "doi_fishing",
    "cross_source_contradiction",
    "empty_rag",
)

HEADER = [
    "id",
    "kind",
    "category",
    "query",
    "gabarito_esperado",
    "fonte_primaria",
    "doi",
    "representativa_1a5",
    "gabarito_correto_sim_nao_incerto",
    "comportamento_faz_sentido_1a5",
    "comentario",
]


def _gabarito_str(item: GoldenItem) -> str:
    if item.kind == "factual":
        unit = f" {item.unit}" if item.unit else ""
        return f"{item.expected_value}{unit}"
    if item.kind == "comparative":
        parts = []
        if item.expected_brazil is not None:
            parts.append(f"BRA={item.expected_brazil}")
        if item.expected_oecd_avg is not None:
            parts.append(f"OCDE={item.expected_oecd_avg}")
        for k, v in item.expected_other.items():
            parts.append(f"{k}={v}")
        unit = f" ({item.unit})" if item.unit else ""
        return ", ".join(parts) + unit
    return item.expected_behavior or ""


def select_items(
    golden: list[GoldenItem],
    in_scope_ids: tuple[str, ...] = DEFAULT_IN_SCOPE,
    adversarial_categories: tuple[str, ...] = DEFAULT_ADVERSARIAL_CATEGORIES,
) -> list[GoldenItem]:
    by_id = {it.id: it for it in golden}
    selected: list[GoldenItem] = [by_id[i] for i in in_scope_ids if i in by_id]

    seen_categories: set[str] = set()
    for cat in adversarial_categories:
        for it in golden:
            if it.kind == "adversarial" and it.category == cat and cat not in seen_categories:
                selected.append(it)
                seen_categories.add(cat)
                break
    return selected


def _rows(items: list[GoldenItem]) -> list[list[str]]:
    rows: list[list[str]] = []
    for it in items:
        rows.append([
            it.id,
            it.kind,
            it.category or "",
            it.query,
            _gabarito_str(it),
            it.primary_source or "",
            it.doi or "",
            "",  # representativa_1a5
            "",  # gabarito_correto
            "",  # comportamento_faz_sentido (adversariais)
            "",  # comentario
        ])
    return rows


def write_csv(items: list[GoldenItem], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig => BOM para o Excel reconhecer acentos.
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(_rows(items))


def write_xlsx(items: list[GoldenItem], output: Path) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
    except ImportError:  # pragma: no cover
        return
    wb = Workbook()
    ws = wb.active
    ws.title = "avaliacao_externa"
    ws.append(HEADER)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in _rows(items):
        ws.append(row)
    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)


def generate(golden_dir: Path, output: Path) -> list[GoldenItem]:
    golden = load_golden(golden_dir)
    items = select_items(golden)
    write_csv(items, output)
    if output.suffix.lower() == ".csv":
        write_xlsx(items, output.with_suffix(".xlsx"))
    return items


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Gera planilha de avaliacao externa.")
    p.add_argument("--golden", type=Path, default=Path("evaluation/golden"))
    p.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/output/external_evaluator_form.csv"),
    )
    args = p.parse_args(argv)
    items = generate(args.golden, args.output)
    print(f"{len(items)} itens escritos em {args.output} (+ .xlsx)")
    for it in items:
        print(f"  {it.id:7} {it.kind:11} {it.category or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
