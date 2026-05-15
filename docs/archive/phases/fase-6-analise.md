# Fase 6 — Análise de Desenvolvimento (Frontend Next.js 14)

> **Análise Educacional Comparada Brasil × Internacional**
> Documento analítico sobre o desenvolvimento da **Fase 6 — Frontend Next.js 14**.
> Complementa o roadmap em [`CLAUDE.md`](../../CLAUDE.md#fase-6--frontend-nextjs-semanas-1619)
> e parte das conclusões da [`Fase 5`](./fase-5-conclusao.md).
> **Data:** 2026-04-30

---

## Sumário

1. [Contexto e ponto de partida](#1-contexto-e-ponto-de-partida)
2. [Objetivos da Fase 6](#2-objetivos-da-fase-6)
3. [Decisões arquiteturais propostas](#3-decisões-arquiteturais-propostas)
4. [Componentes e layout](#4-componentes-e-layout)
5. [Padrões de código](#5-padrões-de-código)
6. [Estratégia de testes](#6-estratégia-de-testes)
7. [Sequência de implementação (sprints)](#7-sequência-de-implementação-sprints)
8. [Riscos e mitigações](#8-riscos-e-mitigações)
9. [Critérios de aceitação](#9-critérios-de-aceitação)

---

## 1. Contexto e ponto de partida

A Fase 5 entregou um sistema de agentes CrewAI completo (8 agentes, 4
crews, 10 tools, RAG ChromaDB com 25 papers, CLI dev) capaz de produzir
um `FinalAnswer` markdown com visualizações Plotly e citações DOI a
partir de uma pergunta em linguagem natural.

A Fase 6 conecta esse sistema a uma **interface web única** —
fechando a stack ponta-a-ponta para o usuário final. Pesquisadores,
gestores e estudantes podem fazer perguntas via browser e ver
respostas adaptadas ao seu perfil em tempo real (streaming), com
gráficos interativos e referências bibliográficas clicáveis.

### Ponto de partida quantitativo

```
frontend/ scaffold da Fase 0:
  Next.js 14.2.5 App Router  ✅
  TypeScript strict           ✅
  Tailwind CSS               ❌ (nao configurado)
  shadcn/ui                  ❌
  Zustand / TanStack Query   ❌
  Plotly.js / react-markdown ❌
  Streaming SSE              ❌
  1 pagina (app/page.tsx hello world)
```

### Insumos disponíveis

- **Backend FastAPI estavel** em `http://localhost:8000`:
  - 4 endpoints de dados sobre marts Gold (Fase 4)
  - OpenAPI auto-gerado em `/docs` (Swagger UI)
- **Sistema de agentes** (Fase 5):
  - `python -m src.cli "<pergunta>"` produz `FinalAnswer`
  - `agents.crews.run_master(question) -> FinalAnswer` como Python API
- **Schemas Pydantic v2** em `agents/src/schemas.py` que serao
  espelhados em TypeScript: `FinalAnswer`, `VizSpec`, `Citation`,
  `IntentDecision`, etc.

---

## 2. Objetivos da Fase 6

### 2.1 Objetivos primários

1. **Workspace unificado** com layout 3 colunas (sidebar + workspace +
   context panel) seguindo wireframe `docs/architecture/frontend-arch.jsx`.
2. **Chat interface** com streaming SSE — usuario ve resposta sendo
   construida em tempo real (markdown progressivo + agent reasoning
   steps).
3. **Visualizacao Plotly** embutida na resposta via `react-plotly.js`
   consumindo `VizSpec.plotly_figure`.
4. **Citation panel** lateral mostrando DOIs com snippets e links
   externos.
5. **Adaptacao automatica ao perfil** detectado pelo sistema de agentes
   (3 temas visuais sutis: researcher / policy / student).
6. **Endpoint `/api/chat/stream`** novo no `api/` que executa
   `run_master` em background e emite SSE com eventos por agente.
7. **Tipos TypeScript do OpenAPI** gerados via `openapi-typescript`
   apontando para o `api/`.

### 2.2 Objetivos secundários

8. **Data Explorer** para navegar marts Gold (catalog + preview).
9. **Library** para ver historico de citacoes acumuladas.
10. **Testes E2E** com Playwright cobrindo fluxo "fazer pergunta -> ver
    resposta com viz + citacao".
11. **Deploy local via Caddy** (HTTPS interno) preparado para producao.

### 2.3 Não-objetivos (escopo de Fases 7+)

- **Authentication** (sistema academico privado).
- **Multi-tenant** (sem usuarios concorrentes).
- **Mobile first** — desktop OK, mobile passable.
- **Internationalization** (apenas pt-BR).
- **PWA / offline mode**.
- **Editor markdown WYSIWYG**.

---

## 3. Decisões arquiteturais propostas

### 3.1 Tailwind 3.4 (não 4.0)

**Por quê.** O `CLAUDE.md` diz "Tailwind 4.x", mas:

- Tailwind 4 (Oxide engine, lançado early-2025) ainda tem migration
  story imatura com shadcn/ui (que é a biblioteca de componentes
  escolhida).
- Tailwind 3.4 é battle-tested, totalmente suportado por shadcn/ui v2,
  com ferramentas (PostCSS, plugins) maduras.
- Upgrade para Tailwind 4 fica como ADR futura quando shadcn/ui
  estabilizar suporte oficial.

Decisão será documentada em ADR 0004 no Sprint 6.6.

### 3.2 shadcn/ui (Radix + Tailwind), não componente library externa

**Por quê.**

- Componentes copiados para `components/ui/` (não dependência npm) —
  customizáveis sem fork.
- Radix primitives garantem acessibilidade (ARIA, keyboard nav).
- Sem lock-in de design system pesado (vs Material/Chakra).
- Bundle size enxuto (tree-shakeable).

### 3.3 Zustand para estado global, TanStack Query para servidor

| Estado | Ferramenta |
|---|---|
| Perfil detectado, histórico chat, sessão atual | Zustand |
| Catálogo de marts, preview, OpenAPI types | TanStack Query (cache) |
| Local de componente (input value, modal aberto) | useState |

Por que Zustand vs Context: Zustand evita re-renders desnecessários e
não exige Provider tree.

### 3.4 Streaming SSE com `EventSource` nativo

**Por quê.** Server-Sent Events é o padrão para uni-directional streaming
HTTP. Browsers suportam via `EventSource` API nativa — sem precisar de
WebSocket nem libs extras.

O endpoint `POST /api/chat/stream` (a criar no `api/`) emite eventos:

```
event: agent_started
data: {"agent": "Orchestrator", "ts": ...}

event: tool_called
data: {"tool": "data_compare", "args": {...}, "ts": ...}

event: partial_markdown
data: {"chunk": "...", "ts": ...}

event: final_answer
data: {<FinalAnswer JSON>}

event: error
data: {"error": "...", "ts": ...}
```

### 3.5 Tipos TypeScript gerados do OpenAPI

`openapi-typescript` lê `http://localhost:8000/openapi.json` e gera
`frontend/types/api.ts`. Re-roda no `npm run gen:api-types`. Garante
contrato cliente↔servidor sem duplicação manual.

Sprint 6.0 começa com tipos espelhados manualmente (rápido) e migra
para auto-geração no Sprint 6.1 (junto com o endpoint SSE).

### 3.6 react-plotly.js (não Recharts) para `VizSpec`

`VizSpec.plotly_figure` é um Plotly figure dict. Renderizar é
`<Plot data={fig.data} layout={fig.layout} />`. Recharts seria
incompatível.

Trade-off: `plotly.js-dist-min` é ~3 MB. Mitigamos com:
- Dynamic import (`next/dynamic` com `ssr: false`)
- Chunk separado via Next bundle splitting

### 3.7 React Markdown + remark-gfm para markdown do `FinalAnswer`

Suporta tabelas, task lists, syntax highlighting (via plugin opcional).
Renderização segura sem `dangerouslySetInnerHTML`.

### 3.8 3 temas visuais sutis (researcher / policy / student)

Não 3 designs distintos — apenas variações:
- **researcher**: tom mais sóbrio (tipografia serif para corpo, sem
  emojis), tabelas com mais densidade, bullets numéricos.
- **policy**: tom institucional (azul/cinza), boxes destacados para
  "PNE meta 20", referências territoriais.
- **student**: tom amigável (sans-serif arredondada), glossário
  inline com tooltips, callouts coloridos.

Implementação: classe CSS no `<body>` baseada em
`useProfileStore().profile`. Tailwind `data-profile="researcher"`
seletor.

### 3.9 Página principal: `/compare` (não `/`)

`/` redireciona para `/compare`. Isso permite ter outras rotas
(`/dashboards`, `/explorer`, `/library`) sem confusão.

---

## 4. Componentes e layout

### 4.1 Estrutura de diretórios proposta

```
frontend/
├── app/
│   ├── layout.tsx                 (root, com QueryClientProvider)
│   ├── page.tsx                   (redirect -> /compare)
│   ├── compare/
│   │   └── page.tsx               (chat principal — Sprint 6.0)
│   ├── explorer/
│   │   └── page.tsx               (data explorer — Sprint 6.4)
│   ├── library/
│   │   └── page.tsx               (citations history — Sprint 6.4)
│   └── globals.css                (Tailwind directives)
├── components/
│   ├── ui/                        (shadcn/ui — Button, Card, etc.)
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Workspace.tsx
│   │   └── ContextPanel.tsx
│   ├── chat/
│   │   ├── Chat.tsx               (Sprint 6.2)
│   │   ├── MessageBubble.tsx
│   │   ├── AgentReasoning.tsx
│   │   ├── InputBox.tsx
│   │   └── StreamingMarkdown.tsx
│   ├── charts/
│   │   ├── InlineChart.tsx        (Sprint 6.3)
│   │   └── PlotlyLazy.tsx         (dynamic import wrapper)
│   ├── citations/
│   │   ├── CitationPanel.tsx      (Sprint 6.3)
│   │   └── CitationCard.tsx
│   └── explorer/
│       ├── DataExplorer.tsx       (Sprint 6.4)
│       └── MartCard.tsx
├── lib/
│   ├── api-client.ts              (fetch wrapper + SSE parser)
│   ├── stores/
│   │   ├── chatStore.ts
│   │   └── profileStore.ts
│   ├── utils/
│   │   └── cn.ts                  (clsx + tailwind-merge)
│   └── query-client.ts            (TanStack Query config)
├── types/
│   ├── api.ts                     (gerado por openapi-typescript)
│   └── domain.ts                  (FinalAnswer, VizSpec, Citation espelhados)
├── tests/
│   ├── e2e/                       (Playwright — Sprint 6.5)
│   └── unit/                      (Vitest + RTL)
├── public/
├── components.json                (shadcn/ui config)
├── tailwind.config.ts
├── postcss.config.js
└── package.json
```

### 4.2 Layout 3 colunas (compare/page.tsx)

```
┌──────────┬──────────────────────────┬────────────────┐
│ Sidebar  │ Workspace                │ Context Panel  │
│ (280px)  │ (flex-1, max-w-3xl)      │ (320px)        │
│          │                          │                │
│ - Logo   │ [chat history scroll]    │ Sources        │
│ - Nav    │                          │ Citations      │
│   /comp  │ ┌──────────────────────┐ │ SQL/Tools used │
│   /expl  │ │ user: pergunta...    │ │ Profile        │
│   /lib   │ ├──────────────────────┤ │ Export         │
│ - Hist.  │ │ [agent reasoning]    │ │                │
│ - Settgs │ │ assistant: resposta │ │                │
│          │ │ [InlineChart]       │ │                │
│          │ └──────────────────────┘ │                │
│          │                          │                │
│          │ [InputBox] [Send btn]    │                │
└──────────┴──────────────────────────┴────────────────┘
```

Responsivo: sidebar e context panel viram drawer em < 1024px.

---

## 5. Padrões de código

### 5.1 Convenções TypeScript

- **strict: true** (já está)
- **noUncheckedIndexedAccess: true** (a adicionar em Sprint 6.0)
- Imports absolutos com alias `@/`
- Server Components por default; `"use client"` apenas onde necessário
  (estado, eventos, hooks)
- Sem `any` exceto em tipos do Plotly (via @types/plotly.js)

### 5.2 Estilização

- Tailwind utility-first
- `cn(...)` helper para merge de classes condicionais
- Variáveis CSS no `globals.css` para temas (`--bg`, `--fg`, etc.)
- Sem CSS modules nem styled-components

### 5.3 Estado

- Zustand stores em `lib/stores/`
- Cada store exporta hook `use<Name>Store`
- Server state via TanStack Query — nunca `useEffect + fetch`

### 5.4 Erros e loading

- Suspense boundaries para Server Components
- `<ErrorBoundary>` em rotas client-side
- Skeletons para loading (não spinners)

---

## 6. Estratégia de testes

### 6.1 Pirâmide

```
         /\        E2E (Playwright)
        /  \       3-5 fluxos canônicos: pergunta -> resposta com viz + citação
       /----\
      /      \     Component tests (Vitest + React Testing Library)
     /        \    componentes complexos: Chat, InlineChart, CitationPanel
    /----------\
   /            \  Unit (Vitest)
                   utils, stores, parsers SSE
```

### 6.2 Cobertura-alvo

- `lib/`: 90%+ (utils, stores, api-client, SSE parser)
- `components/`: 60%+ (foco em lógica)
- E2E: golden path + 1-2 erros por sprint

### 6.3 Mock do backend em testes

- Vitest: `msw` (Mock Service Worker) para fetch + SSE
- Playwright: gravação de fixtures HAR ou mock direto via interception

---

## 7. Sequência de implementação (sprints)

| Sprint | Foco | Entregáveis | Duração |
|---|---|---|---|
| **6.0** | Scaffold + Tailwind + shadcn + layout 3 colunas | deps, configs, stores básicos, `/compare` shell | 3 dias |
| **6.1** | Endpoint `/api/chat/stream` SSE no `api/` + tipos OpenAPI | router chat.py, AsyncIterator wrapping run_master, frontend SSE parser | 2 dias |
| **6.2** | `<Chat>` + `<AgentReasoning>` + streaming UI | chat funcional ponta-a-ponta com mock + streaming markdown | 3 dias |
| **6.3** | `<InlineChart>` Plotly + `<CitationPanel>` | viz interativa + DOIs clicáveis | 2 dias |
| **6.4** | `<DataExplorer>` + adaptação tema por perfil | navegação catálogo + 3 temas | 3 dias |
| **6.5** | Testes E2E Playwright + deploy local Caddy | ≥3 testes E2E, Caddyfile, smoke production build | 2 dias |
| **6.6** | Conclusão + ADR 0004 (frontend arch) | `fase-6-conclusao.md`, ADR | 1 dia |
| **Total Fase 6** | | | **~16 dias úteis** |

### 7.1 Marcos por sprint

- **Após 6.0**: `npm run dev` mostra layout 3 colunas com placeholder; `npm test` ≥ 5 testes verdes (utils + stores).
- **Após 6.1**: `curl -N POST /api/chat/stream` emite eventos SSE; tipos TypeScript regenerados.
- **Após 6.2**: usuário digita pergunta no browser e vê resposta sendo construída (com mock backend).
- **Após 6.3**: resposta inclui gráfico Plotly interativo e painel lateral de citações.
- **Após 6.4**: usuário pode navegar `/explorer` e ver tema diferente em `/compare` se perfil mudar.
- **Após 6.5**: `npx playwright test` 3+ testes verdes; `docker compose up frontend` serve em :3000 via Caddy.

---

## 8. Riscos e mitigações

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|
| R1 | Bundle Plotly muito pesado (~3 MB) | alta | médio | dynamic import + ssr:false; chunk separado |
| R2 | SSE quebra em proxies/firewalls | baixa | alto | Caddy passa SSE OK; fallback polling adiado |
| R3 | shadcn/ui breaking change | baixa | baixo | components copiados ao repo, versão pin via copy semantics |
| R4 | TypeScript strict + Plotly types | média | baixo | @types/plotly.js incompletos — usar `as any` localizado |
| R5 | TanStack Query v5 breaking | baixa | médio | pin version exata; release notes |
| R6 | Tailwind 4 vs 3 confusion | média | baixo | escolher 3.4 explicit; documentar ADR 0004 |
| R7 | Streaming markdown parse errors | média | médio | accumulate buffer + parse on every chunk OR re-parse on final |
| R8 | E2E flaky por timing SSE | alta | médio | Playwright `waitForFunction` em vez de timeouts fixos |

---

## 9. Critérios de aceitação

A Fase 6 está **concluída** quando:

1. ✅ Layout 3 colunas renderiza em `/compare`
2. ✅ `npm run build` produz bundle < 600 KB initial JS (sem Plotly chunk)
3. ✅ `npm test` ≥ 25 testes verdes
4. ✅ Endpoint `/api/chat/stream` emite SSE válido em curl
5. ✅ Pergunta canônica ("BR vs FIN gasto 2020") produz markdown +
   InlineChart Plotly + CitationPanel com ≥1 DOI no browser
6. ✅ Mudança de perfil (researcher → student) re-tema visualmente
7. ✅ `npx playwright test` ≥ 3 testes E2E verdes
8. ✅ `docker compose up` serve frontend em :3000 via Caddy
9. ✅ ADR 0004 + `fase-6-conclusao.md` criados

---

*Próximo passo: implementar Sprint 6.0 (scaffold + Tailwind + shadcn +
layout 3 colunas + stores). Ver progresso em
`docs/phases/fase-6-sprint-6.0-progresso.md` (a criar).*
