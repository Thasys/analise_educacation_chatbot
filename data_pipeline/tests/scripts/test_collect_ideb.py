"""Smoke tests do script `src/scripts/collect_ideb.py`.

Cobre apenas o catalogo e o filtro CLI — a I/O real (httpx + pandas +
BronzeWriter) e exercitada ad-hoc; um teste end-to-end com mock client
fica em test_ideb.py (do coletor generico). Aqui validamos que o catalogo
permanece consistente (3 etapas x 2 ciclos = 6 entradas) e que o filtro
por etapa/ciclo nao quebra.
"""

from __future__ import annotations

import pytest

from src.scripts.collect_ideb import CATALOG, _select_specs


def test_catalog_covers_three_etapas_two_ciclos() -> None:
    assert len(CATALOG) == 6
    etapas = {s.etapa for s in CATALOG}
    ciclos = {s.ciclo for s in CATALOG}
    assert etapas == {"AI", "AF", "EM"}
    assert ciclos == {2019, 2021}


def test_catalog_urls_follow_inep_pattern() -> None:
    for spec in CATALOG:
        assert spec.url.startswith(
            "https://download.inep.gov.br/educacao_basica/portal_ideb/"
        )
        assert spec.url.endswith(f"_{spec.ciclo}.xlsx")
        # Header tecnico fica sempre na linha 9 das planilhas municipais
        # (linhas 0-8 sao titulo + cabecalho descritivo multi-nivel).
        assert spec.header_row == 9


def test_catalog_dataset_slugs_match_etapa() -> None:
    expected = {
        "AI": "ideb_anos_iniciais",
        "AF": "ideb_anos_finais",
        "EM": "ideb_ensino_medio",
    }
    for spec in CATALOG:
        assert spec.dataset == expected[spec.etapa]


@pytest.mark.parametrize(
    ("etapa", "ciclo", "expected"),
    [
        (None, None, 6),
        ("AI", None, 2),
        ("EM", None, 2),
        (None, 2019, 3),
        (None, 2021, 3),
        ("AF", 2019, 1),
        ("EM", 2021, 1),
    ],
)
def test_select_specs_filter(etapa: str | None, ciclo: int | None, expected: int) -> None:
    selected = _select_specs(CATALOG, etapa=etapa, ciclo=ciclo)
    assert len(selected) == expected
    if etapa is not None:
        assert all(s.etapa == etapa for s in selected)
    if ciclo is not None:
        assert all(s.ciclo == ciclo for s in selected)
