"""Re-roda apenas os itens que falharam por infraestrutura (credit
balance, overload) e mescla com o JSON existente.

Economiza tokens: nao re-executa itens ja com resultado valido.

Uso:
    python -m evaluation.shared.rerun_failed \\
        --input  evaluation/output/eduquery_official.json \\
        --golden evaluation/golden \\
        --mode   eduquery
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evaluation.shared.loader import load_golden
from evaluation.shared.runner import execute


def _should_rerun(item: dict) -> bool:
    err = (item.get("error") or "").lower()
    if not err:
        return False
    markers = (
        "credit balance is too low",
        "529",
        "overloaded",
        "rate_limit",
        "ratelimiterror",
        "no completion choices",  # instructor falhou
        "no running event loop",  # crewai.flow.flow async glitch
    )
    return any(m in err for m in markers)


def merge(input_path: Path, golden_dir: Path, *, mode: str) -> None:
    existing = json.loads(input_path.read_text(encoding="utf-8"))
    to_rerun_ids = {it["id"] for it in existing["items"] if _should_rerun(it)}
    print(f"Itens a re-rodar: {sorted(to_rerun_ids)}")
    if not to_rerun_ids:
        print("Nada a re-rodar; saida intacta.")
        return
    all_golden = load_golden(golden_dir)
    items_to_run = [g for g in all_golden if g.id in to_rerun_ids]
    if len(items_to_run) != len(to_rerun_ids):
        missing = to_rerun_ids - {g.id for g in items_to_run}
        print(f"AVISO: {len(missing)} IDs nao encontrados no golden: {sorted(missing)}")
    no_guardrails = mode == "baseline"
    # Output temporario com APENAS os itens re-executados
    tmp_out = input_path.with_suffix(".rerun.json")
    execute(
        items_to_run,
        mode=mode,
        no_guardrails=no_guardrails,
        output=tmp_out,
        limit=None,
    )
    # Le o resultado e mescla
    rerun_data = json.loads(tmp_out.read_text(encoding="utf-8"))
    rerun_by_id = {it["id"]: it for it in rerun_data["items"]}
    merged_items = []
    for it in existing["items"]:
        if it["id"] in rerun_by_id:
            merged_items.append(rerun_by_id[it["id"]])
        else:
            merged_items.append(it)
    existing["items"] = merged_items
    existing["_rerun_appended"] = {
        "n_rerun": len(rerun_by_id),
        "rerun_ids": sorted(rerun_by_id.keys()),
        "rerun_duration_s": rerun_data["duration_s"],
    }
    input_path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Mesclado: {len(rerun_by_id)} itens atualizados em {input_path}")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--golden", type=Path, required=True)
    p.add_argument("--mode", required=True, choices=("baseline", "eduquery", "red_team"))
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    merge(args.input, args.golden, mode=args.mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
