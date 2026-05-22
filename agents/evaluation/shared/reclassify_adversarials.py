"""Re-classifica os 30 itens adversariais aplicando a TCC sobre o
JSON eduquery_official.json existente — sem re-rodar o pipeline.

Implementa a recomendacao do orientador (orientacoes_metodologicas
2026-05-21, Acao #2 da Secao 6: "Re-analisar os 30 markdowns
adversariais com _markdown_contains_refusal para calcular TCC real").

Camadas:
1. structural: ja registrada como `blocked=True` no JSON.
2. semantic:   `markdown_contains_refusal` + `markdown_invents_value`.
3. llm_judge:  apenas para items com `verification_method=llm_judge`
               (sub-set pequeno), via Batch API com 50% desconto.

Saida: cria `eduquery_official_tcc.json` ao lado do original com
campo extra `tcc_classification` por item adversarial.

CLI:
    python -m evaluation.shared.reclassify_adversarials \\
        --input evaluation/output/eduquery_official.json \\
        --golden evaluation/golden \\
        [--enable-llm-judge]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from evaluation.metrics.hallucination_classifier import (
    Classification,
    ResponseUnderTest,
    classify_adversarial,
)
from evaluation.metrics.llm_judge_batch import JudgeRequest, run_judge_batch
from evaluation.shared.loader import load_adversarial


logger = logging.getLogger(__name__)


def _build_resp(adv_item, run_item: dict) -> ResponseUnderTest:
    """Constroi ResponseUnderTest a partir do golden item + JSON result."""
    return ResponseUnderTest(
        item_id=adv_item.id,
        actual_value=run_item.get("actual_value"),
        expected_value=None,
        tolerance_pct=adv_item.tolerance_pct,
        blocked=bool(run_item.get("blocked", False)),
        expected_behavior=adv_item.expected_behavior,
        markdown=run_item.get("markdown", "") or "",
        verification_method=getattr(adv_item, "verification_method", "semantic")
        or "semantic",
        acceptance_criteria=getattr(adv_item, "acceptance_criteria", {}) or {},
    )


def reclassify(
    input_path: Path,
    golden_dir: Path,
    *,
    enable_llm_judge: bool = False,
) -> dict:
    """Le `input_path`, re-classifica adversariais, retorna payload atualizado."""
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    items = payload.get("items", [])

    adv_golden = {it.id: it for it in load_adversarial(golden_dir / "adversarial.yaml")}

    # ----- Camadas 1 + 2 (sem LLM) -----
    needs_llm: list[tuple[str, ResponseUnderTest]] = []
    layer_counts = {"structural": 0, "semantic_correct": 0, "semantic_halluc": 0, "llm_pending": 0}
    for run_item in items:
        if run_item.get("kind") != "adversarial":
            continue
        adv = adv_golden.get(run_item["id"])
        if adv is None:
            logger.warning("Golden item %s not found", run_item["id"])
            continue
        resp = _build_resp(adv, run_item)
        verif_method = getattr(adv, "verification_method", "semantic") or "semantic"

        # Camada 3 atrasada: se item e llm_judge E nao decidido pela camada 1.
        if verif_method == "llm_judge" and not resp.blocked:
            needs_llm.append((adv.id, resp))
            layer_counts["llm_pending"] += 1
            continue

        # Camadas 1 e 2 puras.
        new_cls = classify_adversarial(resp, llm_judge_fn=None)
        if resp.blocked:
            layer_counts["structural"] += 1
        elif new_cls == Classification.CORRECT:
            layer_counts["semantic_correct"] += 1
        else:
            layer_counts["semantic_halluc"] += 1
        run_item["tcc_classification"] = new_cls.value
        run_item["tcc_method"] = verif_method

    # ----- Camada 3 (LLM juiz via batch) -----
    if enable_llm_judge and needs_llm:
        print(f"Chamando Batch API para {len(needs_llm)} itens (LLM juiz)...")
        judge_requests = [
            JudgeRequest(
                custom_id=item_id,
                query=adv_golden[item_id].query,
                expected_behavior=adv_golden[item_id].expected_behavior or "block",
                markdown=resp.markdown,
            )
            for item_id, resp in needs_llm
        ]
        result = run_judge_batch(judge_requests, timeout_s=600)
        print(f"Batch concluido. Custo: ${result.cost_usd:.5f}. Erros: {len(result.errors)}")
        # Aplicar decisoes ao JSON.
        for item_id, resp in needs_llm:
            decision = result.decisions.get(item_id)
            judge_correct = bool(decision) if decision is not None else False
            new_cls = classify_adversarial(
                resp, llm_judge_fn=lambda md, beh, qid, ok=judge_correct: ok
            )
            for run_item in items:
                if run_item["id"] == item_id:
                    run_item["tcc_classification"] = new_cls.value
                    run_item["tcc_method"] = "llm_judge"
                    run_item["tcc_judge_decision"] = decision
                    if item_id in result.errors:
                        run_item["tcc_judge_error"] = result.errors[item_id]
                    break
    elif needs_llm:
        # Sem juiz habilitado: marca como pendente.
        print(
            f"[atencao] {len(needs_llm)} items requerem LLM juiz "
            f"({[i for i, _ in needs_llm]}). "
            f"Use --enable-llm-judge para resolver via Batch API."
        )
        for item_id, resp in needs_llm:
            for run_item in items:
                if run_item["id"] == item_id:
                    run_item["tcc_classification"] = "pending_llm_judge"
                    run_item["tcc_method"] = "llm_judge"
                    break

    payload["_tcc_reclassified"] = {
        "layer_1_structural": layer_counts["structural"],
        "layer_2_correct": layer_counts["semantic_correct"],
        "layer_2_halluc": layer_counts["semantic_halluc"],
        "layer_3_pending": layer_counts["llm_pending"] if not enable_llm_judge else 0,
        "llm_judge_used": enable_llm_judge,
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Re-classifica adversariais via TCC sem re-rodar pipeline."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--golden", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--enable-llm-judge",
        action="store_true",
        help="Aciona Batch API para resolver items llm_judge (custo ~$0.025).",
    )
    args = parser.parse_args(argv)

    output = args.output or args.input.parent / f"{args.input.stem}_tcc.json"
    payload = reclassify(args.input, args.golden, enable_llm_judge=args.enable_llm_judge)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"TCC salva em: {output}")
    print(f"Resumo: {json.dumps(payload['_tcc_reclassified'], indent=2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
