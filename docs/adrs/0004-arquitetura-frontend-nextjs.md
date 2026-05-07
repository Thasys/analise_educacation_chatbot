# ADR 0004 — Arquitetura do frontend Next.js: Tailwind + shadcn cópia, Zustand sem Provider, SSE manual via fetch+ReadableStream, Plotly lazy, perfis via CSS vars

- **Status:** aceito
- **Data:** 2026-05-06
- **Fase:** 6 (Frontend Next.js 14)

## Contexto

A Fase 5 entregou um sistema multi-agente CrewAI completo capaz de
produzir um `FinalAnswer` markdown com viz Plotly e citações DOI a
partir de uma pergunta em linguagem natural. A Fase 6 conecta esse
sistema a uma interface web única em Next.js 14 — fechando a stack
ponta-a-ponta.

Esta ADR consolida as decisões tomadas durante as 7 Sprints da Fase 6
(6.0 a 6.6) que não estão claras só pelo código. Algumas vão contra
defaults da indústria (manter Tailwind 3 vs 4, shadcn por cópia vs lib,
SSE manual vs `EventSource`); todas têm trade-offs explícitos.

## Decisões

### 1. Tailwind 3.4 (não 4.0) durante toda a Fase 6

CLAUDE.md cita "Tailwind 4.x", mas Tailwind 4 (Oxide engine, lançado
early-2025) ainda tem migration story imatura com shadcn/ui:

- shadcn/ui v2 oficialmente suporta Tailwind 3.4 como baseline.
- PostCSS plugin clássico do Tailwind 3 é battle-tested; o pipeline
  Oxide é mais novo.
- Migrar para 4 fica como upgrade futuro quando shadcn estabilizar
  suporte oficial — sem ganho operacional óbvio para nosso caso.

Decisão: Tailwind 3.4.6 + `tailwindcss-animate`.

### 2. shadcn/ui via cópia (não dependência npm)

Componentes (`Button`, `Card`) copiados direto para `components/ui/`,
configuração em `components.json`. Vantagens:

- **Customizável sem fork**: ajustamos variants/sizes em arquivos
  versionados.
- **Versão pin via copy semantics**: shadcn atualiza, nada quebra.
- **Bundle enxuto**: sem código morto de componentes não usados.
- **Acessibilidade**: cada componente embarca primitivos Radix
  (focus management, ARIA, keyboard).

Trade-off: atualizar shadcn manualmente quando quiser melhorias
upstream. Aceitável dado o ritmo lento da biblioteca.

### 3. Zustand sem `Provider` tree (hook direto)

```ts
export const useChatStore = create<ChatState>((set) => ({...}));
```

Hook `useChatStore()` consumido diretamente nos componentes. Não há
`<ChatProvider>` em volta da árvore.

Vantagens:
- Re-renders mínimos (só componentes que selecionam o slice mudado).
- Sem prop drilling nem Context boilerplate.
- Stores são módulos Python-like — fácil de testar em isolamento.

Aplicado a 2 stores: `profileStore` (perfil + manualOverride) e
`chatStore` (messages + streaming events).

### 4. TanStack Query somente para state de servidor (não local)

Catálogo do explorer (`useCatalog`) usa TanStack Query com cache 5 min.
Stores Zustand usados para state que muda em response a ação do
usuário (chat, perfil). Local component state via `useState`.

3-tier separation:
- **Server state**: TanStack Query (catalog, preview, OpenAPI types)
- **Global app state**: Zustand (perfil, chat history)
- **Local state**: useState (input value, modal aberto)

### 5. SSE manual via `fetch` + `ReadableStream` (não `EventSource`)

`EventSource` API só suporta GET sem body. Nosso `/api/chat/stream` é
POST com `{question: str}` — exige `fetch`. `Response.body` é um
`ReadableStream<Uint8Array>` que consumimos com `TextDecoder` +
parser SSE manual.

`SseParser` segue spec W3C: bloco termina em `\n\n`, multi-data joined
com `\n`, comments `:` ignorados, primeiro espaço após `:` stripado,
`flush()` drena buffer residual. 11 testes unitários cobrem todos
edge cases.

### 6. Plotly via dynamic import singleton (`plotly.js-basic-dist-min`)

Plotly full = ~3 MB. `basic-dist-min` = ~840 KB e cobre bar / line /
scatter / pie — suficiente para Visualizer Agent (Fase 5).

```ts
// PlotlyLazy.tsx
let cachedComponent: ComponentType | null = null;
async function loadPlotComponent() {
  if (cachedComponent) return cachedComponent;
  const Plotly = (await import('plotly.js-basic-dist-min')).default;
  const factory = (await import('react-plotly.js/factory')).default;
  cachedComponent = factory(Plotly);
  return cachedComponent;
}
```

Vantagens:
- Bundle inicial do `/compare` cresce ~1 KB (só wrapper).
- Plotly real entra em chunk separado, baixado on demand quando viz
  aparece pela primeira vez.
- Tela estática (zero perguntas) nunca carrega Plotly.
- Múltiplas vizes na mesma sessão reusam o componente cacheado.

`useEffect + mountedRef` previne `setState` em componente desmontado.

### 7. `<ChartErrorBoundary>` local ao Plotly (não global)

React 18 não oferece error boundaries em hooks; class component com
`getDerivedStateFromError + componentDidCatch`. Mantemos local: erro
de gráfico mostra fallback compacto inline, **resto da resposta
permanece visível** (markdown, citações, fontes). Boundary global
derrubaria a bolha inteira.

### 8. Adaptação de perfil via CSS variables + `[data-profile="..."]`

Não 3 designs distintos — apenas variações da paleta + tipografia +
arredondamento via tokens CSS:

```css
[data-profile='policy'] {
  --primary: 213 73% 50%;
  --ring: 213 73% 55%;
}
[data-profile='student'] {
  --primary: 158 64% 42%;
  --radius: 0.875rem;
}
[data-profile='researcher'] .prose-body { @apply font-serif; }
```

`<ProfileTheme>` (Client Component) escreve `data-profile` no
`<html>`. Mudança é imediata, sem re-renders React (CSS recalcula
tokens). Validado em E2E.

### 9. Detecção automática de perfil sem sobrescrever override manual

```ts
profileStore.setProfile(profile, manual=false) {
  if (state.manualOverride && !manual) return state;  // ignora
  return { profile, manualOverride: manual || ... };
}
```

Quando agente Core retorna `result.profile`, `useChat` chama
`setProfile(detected)` (sem `manual=true`). Se usuário já clicou
manualmente em outro perfil, a detecção é silenciosamente ignorada.
Validado em E2E (`override sobrevive auto-detect`).

### 10. Markdown via classes utility (não `@tailwindcss/typography`)

`@tailwindcss/typography` adicionaria ~30 KB + estilo opinativo. Em
vez disso, `<StreamingMarkdown>` aplica classes utility direto via
seletores filhos:

```tsx
<div className="[&>h1]:text-xl [&>p]:mb-3 [&_table]:my-3 ...">
  <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
</div>
```

Bundle menor + estilo combina com tema dark + variáveis CSS por
perfil.

### 11. Mini-server `agents-server:8001` separado do `api:8000`

(Decisão herdada da Sprint 6.1 mas relevante para frontend.)

Frontend usa **2 origens** em dev:
- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` (dados)
- `NEXT_PUBLIC_AGENTS_BASE_URL=http://localhost:8001` (chat streaming)

Em produção, Caddy fica em frente:
- `/api/chat/*` → :8001 com `flush_interval -1` (SSE não-bufferizado)
- `/api/data/*` → :8000
- `/*` → :3000

Single origin para o browser; backends fisicamente separados (api
~200 MB venv, agents ~1.9 GB venv com CrewAI).

### 12. Tipos espelhados de `agents/schemas.py` em `frontend/types/domain.ts`

Mesmo motivo dos Sprints 5.0/5.5: serviços têm runtimes (TS / Python)
e venvs distintos. `openapi-typescript` gera `types/api.ts` a partir
do contrato OpenAPI, mas para Sprint 6.6 ainda não consumimos no
runtime — schemas manuais bateram 100% até agora.

Snapshot estático (`types/openapi.snapshot.json`) versionado serve
para detectar drift em PR diff.

### 13. Playwright E2E com `page.route` mockando backend

Sprint 6.5: 9 testes em ~30s. Mocks via `mockCatalog(...)`,
`mockChatStream(sseText)`. NÃO sobe api/agents reais. Vantagens:

- Determinístico (LLM não-determinístico fica para suite live no agents).
- Roda offline (sem dependência de Anthropic, DuckDB, ChromaDB).
- Rápido o suficiente para `pre-push` hook.

Smoke E2E rodando stack inteira fica como pendência (Sprint 6+ ou
futuro).

## Consequências

### Positivas

1. **Bundle inicial enxuto**: `/compare` 158 KB First Load JS (alvo
   < 600 KB). Plotly chunk separado, lazy.
2. **Testabilidade**: 86 testes verdes (77 unit + 9 E2E) em ~32s
   total, $0.
3. **Acessibilidade out-of-the-box**: Radix primitives + role-based
   semantics; testes E2E usam `getByRole`/`getByLabel`.
4. **Tipagem strict** + `noUncheckedIndexedAccess: true`: erros de
   runtime por undefined caem cedo.
5. **3 temas perceptíveis** sem 3 codebases — variáveis CSS ditam
   diferença visual.
6. **Streaming SSE robusto**: parser stateful + ReadableStream;
   resilient a chunks parciais ou completos.

### Negativas / dívidas técnicas

1. Tipos auto-gerados não consumidos em runtime ainda — duplicação
   manual em `domain.ts`. Migrar quando contrato estabilizar.
2. Smoke E2E rodando stack inteira não existe — apenas mocks.
3. Tailwind 4 upgrade fica para sprint futuro.
4. Plotly chunk size (~840 KB) ainda é pesado no first chart render —
   prefetch via `<link rel="modulepreload">` é otimização possível.
5. `openapi.snapshot.json` precisa ser regenerado manualmente quando
   contrato mudar; pre-commit hook para validação fica para futuro.

## Alternativas consideradas e rejeitadas

### A. Material UI ou Chakra em vez de shadcn/ui

Rejeitado: lock-in de design system pesado (40-100 KB extra), menos
controle sobre estilo, opinião embutida sobre tipografia/espaçamento
que conflita com nossos 3 perfis.

### B. SWR em vez de TanStack Query

Considerado e rejeitado: TanStack Query tem ecosistema mais maduro
(devtools, infinite query, prefetch), tipos melhores, e o catálogo
nem é uma query crítica para latência.

### C. Recharts em vez de Plotly

Rejeitado: `VizSpec.plotly_figure` vem como Plotly figure dict do
Visualizer Agent (Fase 5). Trocar exigiria reescrever o agente; e
Plotly tem suporte interativo (zoom, pan, hover) nativo que Recharts
exige código manual.

### D. WebSocket em vez de SSE

Rejeitado: chat é unidirecional (server → client). WebSocket adiciona
complexidade (heartbeat, reconnect logic) sem benefício. SSE através
de Caddy é trivial; basta `flush_interval -1`.

### E. Endpoint de chat dentro do `api/`

Rejeitado: instalar CrewAI + Anthropic + ChromaDB + sentence-transformers
+ torch no `api/.venv` (~200 MB) o levaria a ~1.9 GB. Separação
física via mini-server no `agents/` mantém footprint do gateway de
dados pequeno. Trade-off: 2 origens em dev (resolvido via Caddy em
prod).

### F. Tipos via Zod runtime validation

Considerado para validar payloads SSE em runtime. Adiado: o gateway
agents-server já valida via Pydantic; runtime check no frontend é
defesa em profundidade nice-to-have, não bloqueante.

## Notas de operação

### Subir stack completa (dev local)

```bash
# Terminal 1: api de dados (Fase 4)
cd api && .venv/Scripts/uvicorn src.main:app --port 8000

# Terminal 2: agents-server (chat streaming)
cd agents && .venv/Scripts/uvicorn src.server.main:app --port 8001 --reload

# Terminal 3: frontend dev
cd frontend && npm run dev
# Abre http://localhost:3000

# Opcional Terminal 4: Caddy reverse proxy (single origin :8443)
caddy run --config infra/caddy/Caddyfile
# Abre http://localhost:8443
```

### Rodar todos os testes

```bash
cd frontend
npm test                           # 77 unit (vitest) ~3s
npm run test:e2e                   # 9 E2E (playwright) ~30s
npm run lint                       # ESLint
npm run build                      # bundle production
```

### Regenerar tipos OpenAPI

```bash
# Com api/ rodando
cd frontend && npm run gen:api-types

# Ou via snapshot offline
cd api && .venv/Scripts/python -c "
import json; from src.main import app
print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))
" > ../frontend/types/openapi.snapshot.json
cd ../frontend && npm run gen:api-types:snapshot
```

## Referências

- [`CLAUDE.md`](../../CLAUDE.md) §"Frontend e integração" — wireframe e
  endpoints alvo.
- [`docs/phases/fase-6-analise.md`](../phases/fase-6-analise.md) — plano
  original.
- [`docs/phases/fase-6-sprint-6.0-progresso.md`](../phases/fase-6-sprint-6.0-progresso.md)
  até [`fase-6-sprint-6.6-progresso.md`](../phases/fase-6-sprint-6.6-progresso.md)
  — narrativa por sprint.
- ADR 0001 (Bootstrap Fase 0) — estrutura de venvs/Docker.
- ADR 0003 (FastAPI + CrewAI) — separação api/agents que motivou
  Caddy.
