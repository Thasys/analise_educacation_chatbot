"""Conftest local para `tests/evaluation/`.

Reexporta as fixtures de carregamento de YAML definidas em
`evaluation/conftest.py`. Mantemos o fixture sob session-scope para
que ler os YAMLs aconteca uma unica vez por suite.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

GOLDEN_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "golden"


def _load(name: str) -> list[dict[str, Any]]:
    with (GOLDEN_DIR / name).open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list):
        raise ValueError(f"{name}: esperava lista; achou {type(data).__name__}")
    return data


@pytest.fixture(scope="session")
def queries_factuais() -> list[dict[str, Any]]:
    return _load("queries_factuais.yaml")


@pytest.fixture(scope="session")
def queries_comparativas() -> list[dict[str, Any]]:
    return _load("queries_comparativas.yaml")


@pytest.fixture(scope="session")
def adversarial() -> list[dict[str, Any]]:
    return _load("adversarial.yaml")
