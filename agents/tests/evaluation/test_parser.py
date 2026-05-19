"""Unit tests para `evaluation.shared.parser`."""

from __future__ import annotations

import pytest

from evaluation.shared.parser import (
    best_match,
    extract_numbers,
    first_non_year_number,
)


# ----------------------------------------------------------------------
# extract_numbers — casos felizes
# ----------------------------------------------------------------------


def test_extract_numbers_filtra_anos() -> None:
    md = "Em 2022, o Brasil teve 379 pontos em Matematica."
    nums = extract_numbers(md)
    assert 379.0 in nums
    assert 2022.0 not in nums


def test_extract_numbers_aceita_virgula_decimal() -> None:
    md = "A taxa caiu para 5,6% em 2022."
    nums = extract_numbers(md)
    assert 5.6 in nums


def test_extract_numbers_aceita_ponto_decimal() -> None:
    md = "IDEB 5.8 nos anos iniciais."
    nums = extract_numbers(md)
    assert 5.8 in nums


def test_extract_numbers_multiplos_valores() -> None:
    md = "Brasil 379, OCDE 472, gap de 93."
    nums = extract_numbers(md)
    assert 379.0 in nums
    assert 472.0 in nums
    assert 93.0 in nums


# ----------------------------------------------------------------------
# extract_numbers — casos adversariais
# ----------------------------------------------------------------------


def test_extract_numbers_string_vazia() -> None:
    assert extract_numbers("") == []


def test_extract_numbers_sem_numeros() -> None:
    assert extract_numbers("apenas texto sem digitos") == []


def test_extract_numbers_aceita_negativo() -> None:
    md = "Variacao de -3,2 pontos em relacao a 2018."
    nums = extract_numbers(md)
    assert -3.2 in nums


# ----------------------------------------------------------------------
# best_match — caso feliz
# ----------------------------------------------------------------------


def test_best_match_pega_mais_proximo() -> None:
    nums = [100.0, 200.0, 379.0, 500.0]
    assert best_match(nums, expected=379.0, tolerance_pct=5) == 379.0


def test_best_match_tolerancia_dentro() -> None:
    """380.5 esta a 0.4% de 379 — bate."""
    assert best_match([380.5], expected=379.0, tolerance_pct=5) == 380.5


def test_best_match_variante_percentual() -> None:
    """Resposta usa proporcao 0.056 quando expected eh 5.6 (%): bate via *100."""
    assert best_match([0.056], expected=5.6, tolerance_pct=5) == 0.056


def test_best_match_variante_inversa() -> None:
    """Resposta usa 0.73 (proporcao) quando expected eh 73 (%): bate via *100."""
    assert best_match([0.73], expected=73.0, tolerance_pct=5) == 0.73


# ----------------------------------------------------------------------
# best_match — casos adversariais
# ----------------------------------------------------------------------


def test_best_match_lista_vazia() -> None:
    assert best_match([], expected=379.0) is None


def test_best_match_nada_dentro_da_tolerancia() -> None:
    nums = [100.0, 200.0, 500.0]
    assert best_match(nums, expected=379.0, tolerance_pct=5) is None


def test_best_match_expected_zero_pega_min_abs() -> None:
    nums = [3.0, -1.0, 5.0]
    assert best_match(nums, expected=0.0) == -1.0


def test_first_non_year_number_skipa_2022() -> None:
    md = "Em 2022, Brasil tirou 379 pontos."
    assert first_non_year_number(md) == 379.0


def test_first_non_year_number_retorna_none_sem_match() -> None:
    assert first_non_year_number("texto sem numero") is None
