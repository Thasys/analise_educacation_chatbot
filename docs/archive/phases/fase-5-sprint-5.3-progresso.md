# Fase 5 — Sprint 5.3 (Statistician + Comparativist) — Progresso

> Estado da Sprint 5.3 da Fase 5 (Sistema de agentes CrewAI).
> Complementa [`fase-5-analise.md`](./fase-5-analise.md) e
> [`fase-5-sprint-5.2-progresso.md`](./fase-5-sprint-5.2-progresso.md).
> **Data:** 2026-04-29
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Adicionar os dois agentes de raciocínio analítico que **consomem** a
saída do Retriever (`RetrievedData`) e produzem:

- **Statistical Analyst** (Sonnet 4.5) → `StatAnalysis` com z-score,
  percentil, rank, ressalvas metodológicas.
- **Comparative Education** (Sonnet 4.5) → `ComparativeContext` com
  narrativa BR × Internacional, contexto histórico (PNE, lacunas
  PISA/TIMSS) e caveats.

Ambos via "agente como caixa-preta": LLM mockado retorna direto o JSON
estruturado; tool-call loop real fica para suite live em Sprint 5.6.

---

## 2. Entregáveis

### 2.1 Arquivos novos

| Arquivo | Linhas | Descrição |
|---|---|---|
| `agents/src/tools/stats_tools.py` | 165 | `compute_summary_stats`, `compute_position`, `ComputeStatsTool` BaseTool |
| `agents/src/agents/statistician.py` | 32 | `build_statistician()` com Sonnet 4.5 + ComputeStatsTool |
| `agents/src/agents/comparativist.py` | 30 | `build_comparativist()` com Sonnet 4.5 (sem tools, ganhará RAG em 5.5) |
| `agents/src/prompts/statistician_system.txt` | 80 | regras metodológicas (PVs vetados para PISA/TIMSS, padrões de interpretação z-score/percentil) |
| `agents/src/prompts/comparativist_system.txt` | 75 | narrativa fundamentada, PNE meta 20, lacunas TIMSS/PIRLS, regras de tonalidade |
| `agents/tests/tools/test_stats_tools.py` | 130 | 11 testes (helpers + tool, edge cases) |
| `agents/tests/agents/test_statistician_comparativist.py` | 220 | 6 testes (build factories + 4 cenários crew kickoff) |

### 2.2 Edições

| Arquivo | Mudança |
|---|---|
| `agents/src/schemas.py` | +`CountryPosition`, +`StatAnalysis` (com `method ∈ {agregados, plausible_values_pending}`), +`ComparativeContext` |
| `agents/src/tools/__init__.py` | +exports `ComputeStatsTool`, `compute_summary_stats`, `compute_position` |
| `agents/src/agents/__init__.py` | +`build_statistician`, +`build_comparativist` |

**Total Sprint 5.3: ~580 linhas Python + 155 linhas de prompt.**

---

## 3. Decisões aplicadas

### 3.1 ✅ `method ∈ {"agregados", "plausible_values_pending"}` no schema

O `StatAnalysis` carrega explicitamente o método estatístico aplicado.
Para indicadores agregados (% PIB, % alfabetização) o agente faz
descritivas usuais. Para microdados PISA/TIMSS/PIRLS o agente DEVE
recusar (retornando `method="plausible_values_pending"` + warnings),
mitigando o risco R5 do `fase-5-analise.md`. Validado em
`test_statistician_refuses_pisa_without_pv`.

### 3.2 ✅ `compute_summary_stats` + `compute_position` como helpers puros

Funções Python sem dependência CrewAI. Reusáveis em testes unitários
rápidos (~ms cada) e na tool. Cobertura 100% das branches:
- listas vazias (zeros seguros)
- listas de 1 elemento (stddev/cv = 0)
- `higher_is_better=False` para taxa de analfabetismo (inverte percentil)

### 3.3 ✅ `ComputeStatsTool` herda diretamente de `BaseTool`

Não usa o `_SafeDataTool` mixin de `data_tools.py` porque não tem
`_client_override`; mas replica o mesmo `try/except ValueError` no seu
próprio `run()` para padronizar resposta de erro.

### 3.4 ✅ Comparativist sem tools nesta sprint

A análise comparativa em Sprint 5.3 é puramente sintética sobre
`RetrievedData + StatAnalysis`. Tools de RAG (`rag_search`,
`cite_resolve`) entrarão em Sprint 5.5. O prompt já restringe DOIs e
gráficos como "tarefa de outros agentes" — evita alucinação prévia.

### 3.5 ✅ Prompts incluem "regras de proibição" explícitas

Padronizamos cláusulas:
- Proibição de citar mais de 15 palavras literais sem aspas (regra do
  CLAUDE.md seção §6 metodologia).
- Proibição de DOIs/links no Comparativist (Citation Agent — Sprint 5.5).
- Proibição de prescrições de política (descreve, não recomenda).

Reduz risco de respostas alucinadas pelo Sonnet.

### 3.6 ⚠️ Cobertura "agente como caixa-preta" mantida

Tool-call loop real do CrewAI 1.x (LLM tool_use → CrewAI parsing →
ferramenta executa → resultado retorna ao LLM) ainda não é exercido em
nenhum teste do Sprint 5.3. A confiança vem de:

- Tools individualmente cobertas via gateway mock (Sprint 5.2).
- Helpers `compute_*_stats` cobertos via testes diretos (esta sprint).
- Validação ponta-a-ponta vai para `tests/e2e/` no Sprint 5.6, com
  ~3 chamadas Anthropic reais.

---

## 4. Métricas finais

```
Linhas Python adicionadas:     ~580 (src + tests Sprint 5.3)
Linhas de prompt:              +155 (statistician + comparativist)
Testes pytest TOTAL:           63 / 63 PASS (~37s)
Testes especificos Sprint 5.3: 17 / 17 PASS
  - stats helpers + tool: 11 testes (~0.3s)
  - statistician/comparativist: 6 testes (~14s)
Custo Anthropic:               $0.00 (LLM mockado)
```

---

## 5. Estrutura do `agents/` após Sprint 5.3

```
agents/
├── src/
│   ├── schemas.py             (+ CountryPosition, StatAnalysis, ComparativeContext)
│   ├── agents/
│   │   ├── orchestrator.py
│   │   ├── profiler.py
│   │   ├── retriever.py
│   │   ├── statistician.py    ✅ NOVO
│   │   └── comparativist.py   ✅ NOVO
│   ├── prompts/
│   │   ├── orchestrator_system.txt
│   │   ├── profiler_system.txt
│   │   ├── retriever_system.txt
│   │   ├── statistician_system.txt   ✅ NOVO
│   │   └── comparativist_system.txt  ✅ NOVO
│   └── tools/
│       ├── data_tools.py
│       └── stats_tools.py     ✅ NOVO
└── tests/
    ├── agents/
    │   ├── test_orchestrator_profiler.py
    │   ├── test_retriever.py
    │   └── test_statistician_comparativist.py  ✅ NOVO
    └── tools/
        ├── test_data_tools.py
        └── test_stats_tools.py   ✅ NOVO
```

---

## 6. Próximo: Sprint 5.4 (Visualizer + Synthesizer)

A Sprint 5.4 fecha o caminho **dado → visualização + resposta final**:

- **Visualization Agent** (Haiku 4.5) — gera Plotly spec a partir de
  templates (bar chart, line chart) sobre `primary_data`.
- **Response Synthesizer** (Sonnet 4.5) — combina tudo (RetrievedData,
  StatAnalysis, ComparativeContext, VizSpec) em markdown adaptado ao
  perfil detectado (researcher / policy / student).

### 6.1 Entregáveis previstos

- `agents/src/tools/viz_tools.py` com `make_plotly_spec` (template).
- `agents/src/agents/visualizer.py`, `synthesizer.py` + prompts.
- `agents/src/schemas.py` +`VizSpec`, `FinalAnswer`.
- `agents/src/crews/synthesis_crew.py` com Visualizer || Synthesizer
  (paralelizáveis).
- Testes ~10 novos.

### 6.2 Critério de avanço

Pergunta exemplo, com mock LLM, deve produzir um `FinalAnswer` com:
- markdown adaptado ao perfil (linguagem técnica vs informal),
- ≥ 1 referência ao Plotly figure dict (mesmo que stub),
- lista de fontes citadas no rodapé.

---

## 7. Pendências registradas

1. ⏳ Suite live (`-m live`) com tool-call loop e custo real Anthropic
   só em Sprint 5.6.
2. ⏳ ADR 0003 (FastAPI + CrewAI) — Sprint 5.7.
3. ⚠️ Statistician usa `compute_stats` como tool opcional. O LLM Sonnet
   é capaz de fazer aritmética com 4-30 valores sozinho; a tool só
   ajuda em conjuntos grandes (>30 países). Em Sprint 5.6, medir se a
   tool é realmente invocada e ajustar o prompt se for ignorada.
4. ⚠️ Comparativist gera `historical_context` por inferência do prompt
   (sem RAG) — risco de afirmações datadas/imprecisas. Sprint 5.5
   resolverá ancorando em literatura.

---

*Próximo doc: `fase-5-sprint-5.4-progresso.md` (a criar quando Sprint
5.4 começar).*
