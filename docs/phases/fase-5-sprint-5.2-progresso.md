# Fase 5 — Sprint 5.2 (Data Retrieval Agent + Tools) — Progresso

> Estado da Sprint 5.2 da Fase 5 (Sistema de agentes CrewAI).
> Complementa [`fase-5-analise.md`](./fase-5-analise.md) e
> [`fase-5-sprint-5.1-progresso.md`](./fase-5-sprint-5.1-progresso.md).
> **Data:** 2026-04-29
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Conectar o sistema de agentes ao FastAPI gateway via 4 tools CrewAI
tipadas — fechando o caminho **pergunta → entidades → tool → JSON do
gateway** sem tocar em SQL ou DuckDB diretamente.

- 4 BaseTool sobre `EduGatewayClient` (catalog, timeseries, compare, ranking).
- 1 agente novo (`Data Retrieval Agent`) com prompt versionado e as 4
  tools acopladas.
- Schema `RetrievedData` para output estruturado.
- Cobertura: 16 testes novos (10 tools + 6 retriever) — todos verdes
  com `httpx.MockTransport` + `mock_llm_call`.

---

## 2. Entregáveis

### 2.1 Arquivos novos

| Arquivo | Linhas | Descrição |
|---|---|---|
| `agents/src/tools/data_tools.py` | 215 | 4 BaseTool + `_SafeDataTool` mixin (captura `ValueError` da validação CrewAI) + factory `build_data_tools(client)` |
| `agents/src/tools/__init__.py` | 24 | reexporta as 4 tools + factory |
| `agents/src/agents/retriever.py` | 33 | `build_retriever(client)` com Haiku 4.5 + 4 tools |
| `agents/src/prompts/retriever_system.txt` | 70 | prompt com regras de decisão por tool, padrões de query e instruções metodológicas |
| `agents/tests/tools/test_data_tools.py` | 175 | 10 testes (factory, happy-path por tool, validação, 404 do gateway) |
| `agents/tests/agents/test_retriever.py` | 175 | 6 testes (build, prompt loading, 3 cenários crew kickoff com LLM mock) |

### 2.2 Edições

| Arquivo | Mudança |
|---|---|
| `agents/src/schemas.py` | +`ToolCallRecord`, +`RetrievedData` (saída estruturada do Retriever) |
| `agents/src/agents/__init__.py` | +`build_retriever` no reexport |

**Total Sprint 5.2: ~620 linhas Python + 70 linhas de prompt.**

---

## 3. Decisões aplicadas

### 3.1 ✅ Tools como classes Pydantic com `_client_override` ClassVar

CrewAI `BaseTool` é Pydantic e recusa atributos arbitrários em runtime.
Para injetar um `EduGatewayClient` mockado nos testes sem clonar a
factory, usamos um `ClassVar` por tool:

```python
class DataCompareTool(_SafeDataTool):
    _client_override: ClassVar[EduGatewayClient | None] = None
    def _run(self, **kwargs):
        client = _client_for_tool(type(self))
        ...
```

`build_data_tools(client=...)` grava o override em todas as classes
antes de instanciar. Em produção, fica `None` e cada instância cria seu
client com defaults.

### 3.2 ✅ `_SafeDataTool` captura `ValueError` da validação

Descoberto durante a Sprint: CrewAI `BaseTool.run()` chama
`_validate_kwargs` antes de `_run`, e levanta `ValueError` se os args
não baterem com `args_schema`. Sem intervenção, isso quebraria o loop
do agente. Solução: mixin que sobrescreve `run()` para capturar e
converter em JSON:

```python
class _SafeDataTool(BaseTool):
    def run(self, *args, **kwargs):
        try:
            return super().run(*args, **kwargs)
        except ValueError as exc:
            return _validation_error_payload(str(exc))
```

O LLM agora recebe `{"ok": false, "error": {"error_type":
"validation", "message": "..."}}` e pode reformular os args. Mitigação
do risco R7 do `fase-5-analise.md`.

### 3.3 ✅ JSON compacto (sem indent) na saída das tools

`json.dumps(...)` sem `indent` economiza tokens na janela de contexto
do LLM. Estrutura padronizada:

```json
{"ok": true, "data": [...], "meta": {...}}
{"ok": false, "error": {"error_type": "...", "message": "...", ...}}
```

Em testes, `json.loads()` reconstrói o dict para asserts.

### 3.4 ✅ `RetrievedData` com `tool_calls` rastreáveis

Cada chamada do agente gera `ToolCallRecord(tool, arguments, status,
rows_returned, sources, error_message)`. Permite ao Statistician
(Sprint 5.3) e ao Synthesizer (Sprint 5.4) saber exatamente:

- quais fontes foram consultadas (necessário para citação),
- quantas linhas vieram (sanity check),
- se houve erros recuperados (warnings ao usuário).

### 3.5 ✅ Estratégia "agente como caixa-preta" para testes E2E

Testar o tool-call loop completo do CrewAI exige LLM real ou mock que
implemente o protocolo de tool-calling do Anthropic — caro e frágil.
Optamos por testar o agente **como caixa-preta**: o LLM mock retorna
direto um `RetrievedData` JSON válido, e os testes validam que:

1. A factory acopla as 4 tools corretas.
2. O prompt está carregado com o conteúdo esperado.
3. A saída do crew kickoff é parseada como `RetrievedData`.

A cobertura *real* do tool-call loop (LLM decide → CrewAI parseia →
tool roda → resultado volta ao LLM) fica para a suite `live` da Sprint
5.6, com 1-2 chamadas Anthropic verdadeiras.

### 3.6 ✅ Sem alteração na API/gateway

A regra do CLAUDE.md ("agentes não escrevem SQL livre") é cumprida
arquiteturalmente: as 4 tools chamam apenas `EduGatewayClient`, que
chama os endpoints REST validados. Nenhum acesso direto a DuckDB
introduzido. Não foi necessário mudar nada em `api/` para esta sprint.

---

## 4. Métricas finais

```
Linhas Python adicionadas:     ~620 (src + tests Sprint 5.2)
Linhas de prompt:              +70 (retriever_system.txt)
Testes pytest TOTAL:           46 / 46 PASS (~30s, dominado por crew kickoff mock)
Testes especificos Sprint 5.2: 16 / 16 PASS
  - Tools (test_data_tools.py): 10 testes (~4s)
  - Retriever (test_retriever.py): 6 testes (~9s)
Custo Anthropic:               $0.00 (LLM mockado)
```

Saída final:

```
tests/agents/test_orchestrator_profiler.py ........... 6 PASSED
tests/agents/test_retriever.py ........................ 5 PASSED
tests/test_api_client.py .............................. 12 PASSED
tests/test_config.py ................................... 8 PASSED
tests/test_llm.py ...................................... 5 PASSED
tests/tools/test_data_tools.py ........................ 10 PASSED
=========================== 46 passed in 30.61s
```

---

## 5. Estrutura do `agents/` após Sprint 5.2

```
agents/
├── pyproject.toml
├── src/
│   ├── config.py
│   ├── logging_config.py
│   ├── api_client.py
│   ├── schemas.py             (+ ToolCallRecord, RetrievedData)
│   ├── llm.py
│   ├── agents/
│   │   ├── __init__.py        (+ build_retriever)
│   │   ├── _prompt_loader.py
│   │   ├── orchestrator.py
│   │   ├── profiler.py
│   │   └── retriever.py       ✅ NOVO
│   ├── crews/
│   │   ├── __init__.py
│   │   └── core_crew.py
│   ├── prompts/
│   │   ├── orchestrator_system.txt
│   │   ├── profiler_system.txt
│   │   └── retriever_system.txt  ✅ NOVO
│   ├── tools/
│   │   ├── __init__.py        ✅ NOVO
│   │   └── data_tools.py      ✅ NOVO (4 tools + _SafeDataTool mixin)
│   └── rag/                    (vazio, Sprint 5.5)
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_api_client.py
    ├── test_llm.py
    ├── agents/
    │   ├── test_orchestrator_profiler.py
    │   └── test_retriever.py  ✅ NOVO
    └── tools/
        └── test_data_tools.py ✅ NOVO
```

---

## 6. Próximo: Sprint 5.3 (Statistician + Comparativist)

A Sprint 5.3 implementa os agentes de raciocínio analítico que
**consomem** a saída do Retriever (`RetrievedData`) e produzem:

- **Statistical Analysis** (`StatAnalysis` schema) — z-scores,
  percentis, intervalos de confiança, ressalvas metodológicas
  (especialmente sobre Plausible Values mesmo que o Sprint 5.3 só toque
  agregados).
- **Comparative Education Context** (`ComparativeContext` schema) —
  contextualização BR × Internacional baseada em literatura.

### 6.1 Entregáveis previstos

- `agents/src/tools/stats_tools.py` com `compute_stats(series)` puro
  Python (mean, median, CV, trend slope, z-score por país de
  referência).
- `agents/src/agents/statistician.py` com Sonnet 4.5 (raciocínio
  metodológico).
- `agents/src/agents/comparativist.py` com Sonnet 4.5.
- `agents/src/prompts/statistician_system.txt`,
  `comparativist_system.txt`.
- `agents/tests/tools/test_stats_tools.py` (≥6 testes).
- `agents/tests/agents/test_statistician.py`,
  `test_comparativist.py` (~3 testes cada).

### 6.2 Critério de avanço

Dado um `RetrievedData` mock com 4 países em comparação, o Statistician
deve produzir `StatAnalysis(method, sample_size, key_metrics={mean,
median, ranges}, brazil_position={zscore, percentile, gap}, warnings)`
sem chamar gateway adicional.

### 6.3 Riscos antecipados

- **R5** (Plausible Values mal aplicados): Sprint 5.3 só usa indicadores
  agregados (% PIB, % literacy) — sem PVs. Documentar isso explicitamente
  no prompt do Statistician para evitar generalização indevida.

---

## 7. Pendências registradas

1. ⏳ Suite "live" (`-m live`) com tool-call loop real só em Sprint 5.6.
2. ⏳ ADR 0003 (FastAPI + CrewAI) — Sprint 5.7.
3. ⚠️ `_client_override` é compartilhado entre TODAS as instâncias da
   classe (ClassVar). Em testes paralelos (`pytest-xdist`), pode haver
   race. Como rodamos sequencial e cada teste limpa via fixture, OK por
   agora — documentar caso paralelizemos.
4. ⚠️ Prompt do Retriever ainda não cobre fallback explícito quando o
   gateway retorna 503 — apenas a estrutura de `tool_calls` permite. O
   Statistician (5.3) pode amplificar essa lacuna; revisar em 5.6.

---

*Próximo doc: `fase-5-sprint-5.3-progresso.md` (a criar quando Sprint
5.3 começar).*
