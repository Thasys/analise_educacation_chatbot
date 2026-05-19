"""Unit tests para `evaluation.metrics.doi_validity`.

Os testes que tocariam a rede (`is_doi_resolvable`) ficam fora desta
suite por padrao. So testamos a parte sintatica + recall.
"""

from __future__ import annotations

import pytest

from evaluation.metrics.doi_validity import (
    compute_doi_recall,
    is_doi_syntactically_valid,
)


# ----------------------------------------------------------------------
# Sintaxe — caso feliz
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "doi",
    [
        "10.1787/53f23881-en",  # PISA 2022 OECD
        "10.1787/c00cad36-en",  # OECD EAG 2024
        "10.1000/xyz123",  # generico
        "10.1234/ab-cd_ef.gh:ij",  # caracteres permitidos
    ],
)
def test_dois_validos_sintaticamente(doi: str) -> None:
    assert is_doi_syntactically_valid(doi) is True


def test_recall_perfeito_quando_todos_citados() -> None:
    cited = ["10.1787/53f23881-en", "10.1787/c00cad36-en"]
    expected = ["10.1787/53f23881-en", "10.1787/c00cad36-en"]
    assert compute_doi_recall(cited, expected) == 1.0


def test_recall_case_insensitive() -> None:
    cited = ["10.1787/ABC-DEF"]
    expected = ["10.1787/abc-def"]
    assert compute_doi_recall(cited, expected) == 1.0


def test_recall_trivial_quando_expected_vazio() -> None:
    assert compute_doi_recall([], []) == 1.0
    assert compute_doi_recall(["10.1787/foo"], []) == 1.0


# ----------------------------------------------------------------------
# Sintaxe — casos adversariais
# ----------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_doi",
    [
        None,
        "",
        "   ",
        "doi:10.1787/foo",  # prefixo `doi:` nao pertence ao identificador
        "10.123/foo",  # prefix tem so 3 digitos; minimo 4
        "10./foo",  # registry vazio
        "10.1787/",  # suffix vazio
        "https://doi.org/10.1787/abc",  # URL completa nao e o DOI
    ],
)
def test_dois_invalidos(bad_doi: str | None) -> None:
    assert is_doi_syntactically_valid(bad_doi) is False  # type: ignore[arg-type]


def test_recall_parcial_quando_um_doi_inventado() -> None:
    """Resposta cita 1 DOI real e 1 fabricado; expected eh um real e outro real."""
    cited = ["10.1787/53f23881-en", "10.9999/fake-doi-inventado"]
    expected = ["10.1787/53f23881-en", "10.1787/c00cad36-en"]
    recall = compute_doi_recall(cited, expected)
    assert recall == pytest.approx(0.5)


def test_recall_ignora_strings_invalidas_no_input() -> None:
    """Citacoes com sintaxe invalida nao deveriam contar como hit."""
    cited = ["nao-e-um-doi", "10.1787/53f23881-en"]
    expected = ["10.1787/53f23881-en"]
    assert compute_doi_recall(cited, expected) == 1.0
