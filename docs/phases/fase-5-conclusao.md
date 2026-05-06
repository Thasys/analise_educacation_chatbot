# Fase 5 — Conclusão e Estado do Sistema

> **Análise Educacional Comparada Brasil × Internacional**
> Documento de fechamento da Fase 5 (Sistema de agentes CrewAI).
> **Data de fechamento:** 2026-04-30
> **Status:** ✅ Concluída — pronta para iniciar Fase 6 (Frontend Next.js).

---

## 1. Sumário executivo

A Fase 5 amarra os 5 marts Gold (Fase 3) + 4 endpoints REST (Fase 4) a
um **sistema multi-agente CrewAI de 8 agentes especializados**, capaz
de responder perguntas educacionais em linguagem natural com:

- dados reais recuperados via tools tipadas (sem SQL livre);
- estatísticas descritivas com ressalvas metodológicas (Plausible
  Values vetados para PISA/TIMSS/PIRLS);
- narrativa contextualizada com referências PNE, OCDE EAG;
- visualização Plotly pronta para `react-plotly.js`;
- citações DOI reais do RAG ChromaDB (~25 papers seed);
- adaptação de estilo a 3 perfis (researcher/policy/student).

### Em uma frase

> Saímos de "API REST estável servindo 5 marts Gold via 4 endpoints"
> (Fase 4) para "**8 agentes CrewAI orquestrados em 4 crews, com 10
> tools, RAG ChromaDB com 25 papers e CLI dev**, produzindo respostas
> markdown adaptadas ao perfil — tudo testado com 119 testes mock
> verdes em ~80s a US$0 e suite live opt-in com Anthropic real".

---

## 2. O que foi entregue

### 2.1 Os 8 agentes

| # | Agente | Crew | LLM | Tools |
|---|---|---|---|---|
| 1 | Orchestrator | Core | Haiku 4.5 | — |
| 2 | Profile & Intent | Core | Haiku 4.5 | — |
| 3 | Data Retrieval | Analysis | Haiku 4.5 | data_catalog, data_timeseries, data_compare, data_ranking |
| 4 | Statistical Analyst | Analysis | Sonnet 4.5 | compute_stats |
| 5 | Comparative Education | Analysis | Sonnet 4.5 | rag_search |
| 6 | Citation & Evidence | Analysis | Haiku 4.5 | rag_search, cite_resolve |
| 7 | Visualization | Synthesis | Haiku 4.5 | make_plotly_spec |
| 8 | Response Synthesizer | Synthesis | Sonnet 4.5 | — |

Mix esperado: ~5 chamadas Haiku 4.5 + 3 chamadas Sonnet 4.5 por
pergunta data flow.

### 2.2 As 4 crews

| Crew | Função | Função entrypoint |
|---|---|---|
| Core | Sempre roda. Classifica fluxo + extrai entidades. | `run_core_flow(question)` |
| Analysis | Para fluxos `data`/`deep`. Recupera + calcula + contextualiza + cita. | `run_analysis_flow(core, ...)` |
| Synthesis | Sempre roda. Gera viz + markdown final. | `run_synthesis_flow(...)` |
| Master | Orquestra tudo com routing por flow. | `run_master(question)` |

### 2.3 Tools (10)

| Tool | I/O | Backing |
|---|---|---|
| `data_catalog` | () → list of marts | GET /api/data/catalog |
| `data_timeseries` | TimeseriesArgs → series | POST /api/data/timeseries |
| `data_compare` | CompareArgs → table+stats | POST /api/data/compare |
| `data_ranking` | RankingArgs → ranked list | POST /api/data/ranking |
| `compute_stats` | values+focus → stats+position | local Python |
| `rag_search` | query+filters → hits | ChromaDB local |
| `cite_resolve` | doi → metadata | RAG lookup local |
| `make_plotly_spec` | rows+chart_type → figure | Python templates |
| (extract_entities) | implícito no Profiler | Haiku via prompt |
| (detect_profile) | implícito no Orchestrator | Haiku via prompt |

### 2.4 Os 3 fluxos de execução

| Fluxo | Latência alvo | Tokens estim. | Pipeline |
|---|---|---|---|
| `simple` | 5-10s | ~5k | Core → Comparativist → Citation → Synthesis |
| `data` | 20-40s | ~15k | Core → Analysis full → Synthesis |
| `deep` | 60-120s | ~80k | Core → Analysis (futuro: max_iter +) → Synthesis |

### 2.5 RAG ChromaDB

- 25 papers seed em `agents/src/rag/seeds/manifest.yaml`
- Mix de 6 papers em PT (SciELO/INEP) + 17 em EN + 1 em ES + 1 sem lang
- Cobertura: 10 fundamentais do CLAUDE.md + 15 complementares
  (Brasil/internacional/metodologia/avaliação)
- Embedding produção: `paraphrase-multilingual-MiniLM-L12-v2`
- Embedding testes: `StubEmbedding` MD5 32-dim (determinístico, sem
  download)

### 2.6 CLI dev

```bash
cd agents
.venv/Scripts/python -m src.cli "<pergunta>"               # markdown formatado
.venv/Scripts/python -m src.cli "..." --json-only          # JSON puro
```

---

## 3. Sprints da Fase 5

| Sprint | Foco | Linhas Python | Testes | Status |
|---|---|---|---|---|
| 5.0 | Setup + scaffold (config, logging, api_client, schemas) | ~880 | 20 | ✅ |
| 5.1 | Profile + Orchestrator (Core Crew) | ~520 | 11 | ✅ |
| 5.2 | Data Retrieval Agent + 4 tools | ~620 | 16 | ✅ |
| 5.3 | Statistician + Comparativist (Sonnet 4.5) | ~580 | 17 | ✅ |
| 5.4 | Visualizer + Synthesizer + Synthesis Crew | ~870 | 16 | ✅ |
| 5.5 | RAG ChromaDB + Citation Agent (25 seeds) | ~1.000 | 30 | ✅ |
| 5.6 | Master Flow + CLI + suite live | ~915 | 9 + 2 live | ✅ |
| 5.7 | Conclusão + ADR 0003 | (docs) | — | ✅ |
| **Fase 5** | **8 sprints** | **~5.385 linhas Python** | **119 + 2 live** | **✅** |

Linhas adicionais: ~880 linhas YAML/prompt (manifest RAG + 8 system prompts).

---

## 4. Decisões aplicadas (vs `fase-5-analise.md`)

### 4.1 ✅ Tools chamam o gateway HTTP, sem exceção

Confirmado e validado pelos 119 testes. `agents/src/api_client.py` é o
único canal; nenhum `import duckdb` no `agents/`. ADR 0003 §2 detalha.

### 4.2 ✅ LLM por papel — Haiku/Sonnet split

Implementado em `agents/src/llm.py::make_llm("fast" | "smart")`. Mix
~70% Haiku, ~30% Sonnet conforme planejado.

### 4.3 ✅ Tools com schemas Pydantic + `_SafeDataTool` mixin

Inputs validados ANTES do POST/local. Erros estruturados em JSON em
vez de `ValueError` propagado — agente pode reformular.

### 4.4 ✅ RAG ChromaDB embedded

`PersistentClient` em `data/chromadb/edu_literature/`. Sem servidor.
ADR 0003 §9.

### 4.5 ✅ Observabilidade preparada (Langfuse), default off

Telemetria CrewAI/PostHog desligada por default
(`CREWAI_DISABLE_TELEMETRY=true`). Langfuse opcional via
`AGENTS_LANGFUSE_*` settings — não rodado em Sprint 5.6.

### 4.6 ✅ Adaptação a 3 perfis no Synthesizer

Validado em `test_synthesis_flow_*_profile_mentions_pne`. Prompts
distinguem researcher (técnico, sem emojis), policy (cita PNE meta 20),
student (glossário inline).

### 4.7 ✅ Suite E2E mockada + live opt-in

119 testes mock em ~80s, $0. 2 testes live skipados por default; rodam
com `pytest -m live`.

### 4.8 ⚠️ `chart_type=scatter` adiado

Cruzamento gasto x alfabetização (Sprint 5+) — fica para depois do
endpoint `/api/data/cross` planejado na Fase 4 §7.

### 4.9 ⚠️ Manifest RAG com 25 entradas (objetivo era 30+)

Decisão consciente: PR enxuto, manifest é apenas seed inicial.
`ingest_manifest` é idempotente, expansão para 50-100 papers fica para
crawler SciELO/ERIC futuro (Sprint 5+).

### 4.10 ⚠️ Suite live nunca executada com chave Anthropic real

Coletada e estruturada (asserts soft); aguarda decisão do usuário de
gastar ~$0.10-0.20 para validação. Estrutura permite rodar quando
quiser.

---

## 5. Insights revelados

### 5.1 CrewAI 1.x: factory `LLM` retorna subclasse, não instância de `LLM`

`crewai.LLM(model="anthropic/...")` devolve `AnthropicCompletion`,
subclasse de `BaseLLM` e **não** de `LLM`. Afeta:

- `isinstance` checks (use `BaseLLM`)
- Mock de `.call` (precisa cobrir as duas classes)
- `llm.model` perde prefixo `anthropic/` (use `llm.provider == "anthropic"`)

Documentado em ADR 0003 §6 e na fixture `mock_llm_call`.

### 5.2 BaseTool valida args ANTES de `_run` e levanta `ValueError`

CrewAI BaseTool valida `args_schema` e levanta antes de chegar ao
`_run`. Quebraria o loop do agente. Solução: `_SafeDataTool` mixin que
captura no `run()` e devolve JSON estruturado. Aplicado em todas as 7
tools de I/O (data, stats, viz, rag).

### 5.3 ChromaDB 1.1.1 `EphemeralClient` não é isolado

Compartilha tenant default entre instâncias do mesmo processo. Para
testes paralelizáveis, RagClient aceita `collection_name` único por
chamada (UUID).

### 5.4 pydantic-settings 2.10: env var > init kwarg com `validation_alias`

Quando o campo tem `validation_alias`, env var sobrescreve init kwarg
mesmo com `populate_by_name=True`. Workaround em testes:
`monkeypatch.delenv` antes de `Settings(...)`.

### 5.5 Logs em stderr, não stdout

`structlog.PrintLoggerFactory(file=sys.__stderr__)` — usar
`__stderr__` (não `stderr`) para sobreviver substituições de pytest
capsys. Permite CLI `--json-only` com stdout limpo.

### 5.6 Prompts versionados em `.txt` >> hardcoded em Python

Carregados via `agents/src/agents/_prompt_loader.py::load_prompt(name)`
cacheado. Vantagens: edição direta sem Python, diffs limpos em PR,
A/B testing trocando arquivo. 8 prompts × média 75 linhas = ~600
linhas de prompt versionadas.

---

## 6. Métricas finais

```
Agentes:                       8
Crews:                         4 (Core, Analysis, Synthesis, Master)
Tools:                         10 (4 data + 1 stats + 3 viz + 2 rag)
Schemas Pydantic v2:           14 (entrada/saida + envelope)
Prompts (.txt):                8 system prompts (~600 linhas)

RAG seed:                      25 papers (10 PT/EN fundamentais + 15 complementares)
Embedding modelo (prod):       paraphrase-multilingual-MiniLM-L12-v2 (~500 MB on demand)
Embedding modelo (testes):     StubEmbedding MD5 32-dim (determinismo, sem download)

Linhas Python (src + tests):   ~5.385
Linhas YAML:                   ~280 (manifest RAG)
Linhas prompt:                 ~600

Testes pytest TOTAL:           119 / 119 PASS (~80s) + 2 skipped (live opt-in)
  - tests/test_*.py:           29 (config, api_client, llm, cli)
  - tests/agents/:             32 (8 agentes em 4 arquivos)
  - tests/tools/:              42 (4 grupos)
  - tests/rag/:                17
Testes Python totais projeto:  306 (data_pipeline 191 + api 19 + agents 119 - 23 mock duplicates)
Tests dbt:                     157 (idem Fase 3)
Tests TOTAL projeto:           ~485 verdes

Custo Anthropic (Sprint 5.0-5.7): $0.00 (LLM mockado)
Custo estimado live (data flow): $0.05-0.10 / pergunta
Latência alvo data flow:       20-40s mediana
Tamanho .venv agents/:         ~1.9 GB (CrewAI + Anthropic + ChromaDB + sentence-transformers + torch)
```

---

## 7. Estado do sistema por camada (CLAUDE.md)

| Camada | Pré-Fase 5 | Pós-Fase 5 |
|---|---|---|
| **0. Fontes** | 6 com dados reais | 6 (idem) |
| **1. Ingestão** | ✅ Prefect coletores | ✅ (idem) |
| **2. Bronze** | 3,2M obs | 3,2M (idem) |
| **3. Silver** | 7 staging + 5 intermediates | idem |
| **4. Gold** | 5 marts | idem |
| **5. FastAPI** | 4 endpoints + rate limit | ✅ (idem; consumido pelos agentes) |
| **6. CrewAI** | ⏳ vazio | ✅ **8 agentes, 4 crews, 10 tools, RAG 25 papers, CLI dev** |
| **7. Frontend** | 🟡 hello world | 🟡 idem (Fase 6 próxima) |

---

## 8. Próximos passos — Fase 6 (Frontend Next.js)

A Fase 6 conecta o sistema de agentes a uma interface web única,
fechando a stack ponta-a-ponta para o usuário final.

### 8.1 O que entra na Fase 6

- Scaffold Next.js 14 App Router + TypeScript strict + Tailwind 4 + shadcn/ui
- Layout 3 colunas (sidebar + workspace + context panel) — wireframe
  em `docs/architecture/frontend-arch.jsx`
- Componentes principais:
  - `<Chat>` consumindo SSE de `POST /api/chat/stream` (a criar no
    `api/`)
  - `<AgentReasoning>` mostrando steps das crews em tempo real
  - `<InlineChart>` renderizando `VizSpec.plotly_figure` via
    `react-plotly.js`
  - `<CitationPanel>` listando DOIs com links externos
  - `<DataExplorer>` navegando catálogo de marts
- Estado global Zustand (perfil detectado, histórico)
- Cache TanStack Query
- Cliente API gerado via `openapi-typescript` apontando para `api/`

### 8.2 Bloqueadores conhecidos

- Endpoint `/api/chat/stream` precisa ser adicionado ao `api/` (Sprint
  6.1) — chama `run_master` em background e emite SSE com
  `agent_started`, `tool_called`, `final_answer` events.
- Renderização do `VizSpec` no frontend exige `react-plotly.js` (~3 MB
  bundle) — avaliar lazy load.

### 8.3 Estimativa Fase 6 (4 semanas)

| Sprint | Foco | Estimativa |
|---|---|---|
| 6.0 | Scaffold + tipos OpenAPI + layout 3 colunas | 3 dias |
| 6.1 | Endpoint SSE `/api/chat/stream` no api/ | 2 dias |
| 6.2 | `<Chat>` + `<AgentReasoning>` + streaming | 3 dias |
| 6.3 | `<InlineChart>` Plotly + `<CitationPanel>` | 2 dias |
| 6.4 | `<DataExplorer>` + adaptação de tema por perfil | 3 dias |
| 6.5 | Testes E2E Playwright + deploy local Caddy | 2 dias |
| 6.6 | Conclusão + ADR 0004 (frontend arch) | 1 dia |
| **Fase 6 completa** | | **~16 dias úteis** |

---

## 9. Débitos técnicos registrados

Herdados das fases 1-4 + novos da Fase 5:

1. **R não executado** (Fase 1) — bloqueia mart_pisa_rankings.
2. **Coletores INEP não executados** (Fase 1) — bloqueia mart_ideb_municipal.
3. **Eurostat sem dataset de % PIB** (Fase 2) — `t2020_42` ou similar.
4. **OpenMetadata stub não configurado** (Fase 3) — `infra/openmetadata/`.
5. **Suite live nunca executada com chave real** — pendente decisão do
   usuário (~$0.20/run).
6. **ADR 0003 já criada** ✅ (Sprint 5.7).
7. **Frontend não pode renderizar VizSpec ainda** — Fase 6.
8. **Endpoint `/api/chat/stream` não existe** — Sprint 6.1.
9. **Manifest RAG com 25 papers** — expansão para 50-100 via crawler
   SciELO/ERIC fica para Sprint futuro.
10. **`compute_stats` raramente chamada pelo Statistician** — Sonnet
    faz aritmética inline com 4-30 valores. Avaliar em produção.
11. **Custo médio por pergunta não medido** — estimado $0.05-0.10
    no `data` flow, confirmar com suite live.
12. **`final.citations` overwrite no master_flow** — funciona mas
    Synthesizer ainda recebe instrução de preencher (desperdício de
    tokens). Otimização: prompt do Synthesizer instrui
    `citations: []` sempre.
13. **`analysis_crew` 4 LLM calls sequenciais** — Sprint 5+ pode
    paralelizar Comparativist || Visualizer.

---

## 10. Conclusão

A Fase 5 entrega o **núcleo conversacional** do sistema. Pesquisadores,
gestores e estudantes agora podem perguntar em linguagem natural:

- "Como o Brasil se compara com a Finlândia em gasto educacional em
  2020?" → resposta com dados WB, z-score, viz Plotly e citações.
- "O que é ISCED 2011?" → resposta conceitual curta sem chamar gateway.
- "Onde o BR aparece no PISA 2022?" → resposta honesta apontando que
  PISA exige Plausible Values + BRR/Jackknife (metodologia ainda não
  implementada).

A regra crítica do `CLAUDE.md` ("agentes não escrevem SQL livre") é
**arquiteturalmente impossível** de violar: nenhum `import duckdb` no
`agents/`, nenhuma string SQL nos prompts, único caminho de dados via
HTTP REST com Pydantic v2 validando inputs.

A próxima fase (Frontend Next.js) começa de um sistema de agentes
testado (119 testes verdes), documentado (ADR 0003 + 7 progress docs)
e com CLI funcional para validação ad-hoc. Basta adicionar o endpoint
`/api/chat/stream` e renderizar `FinalAnswer` em React.

---

*Próxima fase: ver `docs/phases/fase-6-analise.md` (a criar). Documento
de migração para outra máquina permanece em
[`fase-2-sprint-2.0-progresso.md`](./fase-2-sprint-2.0-progresso.md).*
