"""Factory de LLMs CrewAI para os agentes.

Centraliza a criacao de instancias `crewai.LLM` por papel (`fast` ou
`smart`), aplicando temperature/max_tokens das settings. Em testes,
basta `monkeypatch.setattr` em `LLM.call` ou usar a fixture
`mock_llm_call` do conftest.

Provider-agnostico: usa LiteLLM por baixo (transitivo da CrewAI), o que
permite trocar de Anthropic Claude para OpenAI, Gemini, Groq, Ollama
(local), vLLM ou OpenRouter apenas via `AGENTS_LLM_PROVIDER`.

Mapeamento por papel (default Claude, ver `fase-5-analise.md` 3.2):

- `fast`  -> modelo barato/rapido (Haiku 4.5, gpt-4o-mini, llama3.1:8b…)
- `smart` -> modelo principal (Sonnet 4.5, gpt-4o, llama3.1:70b…)
"""

from __future__ import annotations

import os
from typing import Literal

from crewai import LLM

from src.config import settings


LLMRole = Literal["fast", "smart"]


# Variavel de ambiente esperada pelo LiteLLM/SDK nativo de cada provider.
# Ollama nao requer chave (servidor local).
_PROVIDER_ENV_VAR: dict[str, str | None] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ollama": None,
}


def _ensure_provider_env() -> None:
    """Espelha settings.llm_api_key na env var esperada pelo provider ativo.

    A SDK nativa de cada provider (Anthropic, OpenAI, etc.) le da
    `os.environ` na criacao do client. Se a chave estiver definida apenas
    via Pydantic Settings (carregada do .env), precisamos exporta-la.
    """
    provider = settings.llm_provider
    env_var = _PROVIDER_ENV_VAR.get(provider)
    if env_var is None:  # Ollama
        return
    if env_var in os.environ and os.environ[env_var].strip():
        return
    if settings.llm_api_key is None:
        return
    secret = settings.llm_api_key.get_secret_value().strip()
    if secret and not secret.startswith("sk-ant-..."):
        os.environ[env_var] = secret


def _ensure_anthropic_env() -> None:
    """Alias retrocompat: codigo/testes legado chamam essa funcao."""
    _ensure_provider_env()


# Providers que devem usar o fallback LiteLLM em vez do native SDK do CrewAI.
# Gemini native (google-genai) tem incompatibilidade com CrewAI Flow em
# contexto sincrono: dispara `RuntimeError: no running event loop` e devolve
# `Invalid response from LLM call - None or empty`. LiteLLM fallback resolve.
# Ver `docs/evaluation/limitations.md` Secao 2.
_FORCE_LITELLM_PROVIDERS = frozenset({"gemini"})


def make_llm(role: LLMRole, *, temperature: float | None = None) -> LLM:
    """Constroi um `crewai.LLM` para o papel solicitado.

    Args:
        role: 'fast' (modelo barato) ou 'smart' (modelo principal).
        temperature: override; se None, usa `settings.llm_temperature`.
    """
    _ensure_provider_env()
    model_id = settings.llm_for(role)
    kwargs: dict[str, object] = {
        "model": f"{settings.llm_provider}/{model_id}",
        "temperature": temperature if temperature is not None else settings.llm_temperature,
        "max_tokens": settings.llm_max_tokens,
    }
    if settings.llm_api_base:
        kwargs["base_url"] = settings.llm_api_base
    if settings.llm_provider in _FORCE_LITELLM_PROVIDERS:
        # Pula o native provider (google-genai) que tem bug async com CrewAI
        # Flow. LiteLLM funciona corretamente.
        kwargs["is_litellm"] = True
    return LLM(**kwargs)
