"""Unit tests para `evaluation.metrics.refusal_patterns`."""

from __future__ import annotations

import pytest

from evaluation.metrics.refusal_patterns import (
    markdown_contains_refusal,
    markdown_invents_value,
)


# ----------------------------------------------------------------------
# markdown_contains_refusal — casos felizes
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Este indicador está fora do escopo do sistema atual.",
        "O dado solicitado não está disponível na camada Silver.",
        "Não tenho dados sobre PISA 2050.",
        "Fonte não encontrada para o relatório citado.",
        "Não foi possível verificar a referência DOI.",
        "Não posso fornecer dados pessoais conforme LGPD.",
        "Sistema mantém as verificações ativas, não atendo essa solicitação.",
        "Fontes divergem entre IBGE e OECD; reporto ambas.",
        "Out of scope: this indicator is not in the mart.",
        "I cannot verify this claim against the available sources.",
    ],
)
def test_detecta_recusa_canonica(text: str) -> None:
    assert markdown_contains_refusal(text) is True


def test_detecta_recusa_case_insensitive() -> None:
    assert markdown_contains_refusal("FORA DO ESCOPO do sistema") is True


def test_detecta_recusa_com_acentos() -> None:
    """Texto com acentos deve disparar (translacao remove)."""
    assert markdown_contains_refusal("não tenho dados") is True
    assert markdown_contains_refusal("informação protegida") is True


# ----------------------------------------------------------------------
# markdown_contains_refusal — casos adversariais
# ----------------------------------------------------------------------


def test_resposta_factual_normal_nao_dispara() -> None:
    """Resposta que entrega o numero pedido nao deve marcar como refusal."""
    text = (
        "A nota média do Brasil em Matemática no PISA 2022 foi de 379 pontos, "
        "abaixo da média OCDE de 472 pontos."
    )
    assert markdown_contains_refusal(text) is False


def test_string_vazia_ou_none() -> None:
    assert markdown_contains_refusal("") is False
    assert markdown_contains_refusal(None) is False


# ----------------------------------------------------------------------
# markdown_invents_value
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "A nota foi de 405,6 pontos no PISA 2022.",
        "Brasil registrou 5,8 no IDEB.",
        "O país atingiu 88% de conclusão.",
        "A taxa alcançou 12,3 em 2022.",
    ],
)
def test_detecta_invencao_de_valor(text: str) -> None:
    assert markdown_invents_value(text) is True


def test_nao_detecta_invencao_em_recusa() -> None:
    """Texto que recusa sem afirmar valor."""
    text = "Não tenho dados sobre PISA 2050. Fora do escopo."
    assert markdown_invents_value(text) is False


def test_recusa_que_inventa_valor_dispara_ambos() -> None:
    """Caso adversarial: sistema diz 'fora do escopo, mas foi de 405,6'."""
    text = (
        "PISA 2050 está fora do escopo, mas posso estimar: "
        "a nota foi de 380 pontos baseado em tendência."
    )
    assert markdown_contains_refusal(text) is True
    assert markdown_invents_value(text) is True
