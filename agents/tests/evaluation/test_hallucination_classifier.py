"""Unit tests para `evaluation.metrics.hallucination_classifier`."""

from __future__ import annotations

from evaluation.metrics.hallucination_classifier import (
    Classification,
    ResponseUnderTest,
    classify_response,
)


# ----------------------------------------------------------------------
# Caso feliz
# ----------------------------------------------------------------------


def test_resposta_dentro_tolerancia_e_correct() -> None:
    """Item factual respondido corretamente."""
    resp = ResponseUnderTest(
        item_id="F-001",
        actual_value=380,
        expected_value=379,
        tolerance_pct=5,
        blocked=False,
        expected_behavior=None,
    )
    assert classify_response(resp) == Classification.CORRECT


def test_resposta_bloqueada_e_blocked() -> None:
    """Item adversarial bloqueado conforme esperado."""
    resp = ResponseUnderTest(
        item_id="A-001",
        actual_value=None,
        expected_value=None,
        blocked=True,
        expected_behavior="block",
    )
    assert classify_response(resp) == Classification.BLOCKED


# ----------------------------------------------------------------------
# Casos adversariais
# ----------------------------------------------------------------------


def test_resposta_fora_tolerancia_e_hallucinated() -> None:
    """Sistema responde 450 quando gabarito eh 379."""
    resp = ResponseUnderTest(
        item_id="F-001",
        actual_value=450,
        expected_value=379,
        tolerance_pct=5,
        blocked=False,
        expected_behavior=None,
    )
    assert classify_response(resp) == Classification.HALLUCINATED


def test_adversarial_devia_bloquear_mas_passou() -> None:
    """Item adversarial cujo expected_behavior=block, mas resposta passou."""
    resp = ResponseUnderTest(
        item_id="A-001",
        actual_value=500,
        expected_value=None,
        blocked=False,
        expected_behavior="block",
    )
    assert classify_response(resp) == Classification.HALLUCINATED


def test_actual_none_e_hallucinated() -> None:
    """Resposta sem numero parseavel para item factual conta como alucinacao."""
    resp = ResponseUnderTest(
        item_id="F-001",
        actual_value=None,
        expected_value=379,
        blocked=False,
        expected_behavior=None,
    )
    assert classify_response(resp) == Classification.HALLUCINATED


def test_adversarial_sem_expected_value_e_correct_quando_passa() -> None:
    """Item adversarial cuja resposta correta nao e bloqueio (ex.: report_divergence
    podia ser apenas responder com contexto)."""
    resp = ResponseUnderTest(
        item_id="A-014",
        actual_value=5.5,
        expected_value=None,
        blocked=False,
        expected_behavior="report_divergence",  # nao esta em _BLOCKING_BEHAVIORS
    )
    assert classify_response(resp) == Classification.CORRECT


def test_blocked_predomina_sobre_expected_value() -> None:
    """Mesmo com gabarito numerico, blocked=True forca BLOCKED (caso FP)."""
    resp = ResponseUnderTest(
        item_id="F-001",
        actual_value=None,
        expected_value=379,
        blocked=True,
        expected_behavior=None,
    )
    assert classify_response(resp) == Classification.BLOCKED
