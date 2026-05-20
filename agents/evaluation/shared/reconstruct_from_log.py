"""Reconstroi um JSON de resultados a partir do log de execucao do
background task quando o JSON original foi sobrescrito.

Util quando precisamos recuperar id + classification + latency por
item, mas perdemos o markdown / warnings / recall (que ficam null).

Uso:
    python -m evaluation.shared.reconstruct_from_log \\
        --log /path/to/task.output \\
        --golden evaluation/golden \\
        --mode baseline \\
        --output evaluation/output/baseline_official.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from evaluation.shared.loader import load_golden


_ITEM_DONE_RE = re.compile(
    r"item_done\s+classification=(\w+)\s+i=(\d+)\s+id=([A-Z0-9-]+)\s+"
    r"latency_s=([\d.]+)\s+mode=(\w+)"
)


def reconstruct(
    log_path: Path,
    golden_dir: Path,
    *,
    mode: str,
    no_guardrails: bool,
) -> dict:
    items_by_id = {it.id: it for it in load_golden(golden_dir)}
    results: list[dict] = []
    started_at = None
    last_ts = None
    with log_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            ts_match = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
            if ts_match and started_at is None:
                started_at = ts_match.group(1)
            if ts_match:
                last_ts = ts_match.group(1)
            m = _ITEM_DONE_RE.search(line)
            if not m:
                continue
            classification = m.group(1)
            item_id = m.group(3)
            latency_s = float(m.group(4))
            item = items_by_id.get(item_id)
            if item is None:
                continue
            expected = item.expected_value
            if item.kind == "comparative":
                expected = item.expected_brazil
            results.append(
                {
                    "id": item.id,
                    "kind": item.kind,
                    "query": item.query,
                    "expected_value": expected,
                    "actual_value": None,
                    "tolerance_pct": item.tolerance_pct,
                    "blocked": classification == "blocked",
                    "expected_behavior": item.expected_behavior,
                    "category": item.category,
                    "classification": classification,
                    "latency_s": round(latency_s, 3),
                    "markdown": "",
                    "n_citations": 0,
                    "warnings": [],
                    "sources_recall": None,
                    "doi_recall": None,
                    "error": None,
                    "_reconstructed_from_log": True,
                }
            )
    duration = 0.0
    if started_at and last_ts:
        t0 = datetime.fromisoformat(started_at).replace(tzinfo=timezone.utc)
        t1 = datetime.fromisoformat(last_ts).replace(tzinfo=timezone.utc)
        duration = (t1 - t0).total_seconds()
    return {
        "mode": mode,
        "no_guardrails": no_guardrails,
        "started_at": started_at,
        "duration_s": round(duration, 2),
        "n_items": len(results),
        "items": results,
        "_source": f"reconstructed from {log_path.name}",
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--golden", type=Path, required=True)
    p.add_argument("--mode", required=True, choices=("baseline", "eduquery", "red_team"))
    p.add_argument("--output", type=Path, required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    no_guardrails = args.mode == "baseline"
    payload = reconstruct(
        args.log, args.golden, mode=args.mode, no_guardrails=no_guardrails
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Reconstruido {len(payload['items'])} itens em {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
