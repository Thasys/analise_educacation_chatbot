# Fase 5 — Sprint 5.4 (Visualizer + Synthesizer + Synthesis Crew) — Progresso

> Estado da Sprint 5.4 da Fase 5 (Sistema de agentes CrewAI).
> Complementa [`fase-5-analise.md`](./fase-5-analise.md) e
> [`fase-5-sprint-5.3-progresso.md`](./fase-5-sprint-5.3-progresso.md).
> **Data:** 2026-04-29
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Fechar o caminho **dado bruto → resposta final markdown + Plotly spec
adaptada ao perfil**. Implementa os dois últimos agentes da pipeline:

- **Visualization Agent** (Haiku 4.5) → `VizSpec` com Plotly figure dict
  válido para `react-plotly.js` (Fase 6).
- **Response Synthesizer** (Sonnet 4.5) → `FinalAnswer` com markdown
  adaptado a researcher / policy / student.

Mais a `synthesis_crew.run_synthesis_flow(core, retrieved, stats,
context) → (VizSpec, FinalAnswer)` que serializa todo o contexto
acumulado e roda os dois agentes em sequência.

---

## 2. Entregáveis

### 2.1 Arquivos novos

| Arquivo | Linhas | Descrição |
|---|---|---|
| `agents/src/tools/viz_tools.py` | 250 | `make_plotly_bar_horizontal`, `make_plotly_bar_vertical`, `make_plotly_line_multi` + `MakePlotlySpecTool` BaseTool. Brasil destacado em `#c0392b` (terracota) automaticamente |
| `agents/src/agents/visualizer.py` | 30 | `build_visualizer()` com Haiku 4.5 + MakePlotlySpecTool |
| `agents/src/agents/synthesizer.py` | 30 | `build_synthesizer()` com Sonnet 4.5 (sem tools) |
| `agents/src/prompts/visualizer_system.txt` | 70 | regras de decisão por chart type (bar_h ≥6 países, bar_v 3-6, line_multi temporal), regras de título e metadados |
| `agents/src/prompts/synthesizer_system.txt` | 100 | template markdown adaptado a 3 perfis (researcher/policy/student), regras de proibição (sem inventar números, sem prescrever política, sem DOIs nesta sprint) |
| `agents/src/crews/synthesis_crew.py` | 130 | `build_synthesis_crew(core, retrieved, stats, context)` + `run_synthesis_flow(...)` com coerção pydantic/string/dict |
| `agents/tests/tools/test_viz_tools.py` | 175 | 12 testes (helpers + tool, edge cases) |
| `agents/tests/agents/test_visualizer_synthesizer.py` | 220 | 5 testes (build + 3 cenários de `run_synthesis_flow` cobrindo perfis researcher/student/policy) |

### 2.2 Edições

| Arquivo | Mudança |
|---|---|
| `agents/src/schemas.py` | +`ChartType`, +`VizSpec`, +`FinalAnswer` |
| `agents/src/tools/__init__.py` | +exports viz tools |
| `agents/src/agents/__init__.py` | +`build_visualizer`, +`build_synthesizer` |
| `agents/src/crews/__init__.py` | +`build_synthesis_crew`, +`run_synthesis_flow` |

**Total Sprint 5.4: ~870 linhas Python + 170 linhas de prompt.**

---

## 3. Decisões aplicadas

### 3.1 ✅ Templates Plotly puros + tool wrapper

Três funções helper produzem figure dicts válidos para Plotly.js.
Vantagens:

- Testáveis em isolamento (sem CrewAI nem LLM) — 8 testes diretos
  validam labels, ordering, color, axis config.
- Reutilizáveis em outros lugares (ex.: `cli.py` da Sprint 5.6 podendo
  imprimir um chart como ASCII fallback).
- O Visualizer Agent pode chamar a tool OU construir o figure dict
  sozinho — flexibilidade para casos especiais.

### 3.2 ✅ Brasil destacado automaticamente em `#c0392b`

A função `_color_for(country_iso3)` aplica cor de destaque sempre que
encontra `BRA` no campo de label. Isso evita o LLM precisar lembrar a
regra de cor em cada VizSpec — vai de graça pelo template. Documentado
no prompt como "automático".

### 3.3 ✅ Synthesizer recebe contexto serializado em JSON único

Em vez de múltiplas Tasks com `context=[task1, task2, ...]` (CrewAI
1.x exige aliasing manual de outputs), a `synthesis_crew` serializa
**tudo** (intent, entities, retrieved, stats, context) num único JSON
blob passado no `task.description`. Mais simples, robusto e testável.

Trade-off: Synthesizer Sonnet processa ~3-5k tokens de contexto
extra. Aceitável dado custo Sonnet 4.5 (~$3/M input). Se virar gargalo,
em Sprint 5.6 podemos comprimir o blob (drop primary_data quando
StatAnalysis já tem agregados).

### 3.4 ✅ FinalAnswer carrega `visualizations: list[VizSpec]`

O Synthesizer **inclui** a VizSpec gerada pelo Visualizer dentro de
`FinalAnswer.visualizations`. O frontend (Fase 6) lê uma única estrutura
para renderizar tudo. Permite ao Synthesizer também referenciar a viz
no markdown via blockquote `> [Visualização: <descrição>]`.

### 3.5 ✅ `chart_type="none"` para fluxo simple

Perguntas conceituais (fluxo `simple`) não geram visualização — a
VizSpec retorna chart_type=none com figure vazio (apenas anotação
"Sem dados"). Validado em `test_synthesis_flow_simple_no_viz`.

### 3.6 ✅ Adaptação de perfil delegada ao prompt do Synthesizer

O prompt define 3 estilos:
- **researcher**: tom acadêmico, z-scores explícitos, sem emojis.
- **policy**: cita PNE Lei 13.005/2014, números arredondados.
- **student**: glossário inline, analogias.

Validamos que `out_final.profile_used` espelha o perfil do
IntentDecision e que o markdown menciona PNE para `policy`
(`test_synthesis_flow_policy_profile_mentions_pne`).

### 3.7 ⚠️ Cobertura segue "agente como caixa-preta"

Tool-call loop real (Visualizer chamando `make_plotly_spec` via LLM
tool_use) ainda não é exercido — o LLM mock retorna direto a VizSpec
final. Validação ponta-a-ponta na Sprint 5.6 com chamadas Anthropic
reais.

---

## 4. Métricas finais

```
Linhas Python adicionadas:     ~870 (src + tests Sprint 5.4)
Linhas de prompt:              +170 (visualizer + synthesizer)
Testes pytest TOTAL:           79 / 79 PASS (~38s)
Testes especificos Sprint 5.4: 16 / 16 PASS
  - viz tools (test_viz_tools.py): 12 testes (~0.5s)
  - viz/synth agents: 5 testes (~13s)
Custo Anthropic:               $0.00 (LLM mockado)
```

---

## 5. Estrutura do `agents/` após Sprint 5.4

```
agents/
├── src/
│   ├── schemas.py             (+ ChartType, VizSpec, FinalAnswer)
│   ├── agents/
│   │   ├── orchestrator.py
│   │   ├── profiler.py
│   │   ├── retriever.py
│   │   ├── statistician.py
│   │   ├── comparativist.py
│   │   ├── visualizer.py      ✅ NOVO
│   │   └── synthesizer.py     ✅ NOVO
│   ├── prompts/
│   │   ├── orchestrator_system.txt
│   │   ├── profiler_system.txt
│   │   ├── retriever_system.txt
│   │   ├── statistician_system.txt
│   │   ├── comparativist_system.txt
│   │   ├── visualizer_system.txt   ✅ NOVO
│   │   └── synthesizer_system.txt  ✅ NOVO
│   ├── crews/
│   │   ├── core_crew.py
│   │   └── synthesis_crew.py  ✅ NOVO
│   └── tools/
│       ├── data_tools.py
│       ├── stats_tools.py
│       └── viz_tools.py       ✅ NOVO
└── tests/
    ├── agents/
    │   ├── test_orchestrator_profiler.py
    │   ├── test_retriever.py
    │   ├── test_statistician_comparativist.py
    │   └── test_visualizer_synthesizer.py  ✅ NOVO
    └── tools/
        ├── test_data_tools.py
        ├── test_stats_tools.py
        └── test_viz_tools.py  ✅ NOVO
```

---

## 6. Próximo: Sprint 5.5 (RAG ChromaDB + Citation Agent)

Sprint 5.5 popula o ChromaDB com ≥30 papers/abstracts e implementa o
**Citation & Evidence Agent** que consulta o RAG para fundamentar
afirmações com DOIs reais.

### 6.1 Entregáveis previstos

- Instalar extras `[rag]` (chromadb + sentence-transformers + pyyaml).
- `agents/src/rag/client.py` — wrapper ChromaDB com embeddings
  multilingual.
- `agents/src/rag/ingest.py` — pipeline de ingestão a partir de manifest
  YAML.
- `agents/src/rag/seeds/manifest.yaml` — ≥30 entradas (ver lista §5.1
  da `fase-5-analise.md`).
- `agents/src/tools/rag_tools.py` — `RAGSearchTool`, `CiteResolveTool`.
- `agents/src/agents/citation.py` + prompt.
- `agents/src/schemas.py` +`Citation`, `Citations` (lista de DOIs +
  snippets).
- Atualizar `comparativist.py` para acoplar `RAGSearchTool`.
- Testes: ~10 testes (ingest dry-run, search, citation agent).

### 6.2 Critério de avanço

`run_citation_flow(question, narrative_context) → Citations` retorna
≥1 DOI relevante para perguntas canônicas (ex.: "investimento BR vs
OCDE" → Hanushek & Woessmann 2011, OECD EAG 2024).

---

## 7. Pendências registradas

1. ⏳ Tool-call loop real apenas em Sprint 5.6 (suite live).
2. ⏳ ADR 0003 — Sprint 5.7.
3. ⚠️ Synthesizer recebe ~3-5k tokens de contexto. Em Sprint 5.6,
   medir custo médio por pergunta (orçamento <$0.10 conforme objetivo
   §10.8 do `fase-5-analise.md`); se exceder, comprimir blob.
4. ⚠️ Templates de viz cobrem apenas chart types essenciais. Scatter
   (cruzamento gasto x alfab) fica para Sprint 5+ junto com endpoint
   `/api/data/cross` previsto na Fase 4 §7.
5. ⚠️ Frontend não pode renderizar VizSpec ainda — Fase 6 fará a
   integração via `react-plotly.js` consumindo o JSON.

---

*Próximo doc: `fase-5-sprint-5.5-progresso.md` (a criar quando Sprint
5.5 começar).*
