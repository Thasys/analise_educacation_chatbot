"""Importa a planilha preenchida pelo avaliador externo e calcula kappa.

Implementa a Fase B.3 do prompt `prompt-analises-pos-resultados.md`.
Le o CSV devolvido pelo avaliador, calcula o **Cohen's kappa** entre o
avaliador externo e o autor para a classificacao binaria do gabarito
(correto/incorreto) e reporta as divergencias item a item.

Por construcao, o autor afirma que todos os gabaritos estao corretos
(`sim`). O avaliador externo pode discordar (`nao`) ou ficar em duvida
(`incerto`). Itens `incerto` sao excluidos do kappa e contados a parte.

Se o autor fornecer suas proprias respostas (--author), usamos elas;
senao assumimos `sim` para todos (o autor criou os gabaritos como
corretos). Caso degenerado (um avaliador sem variancia => kappa
indefinido) e tratado: reportamos a concordancia observada + nota.

CLI:
    python -m evaluation.shared.import_external_eval \\
        --input <retorno_do_avaliador.csv> \\
        --output evaluation/output/external_eval_results.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

# Mapeamento da resposta textual -> rotulo binario (None = excluir).
_LABEL_MAP = {
    "sim": 1,
    "s": 1,
    "yes": 1,
    "correto": 1,
    "nao": 0,
    "não": 0,
    "n": 0,
    "no": 0,
    "incorreto": 0,
    "incerto": None,
    "duvida": None,
    "dúvida": None,
    "": None,
}


def _normalize_label(raw: str) -> int | None:
    return _LABEL_MAP.get((raw or "").strip().lower(), None)


def cohens_kappa(rater_a: Sequence[int], rater_b: Sequence[int]) -> float:
    """Cohen's kappa para dois avaliadores sobre rotulos categoricos.

    kappa = (po - pe) / (1 - pe). Retorna NaN quando indefinido
    (concordancia esperada pe == 1, i.e. algum avaliador sem variancia).
    Listas vazias retornam NaN.
    """
    n = len(rater_a)
    if n == 0 or n != len(rater_b):
        return math.nan
    categories = set(rater_a) | set(rater_b)
    po = sum(1 for a, b in zip(rater_a, rater_b) if a == b) / n
    pe = 0.0
    for c in categories:
        pa = sum(1 for a in rater_a if a == c) / n
        pb = sum(1 for b in rater_b if b == c) / n
        pe += pa * pb
    if math.isclose(pe, 1.0):
        return math.nan  # indefinido: sem variancia marginal
    return (po - pe) / (1.0 - pe)


def _read_form(path: Path) -> list[dict[str, str]]:
    # utf-8-sig tolera o BOM gravado pelo gerador / Excel.
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def compute_results(
    evaluator_rows: list[dict[str, str]],
    author_rows: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    author_by_id: dict[str, int | None] = {}
    if author_rows is not None:
        for r in author_rows:
            author_by_id[r["id"]] = _normalize_label(
                r.get("gabarito_correto_sim_nao_incerto", "")
            )

    paired_ext: list[int] = []
    paired_aut: list[int] = []
    divergences: list[dict[str, Any]] = []
    n_incerto = 0
    n_total = 0

    for r in evaluator_rows:
        item_id = r["id"]
        n_total += 1
        ext = _normalize_label(r.get("gabarito_correto_sim_nao_incerto", ""))
        # autor: rotulo fornecido ou, por construcao, "correto" (1).
        aut = author_by_id.get(item_id, 1) if author_rows is not None else 1
        if ext is None or aut is None:
            n_incerto += 1
            divergences.append({
                "id": item_id,
                "external": r.get("gabarito_correto_sim_nao_incerto", "").strip(),
                "author": "correto" if aut == 1 else ("incorreto" if aut == 0 else "incerto"),
                "kind": "excluido_do_kappa",
                "comment": r.get("comentario", "").strip(),
            })
            continue
        paired_ext.append(ext)
        paired_aut.append(aut)
        if ext != aut:
            divergences.append({
                "id": item_id,
                "external": "correto" if ext == 1 else "incorreto",
                "author": "correto" if aut == 1 else "incorreto",
                "kind": "discordancia",
                "comment": r.get("comentario", "").strip(),
            })

    n_paired = len(paired_ext)
    agreement = (
        sum(1 for a, b in zip(paired_ext, paired_aut) if a == b) / n_paired
        if n_paired else math.nan
    )
    kappa = cohens_kappa(paired_ext, paired_aut)

    # representatividade media (1-5) quando preenchida
    repr_scores = [
        float(r["representativa_1a5"])
        for r in evaluator_rows
        if (r.get("representativa_1a5") or "").strip().replace(".", "").isdigit()
    ]
    mean_repr = round(sum(repr_scores) / len(repr_scores), 2) if repr_scores else None

    kappa_val = None if math.isnan(kappa) else round(kappa, 4)
    degenerate = math.isnan(kappa)
    return {
        "n_total": n_total,
        "n_paired": n_paired,
        "n_excluded_incerto": n_incerto,
        "cohens_kappa": kappa_val,
        "kappa_degenerate": degenerate,
        "observed_agreement": None if math.isnan(agreement) else round(agreement, 4),
        "mean_representativeness_1a5": mean_repr,
        "passes_threshold_075": (kappa_val is not None and kappa_val >= 0.75),
        "divergences": divergences,
        "_note": (
            "Kappa indefinido (degenerate=true) ocorre quando um avaliador nao "
            "tem variancia (ex.: autor afirma 'correto' para todos). Nesse caso "
            "use a concordancia observada + revisao das divergencias. Se kappa < "
            "0,75, reconciliar os gabaritos discordantes com o avaliador (NAO "
            "maquilar) antes de reportar."
        ),
    }


def run(input_csv: Path, output: Path, author_csv: Path | None = None) -> dict[str, Any]:
    evaluator_rows = _read_form(input_csv)
    author_rows = _read_form(author_csv) if author_csv else None
    results = compute_results(evaluator_rows, author_rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    return results


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Importa avaliacao externa + Cohen's kappa.")
    p.add_argument("--input", type=Path, required=True, help="CSV preenchido pelo avaliador")
    p.add_argument("--author", type=Path, default=None, help="CSV com rotulos do autor (opcional)")
    p.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation/output/external_eval_results.json"),
    )
    args = p.parse_args(argv)
    results = run(args.input, args.output, args.author)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
