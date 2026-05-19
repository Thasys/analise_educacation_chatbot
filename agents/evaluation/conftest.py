"""Fixtures pytest para o pacote `agents/evaluation/`.

Centraliza o carregamento dos YAMLs de golden e os caminhos
canonicos. Usado tanto pelos unit tests das metricas (puros) quanto
pelos runners reais (Fase 2+).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

# pyyaml e dependencia da extra `rag` (ja presente em
# `agents/pyproject.toml`). Caso o ambiente nao tenha, falha cedo com
# mensagem clara ao inves de explodir no meio do teste.
try:
    import yaml  # type: ignore[import-untyped]
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "pyyaml ausente. Instale via `uv pip install pyyaml` ou "
        "`uv sync --extra rag` dentro de agents/."
    ) from e


GOLDEN_DIR = Path(__file__).parent / "golden"


def _load_yaml(path: Path) -> list[dict[str, Any]]:
    """Carrega um YAML de lista. Falha em arquivo vazio ou nao-lista."""
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path}: esperava lista; achou {type(data).__name__}")
    return data


@pytest.fixture(scope="session")
def golden_dir() -> Path:
    """Diretorio raiz dos golden datasets."""
    return GOLDEN_DIR


@pytest.fixture(scope="session")
def queries_factuais() -> list[dict[str, Any]]:
    """Items de `queries_factuais.yaml`."""
    return _load_yaml(GOLDEN_DIR / "queries_factuais.yaml")


@pytest.fixture(scope="session")
def queries_comparativas() -> list[dict[str, Any]]:
    """Items de `queries_comparativas.yaml`."""
    return _load_yaml(GOLDEN_DIR / "queries_comparativas.yaml")


@pytest.fixture(scope="session")
def adversarial() -> list[dict[str, Any]]:
    """Items de `adversarial.yaml`."""
    return _load_yaml(GOLDEN_DIR / "adversarial.yaml")


@pytest.fixture(scope="session")
def all_golden_items(
    queries_factuais: list[dict[str, Any]],
    queries_comparativas: list[dict[str, Any]],
    adversarial: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Conjunto unificado dos 3 YAMLs (factuais + comparativos + adversariais)."""
    return [*queries_factuais, *queries_comparativas, *adversarial]
