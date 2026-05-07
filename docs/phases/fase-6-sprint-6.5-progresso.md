# Fase 6 — Sprint 6.5 (Playwright E2E + Caddy + openapi-typescript) — Progresso

> Estado da Sprint 6.5 da Fase 6 (Frontend Next.js 14).
> Complementa [`fase-6-analise.md`](./fase-6-analise.md) e
> [`fase-6-sprint-6.4-progresso.md`](./fase-6-sprint-6.4-progresso.md).
> **Data:** 2026-05-06
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Fechar a engenharia da Fase 6 com 3 frentes:

- **Playwright E2E** com 9 testes cobrindo navegação, layout, perfis,
  filtros do explorer, fluxo de chat com mock SSE.
- **Caddy reverse proxy** configurado para single origin (`/api/chat/*`
  → :8001, `/api/data/*` → :8000, `/*` → :3000).
- **`openapi-typescript`** rodando contra snapshot do gateway →
  `frontend/types/api.ts` versionado.

---

## 2. Entregáveis

### 2.1 Playwright + testes E2E

| Arquivo | Linhas | Descrição |
|---|---|---|
| `frontend/playwright.config.ts` | 30 | Config: chromium, headless, baseURL :3000, `webServer: npm run dev` reusable, retain-on-failure trace + screenshot |
| `frontend/tests/e2e/fixtures.ts` | 145 | Fixtures customizadas com helpers `mockCatalog`, `mockChatStream`, `mockCatalogError` via `page.route(...)` + payloads compartilhados (`SAMPLE_CATALOG`, `SAMPLE_FINAL_ANSWER`, `CHAT_SSE_DATA_FLOW`) |
| `frontend/tests/e2e/compare-layout.spec.ts` | 50 | 4 testes (redirect / → /compare, layout 3 colunas, troca de perfil aplica `data-profile`, click pergunta exemplo popula input) |
| `frontend/tests/e2e/explorer.spec.ts` | 60 | 3 testes (catálogo + detalhe, filtro por texto, error state com retry) |
| `frontend/tests/e2e/chat-flow.spec.ts` | 70 | 2 testes (fluxo completo com mock SSE: timeline + markdown + DOI link; override manual de perfil sobrevive ao auto-detect) |

### 2.2 Tipos OpenAPI

| Arquivo | Linhas | Descrição |
|---|---|---|
| `frontend/types/openapi.snapshot.json` | ~600 | Snapshot OpenAPI exportado de `api.openapi()` (5 paths, 8 schemas) |
| `frontend/types/api.ts` | ~330 | Gerado por `openapi-typescript` — `paths` + `components.schemas` totalmente tipados |

### 2.3 Caddy

| Arquivo | Mudança |
|---|---|
| `infra/caddy/Caddyfile` | reescrito do scaffold para Caddyfile funcional: `:8443` em dev com 3 routes (chat SSE com `flush_interval -1`, /api/data/*, /* frontend), bloco produção comentado com TLS auto, `:80` heartbeat |

### 2.4 Edições

| Arquivo | Mudança |
|---|---|
| `frontend/package.json` | +`@playwright/test@^1.46`; +scripts `test:e2e`, `test:e2e:ui`, `gen:api-types:snapshot` |

**Total Sprint 6.5: ~700 linhas TS + 1100 linhas snapshot/tipos + Caddyfile.**

---

## 3. Decisões aplicadas

### 3.1 ✅ Playwright com `page.route` em vez de subir api/agents reais

Sprint 6.5 isola UI da lógica backend: `mocks.mockCatalog(SAMPLE_CATALOG)`
e `mocks.mockChatStream(CHAT_SSE_DATA_FLOW)` interceptam fetch via
`page.route(url, handler)`. Vantagens:

- Roda em ~30s (vs 2-5min subindo CrewAI + Anthropic).
- Determinístico (LLM não-determinístico fica para suite live no agents).
- Não depende de DuckDB ou ChromaDB.

Sprint 6.6 pode adicionar smoke E2E que sobe a stack inteira via Caddy.

### 3.2 ✅ `webServer.reuseExistingServer` em dev local

```ts
webServer: {
  command: 'npm run dev',
  url: 'http://localhost:3000',
  reuseExistingServer: !process.env.CI,
  timeout: 120_000,
}
```

Em dev, Playwright reusa um `npm run dev` já rodando. Em CI, sobe um
novo a cada execução. Acelera local dev (Next compila ~10-15s primeira
vez).

### 3.3 ✅ Mock de SSE via `route.fulfill` envia body inteiro de uma vez

`page.route` não streama por padrão; `fulfill({ body: sseText })` entrega
o stream completo numa response. Nosso `parseSseStream` consome via
`response.body.getReader()` que processa todos os blocos `\n\n` e
emite eventos sequencialmente. Funciona porque nosso parser é resilient
a chunks grandes ou pequenos. Validado em 2 testes.

### 3.4 ✅ Strict-mode locators forçam usar role-based em vez de getByLabel

Descoberto: `getByLabel('Pergunta')` resolve **2** elementos em strict
mode — o `<textarea aria-label="Pergunta">` E o `<button aria-label="Enviar pergunta">`
(match parcial). Solução: `getByRole('textbox', { name: 'Pergunta' })`
para ser específico.

Mesma classe de ajuste para conteúdos que aparecem em mais de um
container (citação no `<CitationCard>` + no `<ContextPanel>` lateral) —
usar `.first()`.

### 3.5 ✅ Caddyfile com `flush_interval -1` para SSE

Sem essa flag, Caddy bufferiza response — quebra streaming. Também
configurado `response_header_timeout 0` para não cortar requests
longos (fluxos `data` podem levar 60s).

Bloco de produção (com hostname público) comentado e mantido como
template — Let's Encrypt automático ao descomentar.

### 3.6 ✅ Snapshot OpenAPI versionado em `frontend/types/`

`gen:api-types` original requer api/ rodando. Adicionamos snapshot
estático (`openapi.snapshot.json`) gerado uma vez via
`api.openapi()` + script `gen:api-types:snapshot` que pode rodar
offline. Útil para:

- CI sem subir backend
- Desenvolvimento de frontend isolado
- Detecção de drift quando contrato mudar (snapshot fica em PR diff)

Sprint futura pode adicionar pre-commit hook que falha se snapshot
desatualizado.

### 3.7 ⚠️ Tipos gerados ainda não são consumidos pelo frontend

`types/api.ts` foi gerado mas não é usado em runtime — `lib/api-client.ts`
e `lib/streaming.ts` continuam usando tipos manuais de `types/domain.ts`.
Migração para tipos auto-gerados fica para Sprint 6.6 ou futuro,
sem urgência: schemas manuais bateram 100% com OpenAPI até agora.

---

## 4. Métricas finais

```
Linhas TS adicionadas:         ~700 (Playwright config + 3 spec files + fixtures)
Linhas auto-geradas:           ~330 (types/api.ts) + ~600 (openapi.snapshot.json)
Pacotes npm adicionados:       1 (@playwright/test)
Browsers Playwright:           Chromium baixado para %LocalAppData%\ms-playwright\

Testes vitest TOTAL:           77 / 77 PASS (~2.7s) — sem regressao
Testes Playwright TOTAL:       9 / 9 PASS (~29s)
  - compare-layout:            4 testes
  - explorer:                  3 testes
  - chat-flow:                 2 testes

Lint:                          ✅ 0 warnings ESLint
Build:                         ✅ next build OK (sem regressao)
First Load JS:                 158 KB /compare (idem Sprint 6.4)
```

Saída do `npx playwright test`:

```
Running 9 tests using 1 worker

  ok 1 chat-flow › fluxo completo com SSE
  ok 2 chat-flow › auto-detecção de perfil
  ok 3 compare-layout › redirect /
  ok 4 compare-layout › 3 colunas + header
  ok 5 compare-layout › data-profile applies
  ok 6 compare-layout › sample question fills input
  ok 7 explorer › catálogo + detalhe
  ok 8 explorer › filtro por texto
  ok 9 explorer › error state com retry

  9 passed (28.9s)
```

---

## 5. Como rodar

### 5.1 Suite E2E

```bash
cd frontend
npx playwright install chromium  # so primeira vez
npm run test:e2e                 # 9 testes em ~30s
npm run test:e2e:ui              # interface interativa Playwright UI
```

### 5.2 Regenerar tipos OpenAPI

Quando o contrato do api/ mudar:

```bash
# Opção A: api/ rodando
cd frontend && npm run gen:api-types

# Opção B: offline via snapshot
cd api && .venv/Scripts/python -c "
import json; from src.main import app
print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))
" > ../frontend/types/openapi.snapshot.json
cd ../frontend && npm run gen:api-types:snapshot
```

### 5.3 Caddy reverse proxy

```bash
caddy run --config infra/caddy/Caddyfile
# Acessa http://localhost:8443/compare
```

---

## 6. Próximo: Sprint 6.6 (Conclusão + ADR 0004)

Última sprint da Fase 6. Não adiciona código novo — finaliza
documentação e fecha a fase.

### 6.1 Entregáveis previstos

- `docs/adrs/0004-arquitetura-frontend-nextjs.md` — ADR com decisões
  desta fase (Tailwind 3.4, shadcn cópia, Zustand sem Provider, SSE
  manual, Plotly basic-dist-min lazy, ChartErrorBoundary local, mocks
  Playwright via page.route)
- `docs/phases/fase-6-conclusao.md` — fechamento da Fase 6: 7 sprints,
  ~5500 linhas TS/TSX, 86 testes (77 unit + 9 E2E), bundles, próximos
  passos
- Atualização do `CLAUDE.md` com changelog Fase 6

### 6.2 Critério de avanço

Documentação completa permitindo que outro dev rode `npm install +
test + test:e2e + build` em uma máquina nova sem perguntar nada.

---

## 7. Pendências registradas

1. ⏳ ADR 0004 + `fase-6-conclusao.md` — Sprint 6.6.
2. ⏳ Tipos auto-gerados não consumidos pelo frontend — migrar
   `types/domain.ts` para reexports de `types/api.ts` em sprint
   futura quando contrato estabilizar.
3. ⚠️ Smoke E2E rodando stack inteira (api + agents + frontend +
   Caddy) ainda não existe — Sprint 6.6 ou futuro.
4. ⚠️ Endpoint `/api/chat/stream` ainda não está no `api/` — está no
   `agents/src/server/`. Caddy roteia `/api/chat/*` para :8001 em
   prod. Tipos gerados pelo `gen:api-types` cobrem só os 4 endpoints
   do `api/` (não o do agents). Documentar em ADR 0004.
5. ⚠️ Playwright Chromium baixado em `%LocalAppData%\ms-playwright\`
   (~150 MB). Adicionar ao `.gitignore` se a pasta vazar para o repo.

---

*Próximo doc: `fase-6-conclusao.md` (Sprint 6.6).*
