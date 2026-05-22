"""Marca `_verified: true` em itens cujos gabaritos foram cross-checados.

Lista canonica vem de
`agents/evaluation/shared/verify_in_scope_goldens.py` (Acao #1 do
PDF do orientador).

Idempotente.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


# IDs cujos gabaritos batem com mart (validados em 2026-05-22).
_VERIFIED_VIA_MART = {
    "F-015", "F-016", "F-017",
    "C-001", "C-010", "C-011", "C-017",
}

# IDs verificados manualmente contra fonte externa (OECD EAG 2024).
# F-018: media OCDE gasto 2021 = 4,9% (OECD EAG 2024 Table C2.1).
# F-021: media OCDE conclusao EM 25-34 2021 = 85% (OECD EAG 2023 Tab A1.1).
# F-020: BR conclusao EM 25-34 2021 = 73% (OECD EAG 2023 BR Country Note).
# Para os demais (F-032 USD PPP, F-019 escolaridade media, C-005, C-006,
# C-014, C-015, C-018), aceitar gabarito existente com tolerancia ja
# ampla mas NAO marcar verified — sao trabalho futuro.
_VERIFIED_VIA_EXTERNAL = {
    "F-018",
    "F-020",
    "F-021",
}


ALL_VERIFIED = _VERIFIED_VIA_MART | _VERIFIED_VIA_EXTERNAL

_ID_LINE = re.compile(r"^- id: ([FC]-\d+)\s*$")
_VERIFIED_FALSE = re.compile(r"^(\s*)_verified:\s*false\s*$")


def mark(yaml_path: Path) -> int:
    lines = yaml_path.read_text(encoding="utf-8").splitlines(keepends=True)
    out = []
    current_id = None
    n_changed = 0
    for line in lines:
        m_id = _ID_LINE.match(line)
        if m_id:
            current_id = m_id.group(1)
        if current_id in ALL_VERIFIED:
            m = _VERIFIED_FALSE.match(line)
            if m:
                out.append(f"{m.group(1)}_verified: true\n")
                n_changed += 1
                continue
        out.append(line)
    yaml_path.write_text("".join(out), encoding="utf-8")
    return n_changed


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    golden = repo_root / "evaluation" / "golden"
    total = 0
    for fname in ("queries_factuais.yaml", "queries_comparativas.yaml"):
        n = mark(golden / fname)
        print(f"{fname}: {n} itens marcados _verified=true")
        total += n
    print(f"Total: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
