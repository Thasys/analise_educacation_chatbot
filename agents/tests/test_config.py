"""Sprint 5.0 — testes de Settings."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from src.config import Settings


def test_settings_defaults():
    s = Settings(_env_file=None)
    assert s.project_name == "analise-education-chatbot"
    assert s.gateway_base_url.startswith("http://")
    assert s.llm_smart_model.startswith("claude-sonnet")
    assert s.llm_fast_model.startswith("claude-haiku")
    assert s.rag_default_k >= 1


def test_has_anthropic_key_false_when_unset():
    s = Settings(_env_file=None, anthropic_api_key=None)
    assert s.has_anthropic_key is False


def test_has_anthropic_key_false_when_placeholder():
    s = Settings(_env_file=None, anthropic_api_key=SecretStr("sk-ant-..."))
    assert s.has_anthropic_key is False


def test_has_anthropic_key_true_when_real_value(monkeypatch: pytest.MonkeyPatch):
    # pydantic-settings 2.10: env var via validation_alias sobrescreve init kwarg.
    # Para testar com kwarg precisamos limpar o ambiente antes.
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AGENTS_ANTHROPIC_API_KEY", raising=False)
    s = Settings(_env_file=None, anthropic_api_key=SecretStr("sk-ant-real-key-abc123"))
    assert s.has_anthropic_key is True


def test_llm_for_role():
    s = Settings(_env_file=None)
    assert s.llm_for("fast") == s.llm_fast_model
    assert s.llm_for("smart") == s.llm_smart_model


def test_has_langfuse_false_by_default():
    s = Settings(_env_file=None)
    assert s.has_langfuse is False


def test_temperature_validation():
    with pytest.raises(ValueError):
        Settings(_env_file=None, llm_temperature=1.5)


def test_max_tokens_validation():
    with pytest.raises(ValueError):
        Settings(_env_file=None, llm_max_tokens=10)
