# Fase 6 — Sprint 6.4 (`<DataExplorer>` + temas + ErrorBoundary) — Progresso

> Estado da Sprint 6.4 da Fase 6 (Frontend Next.js 14).
> Complementa [`fase-6-analise.md`](./fase-6-analise.md) e
> [`fase-6-sprint-6.3-progresso.md`](./fase-6-sprint-6.3-progresso.md).
> **Data:** 2026-05-05
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Completar o workspace com 3 frentes:

- **`<DataExplorer>`** — página `/explorer` real consumindo
  `/api/data/catalog` via TanStack Query, com filtro por texto/tag e
  detalhe lateral do mart selecionado.
- **`<ChartErrorBoundary>`** — pendência da Sprint 6.3: isola falhas
  do Plotly para que erro de render do gráfico não derrube a bolha
  inteira da resposta.
- **Refinar temas por perfil** — garantir que researcher / policy /
  student geram mudanças visuais perceptíveis (ring color, transição
  suave, line-height por perfil) e adicionar tooltip explicativo no
  seletor.

---

## 2. Entregáveis

### 2.1 Componentes novos

| Arquivo | Linhas | Descrição |
|---|---|---|
| `frontend/lib/hooks/useCatalog.ts` | 35 | TanStack Query `useCatalog()` que chama `apiGet<CatalogResponse>('/api/data/catalog')`; tipos `MartCatalogItem`, `CatalogResponse` exportados |
| `frontend/components/explorer/MartCard.tsx` | 75 | Card clicável com nome curto (sem prefixo `mart_`), descrição truncada, contagens em pt-BR, tags inline; `aria-pressed` para selected |
| `frontend/components/explorer/DataExplorer.tsx` | 250 | Layout 2-col interno (lista 420px + detalhe). Filtros: search por texto + chips de tag. Estados loading/error (com retry) / empty filter. Detalhe mostra cards de linhas, colunas, tags + placeholder de preview |
| `frontend/components/charts/ChartErrorBoundary.tsx` | 55 | Class component com `getDerivedStateFromError` + `componentDidCatch`. Fallback compacto âmbar com mensagem do erro |

### 2.2 Edições

| Arquivo | Mudança |
|---|---|
| `frontend/app/explorer/page.tsx` | troca placeholder por `<DataExplorer>` |
| `frontend/components/chat/MessageBubble.tsx` | envolve `<InlineChart>` em `<ChartErrorBoundary>` |
| `frontend/components/chat/Chat.tsx` | adicionado `PROFILE_HINT` e `title` nos botões do seletor |
| `frontend/app/globals.css` | +`--ring` por perfil; transição suave de 180ms em cores; `letter-spacing`/`line-height` para `[data-profile='student'] .prose-body` |

### 2.3 Tests novos (RTL)

| Arquivo | Linhas | Testes |
|---|---|---|
| `frontend/tests/unit/MartCard.test.tsx` | 60 | 6 (nome truncado, descrição, formatação pt-BR, tags, onClick, aria-pressed) |
| `frontend/tests/unit/ChartErrorBoundary.test.tsx` | 55 | 3 (children sem erro, fallback ao throw, custom title) |
| `frontend/tests/unit/DataExplorer.test.tsx` | 140 | 5 (loading, lista após fetch, filtro por texto, click → detalhe, error com retry) — usa `QueryClient` isolado por teste e mock de `fetch` |

**Total Sprint 6.4: ~660 linhas TS/TSX.**

---

## 3. Decisões aplicadas

### 3.1 ✅ TanStack Query com `staleTime` global de 5 min

`useCatalog` herda os defaults do `makeQueryClient()` (Sprint 6.0).
Catálogo Gold muda raramente → cache 5 min é seguro e evita refetch
toda vez que o usuário navega de `/compare` para `/explorer` e volta.

### 3.2 ✅ Layout interno do explorer: 420px lista + flex-1 detalhe

Lista (esquerda) tem largura fixa porque os cards têm conteúdo
relativamente uniforme. Detalhe ocupa o resto do espaço com `max-w-2xl`
auto-centrado. Padrão "master-detail" clássico, ideal para 5-15 marts.

### 3.3 ✅ Filtro composto: texto OR + tag AND

`filtered = matchesText && matchesTag`. Texto busca em `name` e
`description` (case-insensitive). Tag chip funciona como filtro
exclusivo — clicar no mesmo desativa. Botão "todos" reset.

### 3.4 ✅ Preview de linhas adiado

`/api/data/:dataset/preview` não existe ainda no gateway (Fase 4
listou como débito técnico). Sprint 6.4 mostra apenas card "Endpoint
ainda não implementado". Quando o api/ adicionar (`Sprint futura`),
basta plug-in adicional no DataExplorer.

### 3.5 ✅ `<ChartErrorBoundary>` como class component (React 18)

React 18 não oferece error boundaries em hooks — precisa ser classe
com `getDerivedStateFromError` + `componentDidCatch`. Mantemos local
ao componente `<InlineChart>` em vez de boundary global: erro de
gráfico mostra fallback inline, mas o resto da resposta (markdown,
citações, fontes) permanece visível.

### 3.6 ✅ Mock de `console.error` nos tests do ErrorBoundary

React loga errors ruidosamente quando boundary captura. `vi.spyOn(console, 'error').mockImplementation(() => {})` no `beforeEach` mantém output do test runner limpo.

### 3.7 ✅ Tema: `--ring` por perfil + transição global

Cada perfil agora também customiza `--ring` (cor de focus outline).
Transição de 180ms em `background-color, border-color, color, fill,
stroke` no seletor `*` faz a mudança de perfil visualmente fluida (não
flicker).

Tooltip nos botões via `title` prop nativo (acessível, sem JS extra) —
hover mostra resumo do que cada perfil muda:
- Researcher: "Tom técnico, fontes serif, z-scores e DOIs visíveis, sem emojis."
- Policy: "Foco em decisão e PNE meta 20, tons institucionais, números arredondados."
- Student: "Tom amigável, glossário inline, tipografia mais aberta, accent verde."

### 3.8 ✅ `useMemo` em `marts` para satisfazer `react-hooks/exhaustive-deps`

`data?.data ?? []` cria array novo a cada render — fazendo `useMemo`
de `allTags` e `filtered` re-rodar. Memoizar `marts` em
`useMemo<MartCatalogItem[]>(() => data?.data ?? [], [data])` resolve.

### 3.9 ⚠️ DataExplorer não tem ScrollArea Radix nesta sprint

A lista usa `overflow-y-auto` nativo. ScrollArea do Radix entra no
Sprint 6.5 se a estética da scrollbar virar prioridade.

---

## 4. Métricas finais

```
Linhas TS/TSX adicionadas:     ~660 (src + tests Sprint 6.4)

Testes vitest TOTAL:           77 / 77 PASS (~2.7s)
  - novos Sprint 6.4:          14 testes (6 MartCard + 3 ErrorBoundary + 5 DataExplorer)

Lint:                          ✅ 0 warnings ESLint
Build:                         ✅ next build OK
First Load JS por rota:
  /                            87.3 KB
  /compare                     160 KB    (era 159; +1 KB ChartErrorBoundary)
  /explorer                    118 KB    (era 105; +13 KB DataExplorer + ícones)
  /library                     105 KB
```

---

## 5. Próximo: Sprint 6.5 (Playwright E2E + Caddy + openapi-typescript)

Sprint 6.5 fecha com testes ponta-a-ponta e deploy local.

### 5.1 Entregáveis previstos

- `frontend/playwright.config.ts` + `frontend/tests/e2e/`
- 3-5 testes Playwright cobrindo:
  - `/compare` mostra layout 3 colunas e seletor de perfil
  - `/explorer` mostra catálogo (com mock fetch ou api real up)
  - Click em pergunta exemplo seed → InputBox preenchido
  - Tema visual muda ao trocar perfil
- `infra/caddy/Caddyfile` com routes para `:8000` e `:8001`
- Geração de tipos via `npm run gen:api-types` apontando para
  `http://localhost:8000/openapi.json`
- Smoke test de `npm run build && npm start` em container

### 5.2 Critério de avanço

`npx playwright test` passa 3+ testes; `docker compose up frontend
agents api caddy` serve a stack inteira em `:443` (HTTPS interno).

---

## 6. Pendências registradas

1. ⏳ Playwright E2E + Caddy — Sprint 6.5.
2. ⏳ openapi-typescript geração — Sprint 6.5.
3. ⏳ ADR 0004 (frontend arch) — Sprint 6.6.
4. ⚠️ Endpoint `/api/data/:dataset/preview` ainda não existe no api/.
   DataExplorer mostra placeholder. Adicionar em sprint futura
   (não-bloqueante).
5. ⚠️ ScrollArea Radix não usado — overflow nativo basta. Refinar se
   estética virar prioridade.
6. ⚠️ Transição de perfil aplica em `*` — pode ser custosa em árvores
   muito grandes. Em prática a app tem ~100-200 elementos visíveis,
   irrelevante. Monitorar.

---

*Próximo doc: `fase-6-sprint-6.5-progresso.md` (a criar quando Sprint
6.5 começar).*
