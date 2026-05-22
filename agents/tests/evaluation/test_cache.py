"""Unit tests para `evaluation.shared.cache`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluation.shared import cache


def test_cache_key_determinismo() -> None:
    """Mesmas entradas geram mesmo hash."""
    k1 = cache.cache_key(
        "Qual o IDEB de 2021?",
        mode="eduquery",
        model_smart="claude-sonnet-4-5",
        model_fast="claude-haiku-4-5",
        marts_version="abc123",
    )
    k2 = cache.cache_key(
        "Qual o IDEB de 2021?",
        mode="eduquery",
        model_smart="claude-sonnet-4-5",
        model_fast="claude-haiku-4-5",
        marts_version="abc123",
    )
    assert k1 == k2
    assert len(k1) == 16


def test_cache_key_diferente_para_query_diferente() -> None:
    k1 = cache.cache_key("query A", mode="eduquery",
                          model_smart="X", model_fast="Y", marts_version="v1")
    k2 = cache.cache_key("query B", mode="eduquery",
                          model_smart="X", model_fast="Y", marts_version="v1")
    assert k1 != k2


def test_cache_key_diferente_para_mart_version() -> None:
    """Mudanca de marts invalida cache."""
    k1 = cache.cache_key("Q", mode="eduquery",
                          model_smart="X", model_fast="Y", marts_version="v1")
    k2 = cache.cache_key("Q", mode="eduquery",
                          model_smart="X", model_fast="Y", marts_version="v2")
    assert k1 != k2


def test_cache_key_diferente_para_modelo() -> None:
    k1 = cache.cache_key("Q", mode="eduquery",
                          model_smart="sonnet-4-5", model_fast="haiku-4-5",
                          marts_version="v1")
    k2 = cache.cache_key("Q", mode="eduquery",
                          model_smart="sonnet-4-6", model_fast="haiku-4-5",
                          marts_version="v1")
    assert k1 != k2


def test_get_miss(tmp_path: Path) -> None:
    assert cache.get(tmp_path, "naoexiste") is None


def test_put_then_get_roundtrip(tmp_path: Path) -> None:
    payload = {"id": "F-001", "classification": "correct", "actual_value": 379}
    cache.put(tmp_path, "abc123", payload)
    got = cache.get(tmp_path, "abc123")
    assert got is not None
    assert got["id"] == "F-001"
    assert got["classification"] == "correct"
    assert got["_cache_hit"] is True


def test_put_ignora_flag_cache_hit(tmp_path: Path) -> None:
    """Cache nao deve persistir a flag _cache_hit que ele mesmo injeta."""
    payload = {"id": "F-001", "_cache_hit": True}
    cache.put(tmp_path, "k", payload)
    raw = json.loads((tmp_path / "cache" / "k.json").read_text(encoding="utf-8"))
    assert "_cache_hit" not in raw
