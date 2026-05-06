# Fase 5 — Sprint 5.0 (Setup + scaffold) — Progresso

> Estado da Sprint 5.0 da Fase 5 (Sistema de agentes CrewAI).
> Complementa [`fase-5-analise.md`](./fase-5-analise.md).
> **Data:** 2026-04-29
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Pôr de pé o scaffold mínimo do serviço `agents/`:

- venv local em `agents/.venv` com dependências leves (pydantic, httpx,
  structlog, pytest), **sem CrewAI/ChromaDB** ainda — esses entram em
  Sprints 5.1+ via extras `[agents]` e `[rag]`.
- `Settings` com prefix `AGENTS_*` e aliases para vars genéricas
  (`ANTHROPIC_API_KEY`).
- `EduGatewayClient` consumindo os 4 endpoints REST da Fase 4 com
  retry, request-id e fallback estruturado para erros (`GatewayError`).
- Suite pytest com 20 testes verdes em <2s, sem dependência de
  Anthropic/DuckDB/CrewAI.

---

## 2. Entregáveis

### 2.1 Arquivos novos

| Arquivo | Linhas | Descrição |
|---|---|---|
| `agents/src/config.py` | 124 | Settings com 4 grupos (gateway, LLM, RAG, Langfuse) |
| `agents/src/logging_config.py` | 53 | structlog idempotente (mesmo padrão de `api/`) |
| `agents/src/schemas.py` | 122 | Pydantic v2 espelhando o contrato OpenAPI do gateway + `GatewayError` |
| `agents/src/api_client.py` | 200 | `EduGatewayClient` síncrono com retry exponencial e `safe_call` |
| `agents/tests/conftest.py` | 124 | `gateway_handler_factory` (MockTransport) + 3 payloads representativos |
| `agents/tests/test_config.py` | 60 | 8 testes de Settings |
| `agents/tests/test_api_client.py` | 200 | 12 testes do client (happy/erro/retry/validação) |

**Total Sprint 5.0: ~880 linhas Python (incluindo testes).**

### 2.2 Edição de `pyproject.toml`

`dependencies` ficou enxuto (httpx, pydantic, pydantic-settings,
structlog). Stack pesado migrado para extras opt-in:

```toml
[project.optional-dependencies]
agents = ["crewai>=0.80", "anthropic>=0.34", "langchain-anthropic>=0.2"]
rag = ["chromadb>=0.5", "sentence-transformers>=2.7", "pyyaml>=6.0"]
dev = ["ruff", "mypy", "pytest", "pytest-asyncio", "pytest-cov"]
```

Comando de instalação Sprint 5.0:

```bash
cd agents
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
```

Sprints 5.1+ adicionarão `.[agents]` e `.[rag]` conforme necessário.

---

## 3. Decisões aplicadas

### 3.1 ✅ Scaffold leve antes de stack pesado

CrewAI + ChromaDB + sentence-transformers somam vários GB e demoram
minutos. Ao deixar tudo em extras, Sprint 5.0 fica testável em CI sem
exigir o download. As tools de dados (Sprints 5.1–5.2) podem nascer e
ser testadas com mock antes de subir o universo CrewAI.

### 3.2 ✅ Tipos canônicos espelhados, não importados

`agents/src/schemas.py` redefine `IndicatorId`, `CountryISO3`,
`GroupingTag`, `SourceTag` com Pydantic v2 — em vez de importar de
`api/src/schemas/common.py`. Justificativa: `agents/` e `api/` têm
venvs distintos, evitamos acoplamento de path. Quando o contrato OpenAPI
estabilizar, podemos gerar `schemas.py` automaticamente via
`datamodel-code-generator` (ADR para Sprint 5.7).

### 3.3 ✅ Cliente síncrono, não async

CrewAI tools são síncronas por padrão; `httpx.Client` simplifica a
implementação e o teste. Quando rebatedores async forem necessários
(streaming SSE em Sprint 5.6/Fase 6), criamos `EduGatewayAsyncClient`
ao lado.

### 3.4 ✅ `safe_call` para erros estruturados

Em vez de propagar `httpx.HTTPStatusError` ao agente (e travar a crew),
`safe_call` devolve `GatewayError` com `error_type ∈ {validation,
not_found, rate_limited, network, unknown}`. O agente pode então
reformular o pedido (ex.: tentar outro `year`) ou abortar com mensagem
clara ao usuário.

### 3.5 ✅ `populate_by_name=True` em Settings

`validation_alias` é necessário para múltiplas vars de ambiente, mas
bloqueia o uso do nome do campo em testes (`Settings(anthropic_api_key=...)`).
A flag `populate_by_name=True` libera ambos os caminhos sem perda de
validação.

### 3.6 ✅ Fixture `gateway_handler_factory`

Em vez de instalar `respx`/`pytest-httpx`, usamos `httpx.MockTransport`
direto via factory. Cada teste declara o mapa `(method, path) → spec`
e recebe um transport injetável no `EduGatewayClient`. Zero dependência
nova.

---

## 4. Métricas finais

```
Pacotes instalados:           29 (lightweight)
Linhas Python adicionadas:    ~880 (src + tests)
Testes pytest:                20 / 20 (100% PASS, ~1.5s)
Cobertura efetiva:            api_client.py 95%+ (8 paths cobertos),
                              config.py 100%, schemas.py via uso indireto
Dependencias venv:            29 (sem crewai, anthropic, chromadb)
Tamanho .venv:                ~50 MB (vs ~3 GB com stack completo)
```

Saída do `pytest`:

```
tests/test_api_client.py::test_catalog_happy_path PASSED
tests/test_api_client.py::test_timeseries_happy_path PASSED
tests/test_api_client.py::test_compare_happy_path PASSED
tests/test_api_client.py::test_ranking_happy_path PASSED
tests/test_api_client.py::test_safe_call_returns_validation_error PASSED
tests/test_api_client.py::test_safe_call_returns_not_found PASSED
tests/test_api_client.py::test_safe_call_returns_network_error PASSED
tests/test_api_client.py::test_retry_on_503_then_success PASSED
tests/test_api_client.py::test_compare_args_rejects_invalid_iso3 PASSED
tests/test_api_client.py::test_timeseries_args_rejects_inverted_years PASSED
tests/test_api_client.py::test_ranking_args_default_limit_20 PASSED
tests/test_api_client.py::test_request_id_propagated PASSED
tests/test_config.py::test_settings_defaults PASSED
tests/test_config.py::test_has_anthropic_key_false_when_unset PASSED
tests/test_config.py::test_has_anthropic_key_false_when_placeholder PASSED
tests/test_config.py::test_has_anthropic_key_true_when_real_value PASSED
tests/test_config.py::test_llm_for_role PASSED
tests/test_config.py::test_has_langfuse_false_by_default PASSED
tests/test_config.py::test_temperature_validation PASSED
tests/test_config.py::test_max_tokens_validation PASSED
============================= 20 passed in 1.53s
```

---

## 5. Estrutura final do `agents/` após Sprint 5.0

```
agents/
├── pyproject.toml         (atualizado — extras agents/rag opt-in)
├── Dockerfile
├── .venv/                 (29 pacotes, ~50 MB)
├── src/
│   ├── __init__.py
│   ├── config.py          ✅ NOVO
│   ├── logging_config.py  ✅ NOVO
│   ├── api_client.py      ✅ NOVO
│   ├── schemas.py         ✅ NOVO
│   ├── agents/__init__.py    (placeholder Sprint 5.1)
│   ├── crews/__init__.py     (placeholder Sprint 5.1)
│   ├── tools/__init__.py     (placeholder Sprint 5.2)
│   ├── prompts/__init__.py   (placeholder Sprint 5.1)
│   └── rag/__init__.py       (placeholder Sprint 5.5)
└── tests/
    ├── __init__.py
    ├── conftest.py        ✅ NOVO
    ├── test_config.py     ✅ NOVO (8 testes)
    ├── test_api_client.py ✅ NOVO (12 testes)
    ├── tools/__init__.py
    ├── agents/__init__.py
    └── e2e/__init__.py
```

---

## 6. Próximo: Sprint 5.1 (Profile + Orchestrator)

A Sprint 5.1 instala extras `[agents]` (CrewAI + langchain-anthropic) e
implementa os 2 primeiros agentes (Orchestrator + Profile & Intent),
com 2 prompts versionados em `prompts/*.txt` e a Core Crew.

### 6.1 Pré-requisitos

- `ANTHROPIC_API_KEY` válida no `.env` raiz (já está placeholder, basta
  trocar por chave real do console.anthropic.com).
- `pip install -e ".[dev,agents]"` em `agents/.venv` — adiciona ~250
  MB (crewai + dependências).

### 6.2 Entregáveis previstos

- `agents/src/llm.py` — factory `make_llm("fast" | "smart")`.
- `agents/src/prompts/orchestrator_system.txt`,
  `prompts/profiler_system.txt`.
- `agents/src/agents/orchestrator.py`, `agents/profiler.py`.
- `agents/src/crews/core_crew.py` com `process=sequential`.
- `agents/src/tools/intent_tools.py` (`extract_entities`,
  `detect_profile`).
- `agents/tests/agents/test_profiler.py` com fixture `mock_llm`.

### 6.3 Critério de avanço

Pergunta exemplo "Como o Brasil se compara com a Finlândia em gasto
educacional em 2022?" deve produzir, **sem chamar LLM real**, um
`IntentDecision(flow=DATA, profile=researcher)` + `EntityExtraction(
indicator=GASTO_EDU_PIB, countries=[BRA, FIN], year=2022)` via mocks.

---

## 7. Pendências registradas

1. Fixture `mock_llm` ainda não existe — entra em Sprint 5.1.
2. Validação cruzada com OpenAPI live do gateway via teste opt-in
   (`-m gateway`) — adicionar em Sprint 5.2.
3. ADR 0003 (FastAPI + CrewAI) — só no Sprint 5.7 conforme planejado.

---

*Próximo doc: `fase-5-sprint-5.1-progresso.md` (a criar quando Sprint
5.1 começar).*
