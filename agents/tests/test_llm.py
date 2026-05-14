"""Sprint 5.1 — testes da factory de LLM.

Apos a refatoracao multi-provider (Sprint 5.x), a factory `make_llm` e
provider-agnostica: o provider ativo vem de `settings.llm_provider` e a
chave da env var apropriada para cada provider. Os testes parametrizam
os providers comuns para garantir que o prefixo do modelo, a chave e o
`api_base` opcional sao propagados corretamente.
"""

from __future__ import annotations

import importlib
import os

import pytest
from crewai import BaseLLM


@pytest.fixture
def reload_llm_module(monkeypatch: pytest.MonkeyPatch):
    """Recarrega `src.config` e `src.llm` apos mudar variaveis de ambiente.

    `Settings` e `settings` sao construidos em tempo de import e cacheados
    via `lru_cache`. Para testar configuracoes alternativas precisamos
    recarregar os modulos depois de setar as envs.
    """

    def _reload():
        import src.config as config_module
        import src.llm as llm_module

        config_module.get_settings.cache_clear()
        importlib.reload(config_module)
        importlib.reload(llm_module)
        return llm_module

    return _reload


# ---------------------------------------------------------------------------
# Anthropic (default) — preserva contrato historico
# ---------------------------------------------------------------------------


@pytest.fixture
def anthropic_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENTS_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("AGENTS_LLM_API_KEY", "sk-ant-test-key-fake")
    monkeypatch.delenv("AGENTS_LLM_API_BASE", raising=False)
    yield


def test_make_llm_fast_returns_haiku(anthropic_env, reload_llm_module):
    """`crewai.LLM` e factory: para Anthropic devolve `AnthropicCompletion`,
    subclasse de `BaseLLM`. Validamos a interface comum.
    """
    llm = reload_llm_module().make_llm("fast")
    assert isinstance(llm, BaseLLM)
    assert "haiku" in llm.model.lower()


def test_make_llm_smart_returns_sonnet(anthropic_env, reload_llm_module):
    llm = reload_llm_module().make_llm("smart")
    assert isinstance(llm, BaseLLM)
    assert "sonnet" in llm.model.lower()


def test_make_llm_temperature_override(anthropic_env, reload_llm_module):
    llm = reload_llm_module().make_llm("fast", temperature=0.7)
    assert llm.temperature == 0.7


def test_make_llm_uses_anthropic_provider(anthropic_env, reload_llm_module):
    """Native provider strip 'anthropic/' do model, mas `provider` retem."""
    llm = reload_llm_module().make_llm("smart")
    assert getattr(llm, "provider", None) == "anthropic"


def test_ensure_provider_env_no_op_when_set(anthropic_env, reload_llm_module):
    """Quando ANTHROPIC_API_KEY ja existe, nao sobrescreve."""
    os.environ["ANTHROPIC_API_KEY"] = "preexisting-value"
    llm_module = reload_llm_module()
    llm_module._ensure_provider_env()
    assert os.environ["ANTHROPIC_API_KEY"] == "preexisting-value"


def test_ensure_anthropic_env_alias_still_works(anthropic_env, reload_llm_module):
    """`_ensure_anthropic_env` permanece como alias retrocompat."""
    llm_module = reload_llm_module()
    assert llm_module._ensure_anthropic_env is not None
    # Deve aceitar a chamada sem argumentos sem levantar.
    llm_module._ensure_anthropic_env()


# ---------------------------------------------------------------------------
# Ollama — provider local, sem chave, com api_base
# ---------------------------------------------------------------------------


@pytest.fixture
def ollama_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENTS_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("AGENTS_LLM_SMART_MODEL", "llama3.1:70b")
    monkeypatch.setenv("AGENTS_LLM_FAST_MODEL", "llama3.1:8b")
    monkeypatch.setenv("AGENTS_LLM_API_BASE", "http://localhost:11434")
    monkeypatch.delenv("AGENTS_LLM_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    yield


def test_make_llm_ollama_uses_local_endpoint(ollama_env, reload_llm_module):
    llm = reload_llm_module().make_llm("smart")
    assert isinstance(llm, BaseLLM)
    assert "llama3.1:70b" in llm.model
    # `api_base` deve ser propagado para o cliente LiteLLM.
    assert getattr(llm, "api_base", None) == "http://localhost:11434"


def test_make_llm_ollama_does_not_require_key(ollama_env, reload_llm_module):
    """Ollama nao precisa de chave — factory nao deve levantar."""
    llm_module = reload_llm_module()
    llm_module._ensure_provider_env()  # no-op para ollama
    llm = llm_module.make_llm("fast")
    assert "llama3.1:8b" in llm.model


# ---------------------------------------------------------------------------
# OpenAI — sanity check do prefixo provider/model
# ---------------------------------------------------------------------------


@pytest.fixture
def openai_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENTS_LLM_PROVIDER", "openai")
    monkeypatch.setenv("AGENTS_LLM_SMART_MODEL", "gpt-4o")
    monkeypatch.setenv("AGENTS_LLM_FAST_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("AGENTS_LLM_API_KEY", "sk-openai-fake")
    monkeypatch.delenv("AGENTS_LLM_API_BASE", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    yield


def test_make_llm_openai_exports_api_key(openai_env, reload_llm_module):
    """Settings -> os.environ['OPENAI_API_KEY'] deve ser espelhado."""
    llm_module = reload_llm_module()
    llm_module._ensure_provider_env()
    assert os.environ.get("OPENAI_API_KEY") == "sk-openai-fake"


def test_make_llm_openai_returns_openai_model(openai_env, reload_llm_module):
    llm = reload_llm_module().make_llm("smart")
    assert isinstance(llm, BaseLLM)
    assert "gpt-4o" in llm.model
