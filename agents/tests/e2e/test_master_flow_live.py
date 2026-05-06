"""Sprint 5.6 — suite LIVE com chamadas Anthropic reais.

Por DEFAULT estes testes sao SKIPADOS. Para rodar:

    pytest -m live agents/tests/e2e/

Pre-requisitos:
  - ANTHROPIC_API_KEY valida no .env (nao placeholder).
  - Gateway HTTP em http://localhost:8000 NAO eh exigido — usamos
    httpx.MockTransport para isolar a parte de rede do gateway, mas o
    LLM bate na Anthropic real.
  - RAG em memoria com seeds (StubEmbedding ja basta para testes
    deterministicos).

Custo esperado por teste: ~$0.05-0.10 (Sonnet 4.5 + Haiku 4.5 mix).
Latencia esperada: ~30-60s por teste com Anthropic real.

Asserts SOFT: validamos estrutura e presenca de dados, nao conteudo
exato (LLM eh nao-deterministico).
"""

from __future__ import annotations

import os
import time

import httpx
import pytest

from src.api_client import EduGatewayClient
from src.crews import run_master
from src.schemas import FinalAnswer


pytestmark = pytest.mark.live


def _has_real_anthropic_key() -> bool:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return bool(key) and not key.startswith("sk-ant-...") and not key.startswith("sk-ant-test")


@pytest.fixture(scope="module")
def _check_api_key():
    if not _has_real_anthropic_key():
        pytest.skip(
            "ANTHROPIC_API_KEY ausente ou placeholder — pulando suite live."
        )


@pytest.fixture
def gateway_with_compare_payload(sample_compare_payload):
    """Gateway local mock — apenas o /api/data/compare retorna dados."""
    def handler(req: httpx.Request) -> httpx.Response:
        if req.method == "POST" and req.url.path == "/api/data/compare":
            return httpx.Response(200, json=sample_compare_payload)
        return httpx.Response(404, json={"detail": "live test mock"})

    return EduGatewayClient(transport=httpx.MockTransport(handler))


def test_live_data_flow_returns_final_answer(
    _check_api_key, gateway_with_compare_payload, rag_client_in_memory
):
    """Fluxo `data` end-to-end com Anthropic real."""
    started = time.perf_counter()
    final = run_master(
        "Como o Brasil se compara com a Finlandia em gasto educacional em 2020?",
        gateway_client=gateway_with_compare_payload,
        rag_client=rag_client_in_memory,
    )
    elapsed = time.perf_counter() - started

    assert isinstance(final, FinalAnswer)
    # Asserts SOFT — LLM eh nao-deterministico
    assert final.flow_used in {"data", "deep"}, f"esperado data/deep, foi {final.flow_used}"
    assert len(final.markdown) > 100, "markdown muito curto"
    assert "BR" in final.markdown.upper() or "Brasil" in final.markdown
    assert len(final.visualizations) >= 1, "esperado ≥1 viz"
    # Latencia esperada ate ~120s na primeira execucao (cold cache)
    assert elapsed < 180, f"latencia muito alta: {elapsed:.1f}s"
    print(
        f"\n[live] data flow OK em {elapsed:.1f}s — "
        f"perfil={final.profile_used}, citations={len(final.citations)}, "
        f"viz={final.visualizations[0].chart_type if final.visualizations else 'none'}"
    )


def test_live_simple_flow_returns_conceptual_answer(
    _check_api_key, rag_client_in_memory
):
    """Fluxo `simple` (conceitual): pergunta sobre ISCED.

    Nao precisa de gateway — pula Retriever/Statistician.
    """
    started = time.perf_counter()
    final = run_master(
        "O que significa ISCED 2011 e por que ele eh importante para "
        "comparacoes internacionais?",
        rag_client=rag_client_in_memory,
    )
    elapsed = time.perf_counter() - started

    assert final.flow_used in {"simple", "data"}  # Orchestrator pode escolher data tambem
    assert "ISCED" in final.markdown.upper()
    assert elapsed < 120
    print(
        f"\n[live] simple flow OK em {elapsed:.1f}s — "
        f"perfil={final.profile_used}, len(md)={len(final.markdown)}"
    )
