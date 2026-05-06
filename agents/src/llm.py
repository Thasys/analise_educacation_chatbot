"""Factory de LLMs CrewAI para os agentes.

Centraliza a criacao de instancias `crewai.LLM` por papel (`fast` ou
`smart`), aplicando temperature/max_tokens das settings. Em testes,
basta `monkeypatch.setattr` em `LLM.call` ou usar a fixture
`mock_llm_call` do conftest.

Mapeamento (ver `fase-5-analise.md` secao 3.2):

- `fast`  -> Haiku 4.5 (Orchestrator, Profiler, Retriever, Citation,
   Visualizer)
- `smart` -> Sonnet 4.5 (Statistician, Comparativist, Synthesizer)
"""

from __future__ import annotations

import os
from typing import Literal

from crewai import LLM

from src.config import settings


LLMRole = Literal["fast", "smart"]


def _ensure_anthropic_env() -> None:
    """Espelha settings.anthropic_api_key em ANTHROPIC_API_KEY do processo.

    A SDK nativa Anthropic usada pela CrewAI le de `os.environ` na criacao
    do client. Se a chave estiver definida apenas via Pydantic Settings
    (carregada do .env), precisamos exporta-la antes.
    """
    if "ANTHROPIC_API_KEY" in os.environ and os.environ["ANTHROPIC_API_KEY"].strip():
        return
    if settings.anthropic_api_key is None:
        return
    secret = settings.anthropic_api_key.get_secret_value().strip()
    if secret and not secret.startswith("sk-ant-..."):
        os.environ["ANTHROPIC_API_KEY"] = secret


def make_llm(role: LLMRole, *, temperature: float | None = None) -> LLM:
    """Constroi um `crewai.LLM` para o papel solicitado.

    Args:
        role: 'fast' (Haiku 4.5) ou 'smart' (Sonnet 4.5).
        temperature: override; se None, usa `settings.llm_temperature`.
    """
    _ensure_anthropic_env()
    model_id = settings.llm_for(role)
    return LLM(
        model=f"anthropic/{model_id}",
        temperature=temperature if temperature is not None else settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
