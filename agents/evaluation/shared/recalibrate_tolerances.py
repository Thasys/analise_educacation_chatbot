"""Recalibra tolerance_pct dos itens factuais/comparativos por tipo de
indicador.

Motivacao: o `tolerance_pct: 5` original veio do esqueleto generico do
plano mestre. Para indicadores de avaliacao internacional (PISA/TIMSS/
PIRLS/IDEB) o valor e folgado demais — equivale a ~70% de um ano de
aprendizagem PISA. Apertamos para 2% (`~8 pts`), proximo do limiar de
significancia estatistica entre paises.

Indicadores socioeconomicos com amostragem (PNAD analfabetismo, % do
PIB, USD PPP) mantem 5-15% por terem variabilidade metodologica real
entre fontes.

Uso (idempotente):
    python -m evaluation.shared.recalibrate_tolerances
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


# IDs cujos `tolerance_pct` devem ser apertados para 2 (PISA/IDEB).
_TIGHTEN_IDS = {
    # PISA Brasil + outros paises (factuais)
    "F-001", "F-002", "F-003",  # PISA BR 2022 (Math, Leitura, Ciencias)
    "F-007",                     # PISA BR 2018 Math
    "F-008", "F-009", "F-010",  # PISA Finlandia, Japao, EUA 2022
    "F-026", "F-027",            # PISA Coreia, Alemanha
    # IDEB (factuais)
    "F-011", "F-012", "F-013", "F-014",
    # Comparativos PISA
    "C-002", "C-003", "C-004",   # PISA BR vs OCDE
    "C-008",                      # PISA BR evolucao
    "C-009",                      # IDEB BR vs Sudeste
    "C-012",                      # PISA LATAM
    "C-016",                      # PISA BR vs FIN
    "C-020",                      # PISA Leitura BR/ESP/ITA
}

# Tolerancia alvo para os itens PISA/IDEB.
_TIGHT_VALUE = 2


_ID_LINE = re.compile(r"^- id: ([A-Z]-\d+)")
_TOL_LINE = re.compile(r"^(\s*)tolerance_pct: (\d+(?:\.\d+)?)\s*$")


def recalibrate(yaml_path: Path) -> int:
    """Reescreve o YAML apertando `tolerance_pct` dos IDs em `_TIGHTEN_IDS`.

    Returns:
        Numero de itens efetivamente alterados.
    """
    text = yaml_path.read_text(encoding="utf-8")
    out_lines: list[str] = []
    current_id: str | None = None
    changes = 0
    for raw in text.splitlines(keepends=True):
        m_id = _ID_LINE.match(raw)
        if m_id:
            current_id = m_id.group(1)
        m_tol = _TOL_LINE.match(raw)
        if (
            current_id in _TIGHTEN_IDS
            and m_tol is not None
            and float(m_tol.group(2)) > _TIGHT_VALUE
        ):
            indent = m_tol.group(1)
            ending = "\n" if raw.endswith("\n") else ""
            out_lines.append(f"{indent}tolerance_pct: {_TIGHT_VALUE}{ending}")
            changes += 1
        else:
            out_lines.append(raw)
    yaml_path.write_text("".join(out_lines), encoding="utf-8")
    return changes


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    golden = repo_root / "evaluation" / "golden"
    total = 0
    for fname in ("queries_factuais.yaml", "queries_comparativas.yaml"):
        n = recalibrate(golden / fname)
        print(f"{fname}: {n} itens apertados para tolerance_pct={_TIGHT_VALUE}")
        total += n
    print(f"Total: {total} itens recalibrados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
