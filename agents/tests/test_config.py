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


def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Limpa todas as env vars que poderiam mascarar `llm_api_key` via alias."""
    for var in (
        "AGENTS_LLM_API_KEY",
        "AGENTS_ANTHROPIC_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


def test_has_anthropic_key_false_when_unset(monkeypatch: pytest.MonkeyPatch):
    _clear_llm_env(monkeypatch)
    s = Settings(_env_file=None, llm_api_key=None)
    assert s.has_anthropic_key is False
    assert s.has_llm_key is False


def test_has_anthropic_key_false_when_placeholder(monkeypatch: pytest.MonkeyPatch):
    _clear_llm_env(monkeypatch)
    s = Settings(_env_file=None, llm_api_key=SecretStr("sk-ant-..."))
    assert s.has_anthropic_key is False


def test_has_anthropic_key_true_when_real_value(monkeypatch: pytest.MonkeyPatch):
    # pydantic-settings 2.10: env var via validation_alias sobrescreve init kwarg.
    # Para testar com kwarg precisamos limpar o ambiente antes.
    _clear_llm_env(monkeypatch)
    s = Settings(_env_file=None, llm_api_key=SecretStr("sk-ant-real-key-abc123"))
    assert s.has_anthropic_key is True
    # Alias retrocompat: leitura via property continua funcionando.
    assert s.anthropic_api_key is not None
    assert s.anthropic_api_key.get_secret_value() == "sk-ant-real-key-abc123"


def test_has_llm_key_true_for_ollama_without_key(monkeypatch: pytest.MonkeyPatch):
    """Ollama nao requer chave — has_llm_key deve ser True mesmo sem key."""
    _clear_llm_env(monkeypatch)
    s = Settings(_env_file=None, llm_provider="ollama", llm_api_key=None)
    assert s.has_llm_key is True
    assert s.has_anthropic_key is False  # provider != anthropic
    # `anthropic_api_key` legado retorna None quando provider != anthropic
    assert s.anthropic_api_key is None


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
