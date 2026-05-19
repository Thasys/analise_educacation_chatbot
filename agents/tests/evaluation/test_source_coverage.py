"""Unit tests para `evaluation.metrics.source_coverage`."""

from __future__ import annotations

import pytest

from evaluation.metrics.source_coverage import compute_source_recall, extract_sources


# ----------------------------------------------------------------------
# Caso feliz
# ----------------------------------------------------------------------


def test_extract_unicas_fontes_canonicas() -> None:
    text = "Segundo o OECD PISA 2022 e dados do IBGE PNAD, o Brasil teve..."
    sources = extract_sources(text)
    assert sources == {"OECD", "IBGE", "PISA"}


def test_aliases_ocde_e_banco_mundial_funcionam() -> None:
    """'OCDE' deve mapear para OECD; 'Banco Mundial' para World Bank."""
    text = "Conforme a OCDE e o Banco Mundial, o gasto..."
    sources = extract_sources(text)
    assert "OECD" in sources
    assert "World Bank" in sources


def test_recall_perfeito_quando_todas_fontes_citadas() -> None:
    text = "INEP IDEB 2021 e OECD Education at a Glance 2024 confirmam..."
    recall = compute_source_recall(text, ["INEP", "OECD"])
    assert recall == 1.0


def test_recall_trivial_quando_lista_vazia() -> None:
    assert compute_source_recall("qualquer coisa", []) == 1.0


# ----------------------------------------------------------------------
# Casos adversariais
# ----------------------------------------------------------------------


def test_resposta_sem_nenhuma_fonte_citada() -> None:
    text = "O Brasil teve nota baixa em Matematica no PISA 2022."
    # PISA conta como fonte canonica neste schema (substring match), entao isolamos
    text2 = "O Brasil teve nota baixa em Matematica em 2022."
    recall = compute_source_recall(text2, ["OECD", "IBGE"])
    assert recall == 0.0


def test_recall_parcial() -> None:
    text = "OCDE relatou queda generalizada em Matematica."
    recall = compute_source_recall(text, ["OECD", "IBGE"])
    assert recall == pytest.approx(0.5)


def test_aliases_case_insensitive() -> None:
    text = "ibge informou que a taxa caiu para 5,6%."
    recall = compute_source_recall(text, ["IBGE"])
    assert recall == 1.0


def test_fonte_inventada_nao_quebra() -> None:
    """Se sources_required contem string que nao bate aliases, conta como nao requerida."""
    text = "OECD disse algo."
    recall = compute_source_recall(text, ["OECD", "Universidade-Fake"])
    # Universidade-Fake nao tem alias -> e descartada -> requirements = {OECD}
    assert recall == 1.0
