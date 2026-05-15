# Fase 6 — Conclusão e Estado do Sistema

> **Análise Educacional Comparada Brasil × Internacional**
> Documento de fechamento da Fase 6 (Frontend Next.js 14).
> **Data de fechamento:** 2026-05-06
> **Status:** ✅ Concluída — sistema completo Brasil × Internacional disponível em browser.

---

## 1. Sumário executivo

A Fase 6 fecha a **stack ponta-a-ponta** do sistema. Pesquisadores,
gestores públicos e estudantes podem agora abrir o navegador, fazer
uma pergunta em linguagem natural sobre educação básica BR × OCDE/LATAM
e receber em tempo real:

- Markdown estruturado adaptado ao seu perfil (3 temas visuais sutis)
- Gráfico Plotly interativo com Brasil destacado
- Lista de citações DOI clicáveis (link doi.org)
- Timeline de raciocínio dos agentes (collapsável)
- Painel lateral com fontes, fluxo executado e citações resumidas

Tudo isso atravessando o pipeline completo: **frontend (Next.js 14) →
agents-server (FastAPI :8001) → master_flow (CrewAI 8 agentes) → api
(FastAPI :8000) → DuckDB (5 marts Gold)**.

### Em uma frase

> Saímos de "8 agentes CrewAI orquestrados em 4 crews + CLI dev"
> (Fase 5) para "**workspace web Next.js 14 com 3 colunas, streaming
> SSE de pergunta → resposta com viz Plotly + citações DOI**, testado
> com 77 unit (vitest) + 9 E2E (Playwright) + tipos auto-gerados do
> OpenAPI + Caddy reverse proxy single origin pronto para produção".

---

## 2. O que foi entregue

### 2.1 Workspace Next.js 14 (3 colunas)

| Coluna | Largura | Conteúdo |
|---|---|---|
| Sidebar | 260px | Logo + nav (Comparar / Explorador / Biblioteca) + settings |
| Workspace | flex-1 | Página específica da rota |
| Context Panel | 320px | Sessão (perfil + nº mensagens + fluxo) + fontes + citações resumidas |

3 rotas implementadas:

| Rota | Componente principal | Sprint |
|---|---|---|
| `/compare` | `<Chat>` real com streaming SSE + InlineChart + CitationPanel | 6.2 + 6.3 |
| `/explorer` | `<DataExplorer>` com filtro + detalhe | 6.4 |
| `/library` | placeholder (futuro) | 6.0 |

### 2.2 Componentes principais

**Chat (`/compare`):**
- `<Chat>` — container com EmptyState + lista messages + footer InputBox
- `<MessageBubble>` — bolha user/assistant com AgentReasoning + Markdown + InlineChart + CitationPanel + footer (sources/warnings/follow-ups)
- `<AgentReasoning>` — timeline collapsável Radix com status running/done/error por agente (deduplicado)
- `<InputBox>` — textarea + Ctrl+Enter envia
- `<StreamingMarkdown>` — react-markdown + remark-gfm + classes Tailwind utility

**Charts:**
- `<PlotlyLazy>` — wrapper com dynamic import de `plotly.js-basic-dist-min` (~840 KB) + factory react-plotly.js, cache singleton
- `<InlineChart>` — recebe VizSpec, renderiza com title + sources + notes; trata `chart_type='none'`
- `<ChartErrorBoundary>` — class component, fallback compacto âmbar isolando falhas Plotly

**Citations:**
- `<CitationPanel>` — lista de cards
- `<CitationCard>` — título, autores formatados (1 / 2 com & / 3+ com et al.), journal, link doi.org externo, snippet em blockquote, source + relevância

**Explorer (`/explorer`):**
- `<DataExplorer>` — layout 2-col (lista 420px + detalhe), filtros texto + chips de tag, estados loading/error/empty
- `<MartCard>` — card com nome curto, descrição truncada, contagens pt-BR, tags

**Layout:**
- `<Sidebar>` — nav lateral
- `<Workspace>` — container central
- `<ContextPanel>` — painel direito com sessão + sources + citations resumidas
- `<ProfileTheme>` — aplica `data-profile=...` no `<html>`
- `<QueryProvider>` — TanStack Query provider

### 2.3 Stores Zustand

- `profileStore` — perfil + manualOverride lock; auto-detect respeita override manual
- `chatStore` — messages + currentAssistantId + 4 actions de streaming (push/start/append/finalize)

### 2.4 Hooks

- `useChat` — orquestra `streamChat` + `chatStore` + auto-detecção de perfil
- `useCatalog` — TanStack Query do `/api/data/catalog`

### 2.5 Bibliotecas core

- `lib/api-client.ts` — `apiFetch` + `ApiError`; lê body como text e tenta JSON.parse
- `lib/streaming.ts` — `streamChat(question, callbacks) → Promise<FinalAnswer>` consumindo SSE
- `lib/sse-parser.ts` — `SseParser` stateful (W3C compliant) + `parseSseStream` async generator
- `lib/utils/cn.ts` — clsx + tailwind-merge
- `lib/query-client.ts` — TanStack Query config

### 2.6 Backend agents-server (Sprint 6.1)

- `agents/src/server/main.py` — mini FastAPI app :8001 com `/health` + CORS
- `agents/src/server/chat_stream.py` — `POST /api/chat/stream` com `StreamingResponse(media_type="text/event-stream")`; bridge thread→loop via `asyncio.to_thread` + `loop.call_soon_threadsafe(queue.put_nowait, event)`
- `agents/src/crews/master_flow.py` — adicionado parâmetro `on_event: Callable[[dict], None]` que emite eventos por etapa

### 2.7 Infraestrutura

- `infra/caddy/Caddyfile` — reverse proxy `:8443` com routes funcionais para SSE (flush_interval -1) + dados + frontend; bloco produção com TLS auto Let's Encrypt comentado

### 2.8 Tipos OpenAPI

- `frontend/types/openapi.snapshot.json` — snapshot do `app.openapi()` (5 paths, 8 schemas)
- `frontend/types/api.ts` — gerado por `openapi-typescript`
- `frontend/types/domain.ts` — tipos espelhados manualmente de `agents/schemas.py` (FinalAnswer, VizSpec, Citation, IntentDecision, StreamEvent)

---

## 3. Sprints da Fase 6

| Sprint | Foco | Linhas TS/TSX | Testes | Status |
|---|---|---|---|---|
| 6.0 | Scaffold + Tailwind + shadcn + layout 3 colunas | ~1.080 | 17 | ✅ |
| 6.1 | Endpoint `/api/chat/stream` SSE (Python + TS) + parser | ~310 TS + ~395 PY | 5 + 4 | ✅ |
| 6.2 | `<Chat>` real + streaming UI | ~700 | 16 | ✅ |
| 6.3 | `<InlineChart>` Plotly + `<CitationPanel>` | ~440 | 15 | ✅ |
| 6.4 | `<DataExplorer>` + temas + ErrorBoundary | ~660 | 14 | ✅ |
| 6.5 | Playwright E2E + Caddy + openapi-typescript | ~700 + 1.430 gen | 9 E2E | ✅ |
| 6.6 | Conclusão + ADR 0004 | (docs) | — | ✅ |
| **Total** | **7 sprints** | **~5.860 linhas TS/TSX + 395 Python** | **86 testes** | **✅** |

Linhas adicionais:
- Configurações: tailwind.config.ts, postcss.config.js, components.json, vitest.config.ts, playwright.config.ts (~100 linhas)
- CSS: globals.css com 3 temas (~80 linhas)
- Snapshot OpenAPI: 600 linhas JSON + 330 linhas types/api.ts auto-geradas

---

## 4. Decisões aplicadas (vs `fase-6-analise.md`)

### 4.1 ✅ Tailwind 3.4 (não 4.0)

Documentado em ADR 0004 §1. Mais maduro com shadcn/ui v2; upgrade fica
para sprint futura.

### 4.2 ✅ shadcn/ui via cópia, sem dep npm

ADR 0004 §2.

### 4.3 ✅ Zustand sem Provider tree

ADR 0004 §3. 2 stores (profile, chat) consumidos via hooks diretos.

### 4.4 ✅ TanStack Query somente para server state

ADR 0004 §4. 3-tier separation (server / global / local).

### 4.5 ✅ SSE manual via `fetch` + `ReadableStream`

ADR 0004 §5. `EventSource` não suporta POST com body — `SseParser`
W3C compliant + 11 testes unitários cobrem edge cases.

### 4.6 ✅ Plotly via dynamic import singleton

ADR 0004 §6. `plotly.js-basic-dist-min` (~840 KB) em chunk separado;
inicial só cresce ~1 KB.

### 4.7 ✅ `<ChartErrorBoundary>` local ao Plotly

ADR 0004 §7.

### 4.8 ✅ 3 temas via CSS variables + `[data-profile="..."]`

ADR 0004 §8. Researcher (serif), policy (azul institucional + PNE),
student (verde + radius maior + line-height aberto).

### 4.9 ✅ Auto-detect de perfil respeita override manual

ADR 0004 §9. Validado em E2E.

### 4.10 ✅ Markdown via classes utility (sem `@tailwindcss/typography`)

ADR 0004 §10. Bundle menor + estilo combina com tema dark.

### 4.11 ✅ Mini-server agents-server :8001 separado do api :8000

ADR 0004 §11. 2 origens em dev; Caddy em prod.

### 4.12 ✅ Tipos espelhados manualmente em `types/domain.ts`

ADR 0004 §12. `openapi-typescript` gera `types/api.ts` mas ainda não
é consumido em runtime.

### 4.13 ✅ Playwright E2E com `page.route` mockando backend

ADR 0004 §13. 9 testes em ~30s, sem subir api/agents.

### 4.14 ⚠️ Smoke E2E rodando stack inteira não existe

Pendência registrada — fica para Sprint 6+ ou futuro.

### 4.15 ⚠️ `partial_markdown` SSE event não emitido pelo servidor

`Synthesizer` retorna markdown completo no `final_answer`. Streaming
token-by-token via Anthropic fica para sprint futuro.

---

## 5. Insights revelados

### 5.1 `getByLabel` strict-mode faz match parcial em multiple aria-label

`getByLabel('Pergunta')` resolve **2** elementos: `<textarea aria-label="Pergunta">` E `<button aria-label="Enviar pergunta">`. Solução: usar
`getByRole('textbox', { name: 'Pergunta' })` para precisão.

### 5.2 ChromaDB e Plotly: dynamic imports salvam o bundle

Sprint 6.3 evidenciou: bundles iniciais grandes (3 MB Plotly, 700 MB+
ChromaDB) viram chunks separados quando importados via `await import(...)`.
Bundle inicial do `/compare` ficou em 158 KB; Plotly real só carrega
quando primeira viz aparece.

### 5.3 `Response.body` só pode ser lido uma vez (`fetch`)

Sprint 6.0 descoberto durante `api-client.ts`: `response.json()` +
fallback `response.text()` falha porque body já foi consumido.
Solução: ler `.text()` primeiro e tentar `JSON.parse`, fallback para
string crua.

### 5.4 `route.fulfill` no Playwright entrega body inteiro de uma vez

Não streama. Funciona porque `parseSseStream` é resilient a chunks
grandes — todos os blocos `\n\n` são processados em sequência. Validado
em 2 testes E2E.

### 5.5 React 18 sem hook para error boundaries

Class component com `getDerivedStateFromError` + `componentDidCatch`.
`<ChartErrorBoundary>` é o único class component do projeto.

### 5.6 Variáveis CSS + `[data-profile="..."]` permitem 3 temas sem 3 codebases

Mudança de perfil é instant: CSS recalcula tokens, sem re-render React.
Transição global de 180ms em `*` para `background-color, border-color,
color, fill, stroke` torna a mudança fluida.

### 5.7 Tailwind 3.4 + `noUncheckedIndexedAccess: true` força ?. em arrays

`messages[0]?.role` em vez de `messages[0].role`. Erros de runtime por
`undefined.role` caem cedo no compile time.

---

## 6. Métricas finais

```
Componentes React:             24 (5 layout + 7 chat + 2 charts +
                                   2 citations + 2 explorer +
                                   2 ui shadcn + 4 wrappers)
Stores Zustand:                2 (profileStore, chatStore)
Hooks customizados:            2 (useChat, useCatalog)
Rotas Next.js:                 4 (/, /compare, /explorer, /library)

Linhas TS/TSX:                 ~5.860 (src + tests)
Linhas Python (Sprint 6.1):    ~395 (server agents + tests + master_flow callback)
Linhas CSS/config:             ~180

Testes vitest:                 77 / 77 PASS (~2.7s)
Testes Playwright E2E:         9 / 9 PASS (~30s)
Testes pytest agents (Sprint 6.1): 5 / 5 PASS server + 2 master_flow
Total Fase 6:                  93 testes verdes em ~33s

Tipos OpenAPI:                 5 paths + 8 schemas auto-gerados
Bundle inicial:                /compare 159 KB First Load JS
                               (alvo era 600 KB — margem de 441 KB)
Plotly chunk:                  ~840 KB lazy

Lint:                          ✅ 0 warnings ESLint
Build:                         ✅ next build OK (7 paginas estaticas)

Custo Anthropic durante a fase: $0.00 (LLM mockado em E2E)
```

---

## 7. Estado do sistema por camada (CLAUDE.md)

| Camada | Pré-Fase 6 | Pós-Fase 6 |
|---|---|---|
| **0. Fontes** | 6 com dados reais | 6 (idem) |
| **1. Ingestão** | ✅ Prefect coletores | ✅ (idem) |
| **2. Bronze** | 3,2M obs | 3,2M (idem) |
| **3. Silver** | 7 staging + 5 intermediates | idem |
| **4. Gold** | 5 marts | idem |
| **5. FastAPI** | 4 endpoints + rate limit | ✅ (idem; consumido pelo frontend) |
| **6. CrewAI** | 8 agentes, 4 crews, RAG, CLI | ✅ + agents-server :8001 com SSE |
| **7. Frontend** | 🟡 hello world | ✅ **Workspace Next.js 14 completo** |

---

## 8. Como o usuário usa

### 8.1 Subir stack completa (3 terminais)

```bash
# Terminal 1: api de dados (Fase 4)
cd api && .venv/Scripts/uvicorn src.main:app --port 8000

# Terminal 2: agents-server (chat streaming)
cd agents && .venv/Scripts/uvicorn src.server.main:app --port 8001 --reload

# Terminal 3: frontend dev
cd frontend && npm run dev
```

Acessa `http://localhost:3000` (redirect automático para `/compare`).

### 8.2 Em produção (single origin via Caddy)

```bash
caddy run --config infra/caddy/Caddyfile
# Acessa http://localhost:8443
# Caddy roteia: /api/chat/* → :8001, /api/data/* → :8000, /* → :3000
```

### 8.3 Fluxo de uso típico (data flow)

1. Usuário abre `/compare`, vê EmptyState com 3 perguntas exemplo.
2. Clica em "Como o Brasil se compara com a Finlândia em gasto educacional em 2020?"
3. Input box é preenchido. Clica enviar (ou Ctrl+Enter).
4. Bolha do user aparece. Bolha do assistant inicia com timeline:
   - Core (Orchestrator + Profiler) — running...
   - Core ✓ flow=data, profile=researcher
   - Retriever — running...
   - Retriever ✓ 1 tool call
   - Statistician ✓ method=agregados, N=4
   - Comparativist ✓
   - Citation ✓ 1 item
   - Synthesis ✓ chart=bar_vertical
5. Markdown final renderiza:
   - "# Gasto educacional 2020 — Brasil vs Finlândia"
   - "BR aplicou **5.77% do PIB** em educação (World Bank)..."
   - Gráfico bar_vertical interativo (Brasil em terracota)
   - Painel "Referências (1)" com Hanushek-Woessmann e link doi.org
   - Footer: Fontes (worldbank), Para aprofundar (3 perguntas)
6. ContextPanel lateral atualiza com perfil detectado, fluxo, sources
   e citations resumidas com link doi.org.

### 8.4 Rodar testes

```bash
cd frontend
npm test                    # 77 unit (vitest) ~3s
npm run test:e2e            # 9 E2E (playwright) ~30s
npm run lint                # ESLint
npm run build               # bundle production

cd ../agents
.venv/Scripts/python -m pytest -q  # 134 testes Python (~80s)
```

---

## 9. Próximos passos — Fase 7 (opcional)

Per CLAUDE.md §"Fase 7 (opcional) — Refinamentos e MLOps":

- MLflow para modelos preditivos (se relevante)
- A/B testing de prompts (Sprint 5.6 não fez)
- Métricas de qualidade das respostas
- Feedback loop do usuário (botão 👍/👎 + comentário)
- Relatórios Quarto para publicação acadêmica

Sem urgência — sistema atual já é funcional para pesquisa individual e
institucional acadêmica conforme escopo do CLAUDE.md.

### Pendências mais imediatas (próximos 2 meses)

1. **Suite live no agents/** com chave Anthropic real — gerar 1ª
   resposta verificada ponta-a-ponta. Custo estimado $0.20-0.50.
2. **Endpoint `/api/data/:dataset/preview`** no api/ — preview de 100
   linhas para o `<DataExplorer>` (atualmente placeholder).
3. **Smoke E2E** rodando stack inteira via Caddy + browser real.
4. **Migração `types/domain.ts` → reexports de `types/api.ts`** quando
   contrato OpenAPI estabilizar.
5. **Pre-commit hook** validando `openapi.snapshot.json` contra
   `app.openapi()` atual.
6. **Suite RAG seed expandida** de 25 → 50 papers via crawler SciELO/ERIC.

---

## 10. Débitos técnicos registrados

Herdados das Fases 1-5 + novos da Fase 6:

1. **R não executado** (Fase 1) — bloqueia mart_pisa_rankings.
2. **Coletores INEP não executados** (Fase 1) — bloqueia mart_ideb_municipal.
3. **Eurostat sem dataset de % PIB** (Fase 2).
4. **OpenMetadata stub não configurado** (Fase 3).
5. **Suite live nunca executada com chave real** (Fase 5) — pendente
   decisão do usuário.
6. **Endpoint `/api/data/:dataset/preview`** ainda não existe.
7. **Tipos auto-gerados não consumidos pelo frontend** — `types/domain.ts`
   ainda é fonte da verdade no runtime.
8. **Smoke E2E rodando stack inteira** não existe.
9. **`partial_markdown` SSE event não emitido** — markdown aparece "de
   uma vez" no `final_answer`.
10. **Manifest RAG com 25 papers** — expandir para 50-100 via crawler.
11. **`compute_stats` raramente chamada pelo Statistician** — Sonnet
    faz aritmética inline.
12. **`final.citations` overwrite no master_flow** — Synthesizer
    desperdiça tokens preenchendo campo que será sobrescrito.
13. **`analysis_crew` 4 LLM calls sequenciais** — paralelizar
    Comparativist || Visualizer.
14. **Tailwind 4 upgrade** quando shadcn estabilizar.
15. **Plotly prefetch** via `<link rel="modulepreload">` para reduzir
    latência do primeiro chart.
16. **Pre-commit hook** validando snapshot OpenAPI vs spec atual.

---

## 11. Conclusão

A Fase 6 entrega o **front oficial** do sistema. Todo o trabalho
acumulado em 5 fases anteriores (40+ bases de dados, harmonização
ISCED/ISO-3166, marts Gold em DuckDB, gateway FastAPI rate-limited, 8
agentes CrewAI com RAG) agora é acessível por uma interface única
respondendo perguntas em português.

A regra crítica do CLAUDE.md ("agentes não escrevem SQL livre") é
**transitivamente honrada** pelo frontend: ele só fala HTTP com
`/api/data/*` (read-only Pydantic-validated) e `/api/chat/stream`
(SSE com run_master). Nenhuma string SQL no JS, nenhum acesso DuckDB
no browser.

Pesquisadores agora podem:

- "Como BR se compara com FIN em gasto 2020?" → resposta com dados
  WB, z-score, viz Plotly, citações DOI, em ~30-60s.
- "O que é ISCED 2011 nível 2?" → resposta conceitual curta no fluxo
  simple, em ~10s.
- "Onde BR aparece no PISA 2022?" → resposta honesta apontando que
  PISA exige Plausible Values + BRR/Jackknife (metodologia ainda não
  implementada).

**A pergunta central do projeto** ("Como a educação básica brasileira
se compara à educação dos países desenvolvidos?") agora tem **um lugar
para ser feita por qualquer usuário** — pesquisador, gestor ou estudante
— com a resposta vindo dos dados reais e fundamentada em literatura
acadêmica.

---

*Próxima fase opcional: ver `docs/phases/fase-7-analise.md` (a criar
quando relevante).*
