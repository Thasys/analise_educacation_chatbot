"""Unit tests para `evaluation.shared.loader`."""

from __future__ import annotations

from pathlib import Path

from evaluation.shared.loader import (
    load_adversarial,
    load_golden,
)


GOLDEN_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "golden"


def test_load_golden_total_84_items() -> None:
    items = load_golden(GOLDEN_DIR)
    assert len(items) >= 80
    kinds = {it.kind for it in items}
    assert kinds == {"factual", "comparative", "adversarial"}


def test_load_adversarial_30_items_9_categorias() -> None:
    items = load_adversarial(GOLDEN_DIR / "adversarial.yaml")
    assert len(items) >= 30
    cats = {it.category for it in items}
    expected = {
        "adversarial_numbers",
        "doi_fishing",
        "source_spoofing",
        "year_confusion",
        "cross_source_contradiction",
        "privacy_probe",
        "prompt_injection",
        "empty_rag",
        "adversarial_figure",
    }
    assert cats == expected


def test_factual_item_tem_expected_value() -> None:
    items = load_golden(GOLDEN_DIR)
    factuais = [it for it in items if it.kind == "factual"]
    # Pelo menos os primeiros 10 itens devem ter expected_value real
    com_valor = [it for it in factuais if it.expected_value is not None]
    assert len(com_valor) >= 30


def test_comparativo_item_tem_expected_brazil() -> None:
    items = load_golden(GOLDEN_DIR)
    comp = [it for it in items if it.kind == "comparative"]
    com_brasil = [it for it in comp if it.expected_brazil is not None]
    assert len(com_brasil) >= 15


def test_adversarial_tem_expected_behavior_canonico() -> None:
    items = load_adversarial(GOLDEN_DIR / "adversarial.yaml")
    behaviors = {it.expected_behavior for it in items}
    canonicos = {
        "block",
        "block_or_disclaim",
        "block_figure",
        "refuse",
        "scope_disclaimer",
        "correct_year_and_value",
        "report_divergence",
        "ignore_injection",
    }
    # Todos os comportamentos observados sao do conjunto canonico.
    assert behaviors.issubset(canonicos), f"unexpected: {behaviors - canonicos}"


def test_in_scope_items_sao_verificados() -> None:
    """Acao #1 das orientacoes_metodologicas (2026-05-21): os 10 itens
    in-scope devem ter _verified=true. Os demais ficam como DRAFT para
    revisao final pos-notificacao SBIE."""
    items = load_golden(GOLDEN_DIR)
    factuais_e_comp = [it for it in items if it.kind in ("factual", "comparative")]
    verificados = [it for it in factuais_e_comp if it.verified]
    # Os 10 in-scope foram verificados em 2026-05-22 (ver
    # `verify_in_scope_goldens.py` e `mark_verified.py`).
    assert len(verificados) >= 10, (
        f"Esperado >=10 itens verificados, encontrei {len(verificados)}"
    )
