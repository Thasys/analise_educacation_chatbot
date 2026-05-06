# Fase 5 — Sprint 5.1 (Profile + Orchestrator) — Progresso

> Estado da Sprint 5.1 da Fase 5 (Sistema de agentes CrewAI).
> Complementa [`fase-5-analise.md`](./fase-5-analise.md) e
> [`fase-5-sprint-5.0-progresso.md`](./fase-5-sprint-5.0-progresso.md).
> **Data:** 2026-04-29
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Implementar os 2 primeiros agentes da Core Crew, com prompts versionados
e crew orquestrada via CrewAI 1.14, **sem custo Anthropic** nos testes.

- **Orchestrator Agent** — classifica fluxo (`simple|data|deep`) +
  perfil (`researcher|policy|student`).
- **Profile & Intent Agent** — extrai entidades (indicador canônico,
  países ISO-3, grouping, ano, janela temporal).

Ambos retornam saída estruturada via `output_pydantic` (Pydantic v2).

---

## 2. Entregáveis

### 2.1 Arquivos novos

| Arquivo | Linhas | Descrição |
|---|---|---|
| `agents/src/llm.py` | 55 | factory `make_llm("fast"|"smart")` retornando CrewAI `LLM` provider Anthropic nativo |
| `agents/src/prompts/orchestrator_system.txt` | 50 | prompt completo do Orchestrator com 3 fluxos, 3 perfis e regras metodológicas críticas |
| `agents/src/prompts/profiler_system.txt` | 65 | prompt do Profiler com mapeamento canônico Brasil/Finlândia/EUA→ISO-3, indicadores, groupings |
| `agents/src/agents/_prompt_loader.py` | 19 | `load_prompt(name)` cacheado lendo `prompts/<name>.txt` |
| `agents/src/agents/orchestrator.py` | 28 | `build_orchestrator() -> Agent` com Haiku 4.5 |
| `agents/src/agents/profiler.py` | 28 | `build_profiler() -> Agent` com Haiku 4.5 |
| `agents/src/agents/__init__.py` | 12 | reexporta `build_orchestrator`, `build_profiler` |
| `agents/src/crews/core_crew.py` | 105 | `build_core_crew(question)` + `run_core_flow(question) -> CoreFlowOutput` com coerção de output Pydantic/string/dict |
| `agents/src/crews/__init__.py` | 11 | reexporta `build_core_crew`, `run_core_flow` |
| `agents/tests/test_llm.py` | 47 | 5 testes da factory de LLM |
| `agents/tests/agents/test_orchestrator_profiler.py` | 145 | 6 testes (build factories + 4 cenários `run_core_flow` com mock) |

### 2.2 Edições

| Arquivo | Mudança |
|---|---|
| `agents/src/config.py` | `llm_fast_model` default ajustado para `claude-haiku-4-5` (sem date suffix) — compatível com CrewAI native provider Anthropic |
| `agents/src/schemas.py` | +`FlowKind`, `ProfileKind`, `IntentDecision`, `EntityExtraction`, `CoreFlowOutput` |
| `agents/tests/conftest.py` | +fixture `mock_llm_call` patcheando `LLM.call` e `AnthropicCompletion.call` (factory routing) |
| `agents/tests/test_config.py` | `test_has_anthropic_key_true_when_real_value` agora limpa env vars antes (workaround pydantic-settings 2.10) |
| `agents/pyproject.toml` | adicionados `filterwarnings` para silenciar `DeprecationWarning` interno do CrewAI 1.14 |

**Total Sprint 5.1: ~520 linhas Python + 115 linhas de prompt.**

---

## 3. Decisões aplicadas

### 3.1 ✅ Prompts em `.txt` carregados pelo factory

Cada agente tem seu `system prompt` em `agents/src/prompts/<role>_system.txt`,
versionado no Git. O factory carrega via `load_prompt(name)` (cached).
Vantagens:

- Edição direta sem mexer em código Python.
- Diffs de PR mostram só a mudança de prompt.
- Permite A/B testing trocando o arquivo (Sprint 5.6).

### 3.2 ✅ `run_core_flow(question)` como ponto de entrada

Em vez de expor `Crew` cru, criamos uma função de alto nível que:

1. Monta a Core Crew para a pergunta.
2. Executa via `crew.kickoff()`.
3. Coalesce a saída: tenta `output.pydantic`, depois `output.raw`
   (string JSON), depois dict bruto. Helpers `_coerce_intent` e
   `_coerce_entities` lidam com cada caso.
4. Retorna `CoreFlowOutput(intent, entities, question)`.

Permite ao master flow (Sprint 5.6) tratar a Core Crew como uma caixa
preta, sem conhecer detalhes do CrewAI.

### 3.3 ✅ LLM factory baseada em prefixo `anthropic/`

`crewai.LLM(model="anthropic/claude-sonnet-4-5", ...)` aciona o
provider nativo Anthropic do CrewAI 1.14, que devolve uma instância
`AnthropicCompletion` (subclasse de `BaseLLM`). Isso é mais rápido que
roteamento via LiteLLM e dá callbacks de tokens nativos para Langfuse.

### 3.4 ⚠️ `mock_llm_call` patcheia 2 classes

CrewAI 1.x tem `LLM` (factory) que retorna `AnthropicCompletion`.
Ambas têm seu próprio override de `.call()`. O fixture do conftest
patcheia AMBAS para garantir intercept independente do roteamento:

```python
monkeypatch.setattr(LLM, "call", fake_call)
monkeypatch.setattr(AnthropicCompletion, "call", fake_call)
```

Quando outras providers entrarem (OpenAI, Gemini), basta extender a
fixture para incluí-las.

### 3.5 ⚠️ pydantic-settings 2.10: env var > init kwarg com `validation_alias`

Descoberto durante a validação dos testes: a downgrade de Pydantic
2.13→2.11 (forçada pelo CrewAI) trouxe pydantic-settings 2.10, que
prioriza env var sobre init kwarg quando o campo tem
`validation_alias`. Solução nos testes: `monkeypatch.delenv` antes de
instanciar `Settings(...)`. Documentado para futuras Sprints.

### 3.6 ✅ Filtro de warnings da CrewAI

CrewAI 1.14 usa `Field(deprecated=...)` em propriedades internas, o
que gera ~70 `DeprecationWarning` por crew kickoff. Filtros em
`pyproject.toml` mantêm a saída limpa sem mascarar warnings novos do
nosso código.

### 3.7 ✅ `IntentDecision` com `confidence`

Adicionado campo `confidence ∈ [0.0, 1.0]` para que o master flow
(Sprint 5.6) possa fallback para Sonnet quando confidence < 0.5
(mitigação R8 do `fase-5-analise.md`).

---

## 4. Métricas finais

```
Pacotes instalados (delta):    +143 (com .[agents] -> crewai 1.14, anthropic 0.97, langchain-anthropic 1.4, etc.)
Tamanho .venv:                 ~1.2 GB (era ~50 MB sem .[agents])
Linhas Python adicionadas:     ~520 (src + tests Sprint 5.1)
Linhas de prompt:              ~115 (orchestrator + profiler)
Testes pytest TOTAL:           31 / 31 PASS (~22s, dominado pelo crew kickoff mockado)
Testes especificos Sprint 5.1: 11 / 11 PASS
Custo Anthropic:               $0.00 (LLM mockado)
```

Saída final do `pytest`:

```
tests/agents/test_orchestrator_profiler.py::test_build_orchestrator_loads_prompt PASSED
tests/agents/test_orchestrator_profiler.py::test_build_profiler_loads_prompt PASSED
tests/agents/test_orchestrator_profiler.py::test_core_flow_data_researcher PASSED
tests/agents/test_orchestrator_profiler.py::test_core_flow_simple_student PASSED
tests/agents/test_orchestrator_profiler.py::test_core_flow_deep_policy PASSED
tests/agents/test_orchestrator_profiler.py::test_core_flow_handles_raw_string_output PASSED
tests/test_api_client.py ............................................. PASSED (12)
tests/test_config.py ........................................... PASSED (8)
tests/test_llm.py ........................................... PASSED (5)
=========================== 31 passed in 22.42s ===========================
```

---

## 5. Estrutura do `agents/` após Sprint 5.1

```
agents/
├── pyproject.toml             (+ filterwarnings)
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── logging_config.py
│   ├── api_client.py          (Sprint 5.0)
│   ├── schemas.py             (Sprint 5.0 + 3 novos schemas)
│   ├── llm.py                 ✅ NOVO
│   ├── agents/
│   │   ├── __init__.py        ✅ NOVO
│   │   ├── _prompt_loader.py  ✅ NOVO
│   │   ├── orchestrator.py    ✅ NOVO
│   │   └── profiler.py        ✅ NOVO
│   ├── crews/
│   │   ├── __init__.py        ✅ NOVO
│   │   └── core_crew.py       ✅ NOVO
│   ├── prompts/
│   │   ├── orchestrator_system.txt  ✅ NOVO
│   │   └── profiler_system.txt      ✅ NOVO
│   ├── tools/                  (vazio, Sprint 5.2)
│   └── rag/                    (vazio, Sprint 5.5)
└── tests/
    ├── conftest.py            (+ mock_llm_call fixture)
    ├── test_config.py         (8 testes)
    ├── test_api_client.py     (12 testes)
    ├── test_llm.py            ✅ NOVO (5 testes)
    └── agents/
        └── test_orchestrator_profiler.py  ✅ NOVO (6 testes)
```

---

## 6. Próximo: Sprint 5.2 (Data Retrieval Agent)

A Sprint 5.2 implementa o agente que **chama os 4 endpoints do gateway**
via tools CrewAI tipadas. É a primeira sprint que conecta agents → API
real e valida ponta a ponta o contrato OpenAPI.

### 6.1 Entregáveis previstos

- `agents/src/tools/data_tools.py` com 4 BaseTool:
  - `data_catalog`
  - `data_timeseries`
  - `data_compare`
  - `data_ranking`
- `agents/src/agents/retriever.py` (build_retriever) — Haiku 4.5.
- `agents/src/prompts/retriever_system.txt`.
- `agents/tests/tools/test_data_tools.py` (≥10 testes com gateway mock).
- `agents/tests/agents/test_retriever.py` (≥3 cenários de uso).

### 6.2 Critério de avanço

Pergunta "compare BR e FIN em gasto educacional 2022" deve, com LLM
mockado:

1. Profiler extrai `EntityExtraction(indicator=GASTO_EDU_PIB,
   countries=[BRA,FIN], year=2022)`.
2. Retriever chama `data_compare(...)` via tool.
3. A tool faz POST ao MockTransport e devolve JSON estruturado.
4. Saída do agente lista 2 países com seus valores.

### 6.3 Riscos antecipados

- **R1** (CrewAI muda API): Sprint 5.1 já validou compatibilidade do
  fixture `mock_llm_call` com a versão 1.14 instalada. Pin em
  `pyproject.toml` será adicionado se algum bug emergir.
- Tools com `args_schema` Pydantic precisam funcionar com o
  validador interno do CrewAI — testar com cenários inválidos para
  garantir 422-like errors no fluxo.

---

## 7. Pendências registradas

1. ⏳ Suite "live" (`-m live`) com chamada Anthropic real só em Sprint 5.6.
2. ⏳ ADR 0003 (FastAPI + CrewAI) — Sprint 5.7.
3. ⚠️ Fluxo `run_core_flow` ainda chama 2 tasks sequencialmente; podem
   rodar em paralelo (`process=Process.sequential` mas sem dependência
   real). Otimização para Sprint 5.6 — economia esperada ~30% latência
   da Core Crew.
4. ⚠️ Telemetria do CrewAI (PostHog) está ligada por default — pode
   gerar tráfego em runtime. Avaliar `CREWAI_DISABLE_TELEMETRY=1` em
   Sprint 5.6.

---

*Próximo doc: `fase-5-sprint-5.2-progresso.md` (a criar quando Sprint
5.2 começar).*
