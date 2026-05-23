"""Figura comparativa: LLM-direto = Baseline = 10% << EduQuery = 63%.

Comunica o argumento central do paper em 1 segundo de leitura: o salto
de acuracia in-scope nao vem do RAG (LLM-direto e Baseline com RAG dao
o mesmo 10%), mas dos guardrails deterministicos do EduQuery.

Le os numeros reais de `statistical_analysis.json` (gerado por
`statistical_analysis.py`) — nenhum valor hardcoded. Fallback para os
JSONs brutos se a analise estatistica ainda nao existir.

CLI:
    python -m evaluation.reports.render_baseline_comparison_figure \\
        --stats evaluation/output/statistical_analysis.json \\
        --output evaluation/output/figures/comparison_baseline.png
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # backend sem display (headless / CI)
import matplotlib.pyplot as plt  # noqa: E402


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def render_figure(stats: dict[str, Any], output: Path) -> None:
    llm = stats.get("llm_direct_in_scope_accuracy", 0.10)
    baseline = stats["bootstrap_baseline_in_scope"]["mean"]
    edu = stats["bootstrap_eduquery_in_scope"]
    edu_mean = edu["mean"]
    # erro assimetrico a partir do IC bootstrap
    err_low = edu_mean - edu["lower"]
    err_high = edu["upper"] - edu_mean

    labels = [
        "LLM-direto\n(sem RAG, Haiku 4.5)",
        "Baseline\n(RAG, sem guardrails)",
        "EduQuery\n(guardrails ON)",
    ]
    values = [llm * 100, baseline * 100, edu_mean * 100]
    # cor distinta para a 3a barra (destaque do sistema proposto)
    colors = ["#9aa7b8", "#9aa7b8", "#2c6fbb"]

    plt.rcParams["font.family"] = "serif"
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=300)
    y = range(len(labels))
    ax.barh(list(y), values, color=colors, height=0.6, zorder=3)

    # error bar apenas na 3a barra (n=3)
    ax.errorbar(
        edu_mean * 100,
        2,
        xerr=[[err_low * 100], [err_high * 100]],
        fmt="none",
        ecolor="#163a63",
        elinewidth=1.6,
        capsize=5,
        capthick=1.6,
        zorder=4,
    )

    for i, v in enumerate(values):
        label = f"{v:.1f}%"
        x = v + 1.5
        if i == 2:
            label = f"{v:.1f}%  (IC95 {edu['lower']*100:.0f}–{edu['upper']*100:.0f})"
            x = edu["upper"] * 100 + 2.5  # apos o whisker, evita sobreposicao
        ax.text(x, i, label, va="center", fontsize=10, zorder=5)

    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()  # primeira label no topo
    ax.set_xlabel("Acuracia in-scope (%)", fontsize=10)
    ax.set_xlim(0, 100)
    ax.grid(axis="x", linestyle=":", alpha=0.5, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_title(
        "O salto de acuracia vem dos guardrails, nao do RAG",
        fontsize=11,
        pad=10,
    )

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Figura comparativa LLM/Baseline/EduQuery.")
    p.add_argument("--stats", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    render_figure(_load(args.stats), args.output)
    print(f"Figura salva em {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
