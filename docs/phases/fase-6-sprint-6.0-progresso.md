# Fase 6 — Sprint 6.0 (Scaffold + Tailwind + shadcn + Layout 3 colunas) — Progresso

> Estado da Sprint 6.0 da Fase 6 (Frontend Next.js 14).
> Complementa [`fase-6-analise.md`](./fase-6-analise.md).
> **Data:** 2026-04-30
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Pôr de pé o scaffold do frontend com:

- Tailwind 3.4 + PostCSS configurados (sem emojis, paleta sóbria
  inspirada no scaffold da Fase 0)
- shadcn/ui base (`<Button>`, `<Card>`) com variáveis CSS por perfil
- Layout 3 colunas em `/compare` (Sidebar + Workspace + ContextPanel)
- Stores Zustand iniciais (`profileStore`, `chatStore`)
- Cliente API com tratamento de erros (`apiFetch`, `ApiError`)
- TanStack Query setup (provider client-side)
- Vitest + React Testing Library + happy-dom para tests
- Tipos TypeScript de domínio espelhados de `agents/src/schemas.py`

---

## 2. Entregáveis

### 2.1 Configurações novas

| Arquivo | Descrição |
|---|---|
| `tailwind.config.ts` | Tailwind 3.4 com paleta via CSS vars + cor `brasil` (#c0392b) espelhando viz_tools.py |
| `postcss.config.js` | PostCSS + autoprefixer |
| `components.json` | shadcn/ui config (style default, baseColor slate, paths @/) |
| `vitest.config.ts` | Vitest 2 + happy-dom + alias @/ + setupFiles |
| `tsconfig.json` | adicionado `noUncheckedIndexedAccess: true` |
| `.prettierrc.json` | adicionado `prettier-plugin-tailwindcss` |
| `package.json` | +14 deps (zustand, tanstack, tailwind, vitest, lucide, radix, etc.) |

### 2.2 Código novo

| Arquivo | Linhas | Descrição |
|---|---|---|
| `app/layout.tsx` | 22 | Root com `<QueryProvider>` + `<ProfileTheme>` + globals.css |
| `app/page.tsx` | 4 | Redirect `/` → `/compare` |
| `app/globals.css` | 75 | Tailwind directives + 3 temas via `[data-profile="..."]` |
| `app/compare/page.tsx` | 22 | Layout 3 colunas com `ChatPlaceholder` |
| `app/explorer/page.tsx` | 30 | Shell com placeholder (Sprint 6.4) |
| `app/library/page.tsx` | 30 | Shell com placeholder (Sprint 6.4) |
| `components/ui/button.tsx` | 50 | shadcn Button com 5 variants × 4 sizes (cva) |
| `components/ui/card.tsx` | 50 | Card + Header + Title + Description + Content + Footer |
| `components/layout/Sidebar.tsx` | 60 | Nav lateral 260px com 3 rotas + ícones lucide |
| `components/layout/Workspace.tsx` | 12 | Container central flex-1 |
| `components/layout/ContextPanel.tsx` | 65 | Painel direito 320px com sessão + sources + citations preview |
| `components/layout/ProfileTheme.tsx` | 16 | Aplica `data-profile=...` no `<html>` para os 3 temas |
| `components/layout/QueryProvider.tsx` | 14 | TanStack Query provider client-side |
| `components/chat/ChatPlaceholder.tsx` | 110 | Header + perguntas exemplo + input box + seletor de perfil |
| `lib/utils/cn.ts` | 14 | clsx + tailwind-merge helper |
| `lib/stores/profileStore.ts` | 25 | Zustand: perfil + manualOverride lock |
| `lib/stores/chatStore.ts` | 80 | Zustand: messages + streaming events + finalize |
| `lib/query-client.ts` | 23 | makeQueryClient com defaults academicos (staleTime 5min) |
| `lib/api-client.ts` | 70 | apiFetch + ApiError + apiGet/apiPost + getApiBaseUrl |
| `types/domain.ts` | 110 | FinalAnswer, VizSpec, Citation, IntentDecision, StreamEvent espelhados |
| `tests/unit/setup.ts` | 7 | jest-dom matchers + cleanup |
| `tests/unit/cn.test.ts` | 22 | 4 testes do helper cn |
| `tests/unit/profileStore.test.ts` | 35 | 4 testes do store de perfil |
| `tests/unit/chatStore.test.ts` | 60 | 4 testes do store de chat |
| `tests/unit/api-client.test.ts` | 75 | 5 testes do cliente HTTP (env, status code, parse error) |

**Total Sprint 6.0: ~1.080 linhas TS/TSX + ~120 linhas CSS/config.**

---

## 3. Decisões aplicadas

### 3.1 ✅ Tailwind 3.4 (não 4.0) — documentar em ADR 0004

CLAUDE.md cita "Tailwind 4.x" mas shadcn/ui v2 ainda tem suporte
oficial para Tailwind 3.4 (battle-tested). Tailwind 4 (Oxide engine)
fica como upgrade futuro quando shadcn estabilizar.

### 3.2 ✅ shadcn/ui via cópia, sem dependência npm

`<Button>` e `<Card>` copiados para `components/ui/`, baseados em Radix
+ cva. Customizáveis sem fork. Próximas Sprints adicionam outros
componentes conforme demanda (Dialog, Tabs, ScrollArea, etc).

### 3.3 ✅ Variáveis CSS por perfil em `[data-profile="..."]`

3 temas sutis sem 3 designs distintos:
- `researcher` (default): tom sóbrio, slate, font-serif no corpo
- `policy`: tom institucional, primary mais azul
- `student`: tom amigável, primary verde, radius maior

`<ProfileTheme>` é um Client Component que faz `document.documentElement.dataset.profile = profile`. Mudança de perfil no
seletor (Sprint 6.0) ou via detecção do Orchestrator (Sprint 6.2) é
imediata.

### 3.4 ✅ Stores Zustand sem Provider tree

`useProfileStore()` e `useChatStore()` exportam hooks diretos. Evita
re-renders em árvore via Context.

`profileStore` tem flag `manualOverride` — uma vez que o usuário escolhe
manualmente, detecção automática não sobrescreve.

`chatStore` modela streaming: `pushUserMessage` → `startAssistantMessage` →
`appendEvent` × N → `appendMarkdownChunk` × N → `finalizeAssistantMessage`.
Sprint 6.2 vai consumir SSE neste shape.

### 3.5 ✅ `api-client.ts` lê body como texto e tenta JSON.parse

Descoberto durante Sprint 6.0: `Response.body` só pode ser lido uma vez
em `fetch`. Ler `.json()` e fallback `.text()` falha. Solução: ler
`.text()` primeiro, tentar `JSON.parse`, fallback string crua. Validado
em `test_api_client_keeps_text_body_when_JSON_parse_fails`.

### 3.6 ✅ TanStack Query sem hidratação SSR (por enquanto)

`makeQueryClient()` é instanciado client-side via `useState`. Sprint 6.4
pode adicionar hidratação se houver server-side fetching pesado. Por
ora, todas as queries são client-side — simpler, sem trade-off real
para tela única de chat.

### 3.7 ⚠️ Conflito npm peer: vite 7 vs @types/node 20

`@vitejs/plugin-react@4.3.x` puxava `vite@^5 || ^6 || ^7` e o resolver
escolheu vite 7, que requer `@types/node` mais novo. Solução: pinar
`vite: ^5.4.0` explicitamente em devDependencies. Documentado.

### 3.8 ✅ Tipos espelhados de `agents/schemas.py`, não importados

Por mesmo motivo do Sprint 5.0 (api/agents): venvs separados,
`frontend/` em outro stack (TS). Quando endpoint `/api/chat/stream`
estabilizar (Sprint 6.1), migrar para `openapi-typescript` auto-geração.

### 3.9 ✅ Bundle inicial < 110 KB First Load JS

`/compare`: 4.67 KB página + 87 KB shared = **108 KB First Load JS**.
Plotly fica fora (Sprint 6.3 com dynamic import). Margem de ~490 KB
até o alvo de 600 KB.

---

## 4. Métricas finais

```
Pacotes npm instalados:        +297 (resolvidos via npm install)
Tamanho node_modules:          ~280 MB
Linhas TS/TSX adicionadas:     ~1.080 (src + tests)
Linhas CSS/config:             ~120

Testes vitest:                 17 / 17 PASS (~2.2s)
  - cn helper:                 4 testes
  - profileStore:              4 testes
  - chatStore:                 4 testes
  - api-client:                5 testes

Lint:                          ✅ 0 warnings ESLint
Build:                         ✅ next build OK
First Load JS:                 87 KB (shared) + 4.67 KB (/compare) = 108 KB
                               (Plotly fica em chunk separado Sprint 6.3)
```

Saída do `npm test`:

```
✓ tests/unit/api-client.test.ts (5 tests) 12ms
✓ tests/unit/profileStore.test.ts (4 tests) 5ms
✓ tests/unit/chatStore.test.ts (4 tests) 8ms
✓ tests/unit/cn.test.ts (4 tests) 13ms

Test Files  4 passed (4)
     Tests  17 passed (17)
  Duration  2.16s
```

Saída do `npm run build`:

```
Route (app)                              Size     First Load JS
┌ ○ /                                    137 B          87.2 kB
├ ○ /_not-found                          871 B          87.9 kB
├ ○ /compare                             4.67 kB         108 kB
├ ○ /explorer                            2.09 kB         105 kB
└ ○ /library                             2.09 kB         105 kB
+ First Load JS shared by all            87.1 kB
```

---

## 5. Estrutura do `frontend/` após Sprint 6.0

```
frontend/
├── package.json               (+14 deps; vite 5 pinado)
├── tsconfig.json              (+ noUncheckedIndexedAccess)
├── tailwind.config.ts         ✅ NOVO
├── postcss.config.js          ✅ NOVO
├── components.json            ✅ NOVO (shadcn/ui)
├── vitest.config.ts           ✅ NOVO
├── .prettierrc.json           (+ prettier-plugin-tailwindcss)
├── app/
│   ├── globals.css            ✅ NOVO (Tailwind + 3 temas)
│   ├── layout.tsx             (refeito: QueryProvider + ProfileTheme)
│   ├── page.tsx               (refeito: redirect /compare)
│   ├── compare/page.tsx       ✅ NOVO (layout 3 colunas)
│   ├── explorer/page.tsx      ✅ NOVO (placeholder)
│   └── library/page.tsx       ✅ NOVO (placeholder)
├── components/
│   ├── ui/
│   │   ├── button.tsx         ✅ NOVO (shadcn)
│   │   └── card.tsx           ✅ NOVO (shadcn)
│   ├── layout/
│   │   ├── Sidebar.tsx        ✅ NOVO
│   │   ├── Workspace.tsx      ✅ NOVO
│   │   ├── ContextPanel.tsx   ✅ NOVO
│   │   ├── ProfileTheme.tsx   ✅ NOVO
│   │   └── QueryProvider.tsx  ✅ NOVO
│   ├── chat/
│   │   └── ChatPlaceholder.tsx ✅ NOVO (Sprint 6.2 substitui por Chat real)
│   ├── charts/                 (vazio, Sprint 6.3)
│   ├── citations/              (vazio, Sprint 6.3)
│   └── explorer/               (vazio, Sprint 6.4)
├── lib/
│   ├── utils/cn.ts            ✅ NOVO
│   ├── stores/
│   │   ├── profileStore.ts    ✅ NOVO
│   │   └── chatStore.ts       ✅ NOVO
│   ├── api-client.ts          ✅ NOVO
│   └── query-client.ts        ✅ NOVO
├── types/
│   └── domain.ts              ✅ NOVO (FinalAnswer, VizSpec, Citation, ...)
└── tests/
    ├── unit/
    │   ├── setup.ts           ✅ NOVO
    │   ├── cn.test.ts         ✅ NOVO (4)
    │   ├── profileStore.test.ts ✅ NOVO (4)
    │   ├── chatStore.test.ts  ✅ NOVO (4)
    │   └── api-client.test.ts ✅ NOVO (5)
    └── e2e/                    (vazio, Sprint 6.5 — Playwright)
```

---

## 6. Próximo: Sprint 6.1 (Endpoint `/api/chat/stream` SSE + tipos OpenAPI)

A Sprint 6.1 adiciona o endpoint streaming no `api/` que executa
`run_master` em background e emite SSE com eventos por agente.

### 6.1 Entregáveis previstos

- `api/src/routers/chat.py` — `POST /api/chat/stream` com `StreamingResponse`
  e `text/event-stream`
- Wrapping de `run_master` em `AsyncIterator` que captura logs structlog
  e emite eventos
- `api/src/schemas/chat.py` — `ChatRequest`, `ChatStreamEvent`
- Testes integração `api/tests/routers/test_chat_stream.py` com TestClient
- `frontend/lib/sse-parser.ts` — parser de SSE (EventSource não funciona
  com POST; usar `fetch` + `ReadableStream`)
- `frontend/npm run gen:api-types` rodável (api up) → `frontend/types/api.ts`
- Atualizar `types/domain.ts` para re-export from gerado

### 6.2 Critério de avanço

`curl -N -X POST http://localhost:8000/api/chat/stream -d '{"question":"..."}'`
retorna stream de eventos SSE válidos (event: + data:) terminando em
`event: final_answer`.

---

## 7. Pendências registradas

1. ⏳ Endpoint `/api/chat/stream` no `api/` — Sprint 6.1.
2. ⏳ Geração automática de tipos via `openapi-typescript` — Sprint 6.1.
3. ⏳ Plotly + react-markdown — Sprint 6.3.
4. ⏳ Playwright E2E — Sprint 6.5.
5. ⏳ ADR 0004 (frontend arch) — Sprint 6.6.
6. ⚠️ ChatPlaceholder tem `<Button type="submit" disabled>` no input — fica habilitado em Sprint 6.2 quando o handler de envio estiver pronto.
7. ⚠️ `noUncheckedIndexedAccess: true` adicionado — requer `?` em qualquer
   acesso por índice. Ajustes pontuais nos tests (ex.: `messages[0]?.role`)
   evitam o erro de tipo.
8. ⚠️ Build emite warning de telemetria do Next.js. Pode ser desabilitado
   via `npx next telemetry disable` se desejado (não fizemos).

---

*Próximo doc: `fase-6-sprint-6.1-progresso.md` (a criar quando Sprint
6.1 começar).*
