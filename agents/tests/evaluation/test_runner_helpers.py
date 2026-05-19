"""Unit tests para helpers internos de `evaluation.shared.runner`.

Nao roda o pipeline real (requer LLM); cobre apenas as heuristicas
auxiliares de classificacao.
"""

from __future__ import annotations

from evaluation.shared.loader import GoldenItem
from evaluation.shared.runner import _detect_blocked, _is_error_a_block


# ----------------------------------------------------------------------
# _detect_blocked
# ----------------------------------------------------------------------


def test_detect_blocked_pega_warning_fact_check() -> None:
    """Fact Checker adiciona warning prefixado com 'Fact-check: ...'."""
    warnings = [
        "Fact-check: 3 valores no markdown nao correspondem ao dado real."
    ]
    assert _detect_blocked(None, warnings) is True


def test_detect_blocked_case_insensitive() -> None:
    warnings = ["FACT-CHECK: divergencias encontradas"]
    assert _detect_blocked(None, warnings) is True


def test_detect_blocked_ignora_outros_warnings() -> None:
    warnings = [
        "RAG local vazio.",
        "Indicador PISA nao publicado na Silver.",
    ]
    assert _detect_blocked(None, warnings) is False


def test_detect_blocked_lista_vazia() -> None:
    assert _detect_blocked(None, []) is False


# ----------------------------------------------------------------------
# _is_error_a_block
# ----------------------------------------------------------------------


def _adv_item(behavior: str | None) -> GoldenItem:
    return GoldenItem(
        id="A-X",
        kind="adversarial",
        query="?",
        category="adversarial_numbers",
        expected_behavior=behavior,
    )


def test_pydantic_validation_error_em_block_conta_como_bloqueio() -> None:
    err = (
        "ValidationError: Input should be less than or equal to 2030 "
        "[type=less_than_equal, input_value=2050, input_type=int]"
    )
    assert _is_error_a_block(err, _adv_item("block")) is True


def test_input_should_be_em_refuse_conta_como_bloqueio() -> None:
    err = "Input should be a valid integer"
    assert _is_error_a_block(err, _adv_item("refuse")) is True


def test_error_em_item_factual_nao_conta_como_block() -> None:
    """Items factuais nao tem expected_behavior; erro = falha tecnica."""
    err = "ValidationError: Input should be less than or equal to 2030"
    factual = GoldenItem(id="F-X", kind="factual", query="?")
    assert _is_error_a_block(err, factual) is False


def test_error_em_behavior_nao_bloqueante_nao_conta() -> None:
    err = "ValidationError: ..."
    item = _adv_item("report_divergence")  # nao bloqueante
    assert _is_error_a_block(err, item) is False


def test_error_vazio_nao_conta() -> None:
    assert _is_error_a_block(None, _adv_item("block")) is False
    assert _is_error_a_block("", _adv_item("block")) is False


def test_erro_generico_nao_pydantic_nao_conta() -> None:
    """Network timeout != bloqueio; e falha de infraestrutura."""
    err = "ConnectionError: gateway unreachable"
    assert _is_error_a_block(err, _adv_item("block")) is False
