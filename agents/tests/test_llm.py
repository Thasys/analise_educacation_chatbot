"""Sprint 5.1 — testes da factory de LLM."""

from __future__ import annotations

import os

import pytest
from crewai import BaseLLM

from src.llm import _ensure_anthropic_env, make_llm


@pytest.fixture(autouse=True)
def _fake_anthropic_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key-fake")
    yield


def test_make_llm_fast_returns_haiku():
    """`crewai.LLM` e factory: para Anthropic devolve `AnthropicCompletion`,
    subclasse de `BaseLLM`. Validamos a interface comum.
    """
    llm = make_llm("fast")
    assert isinstance(llm, BaseLLM)
    assert "haiku" in llm.model.lower()


def test_make_llm_smart_returns_sonnet():
    llm = make_llm("smart")
    assert isinstance(llm, BaseLLM)
    assert "sonnet" in llm.model.lower()


def test_make_llm_temperature_override():
    llm = make_llm("fast", temperature=0.7)
    assert llm.temperature == 0.7


def test_make_llm_uses_anthropic_provider():
    """Native provider strip 'anthropic/' do model, mas `provider` retem."""
    llm = make_llm("smart")
    assert getattr(llm, "provider", None) == "anthropic"


def test_ensure_anthropic_env_no_op_when_set():
    """Quando ANTHROPIC_API_KEY ja existe, nao sobrescreve."""
    os.environ["ANTHROPIC_API_KEY"] = "preexisting-value"
    _ensure_anthropic_env()
    assert os.environ["ANTHROPIC_API_KEY"] == "preexisting-value"
