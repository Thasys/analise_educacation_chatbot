# Fase 6 — Sprint 6.3 (`<InlineChart>` Plotly + `<CitationPanel>`) — Progresso

> Estado da Sprint 6.3 da Fase 6 (Frontend Next.js 14).
> Complementa [`fase-6-analise.md`](./fase-6-analise.md) e
> [`fase-6-sprint-6.2-progresso.md`](./fase-6-sprint-6.2-progresso.md).
> **Data:** 2026-05-05
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Fechar a resposta visual completa adicionando os dois componentes que
faltavam no `<MessageBubble>`:

- **`<InlineChart>`** — renderiza `VizSpec.plotly_figure` via Plotly
  (bar/line/scatter), com Plotly carregado lazy (chunk separado).
- **`<CitationPanel>` + `<CitationCard>`** — lista DOIs validados pelo
  Citation Agent com link clicável para `doi.org`.
- Atualização do `<ContextPanel>` lateral para também listar citações
  resumidas.

---

## 2. Entregáveis

### 2.1 Componentes novos

| Arquivo | Linhas | Descrição |
|---|---|---|
| `frontend/components/charts/PlotlyLazy.tsx` | 105 | Wrapper que carrega `plotly.js-basic-dist-min` + `react-plotly.js/factory` via dynamic import; cache singleton; estados loading/error/ready |
| `frontend/components/charts/InlineChart.tsx` | 50 | Recebe `VizSpec`, renderiza com título + sources + notas; trata `chart_type='none'` (retorna null) e dados vazios |
| `frontend/components/citations/CitationCard.tsx` | 80 | Card individual com título, autores formatados, journal, link doi.org externo, snippet em blockquote, source + relevância |
| `frontend/components/citations/CitationPanel.tsx` | 30 | Lista de `<CitationCard>` com header e contador |

### 2.2 Edições

| Arquivo | Mudança |
|---|---|
| `frontend/components/chat/MessageBubble.tsx` | +2 blocos: `<InlineChart>` por viz + `<CitationPanel>` quando há citations no FinalAnswer |
| `frontend/components/layout/ContextPanel.tsx` | seção "Citações" expande de stub para lista compacta com links doi.org |
| `frontend/package.json` | +3 deps: `plotly.js-basic-dist-min@^2.34`, `react-plotly.js@^2.6`, `@types/react-plotly.js@^2.6.3` |

### 2.3 Tests novos (RTL)

| Arquivo | Linhas | Testes |
|---|---|---|
| `frontend/tests/unit/InlineChart.test.tsx` | 65 | 4 (title/sources/notes, lazy plotly mounted, chart_type=none retorna null, empty data placeholder) — usa `vi.mock` para isolar Plotly |
| `frontend/tests/unit/CitationPanel.test.tsx` | 110 | 11 (4 panel + 7 card: empty state, count, custom title, doi link target/rel, omit link sem DOI, formatação de 1/2/3+ autores, snippet, source + relevância) |

**Total Sprint 6.3: ~440 linhas TS/TSX (src + tests).**

---

## 3. Decisões aplicadas

### 3.1 ✅ `plotly.js-basic-dist-min` (840 KB) em vez de `plotly.js` full (3 MB)

`basic-dist-min` inclui apenas bar / line / scatter / pie — exatamente
os chart types que o Visualizer Agent (Fase 5) produz hoje. Economia
~70% no chunk Plotly.

### 3.2 ✅ Wrapper `PlotlyLazy` com factory + dynamic import singleton

```ts
async function loadPlotComponent() {
  if (cachedComponent) return cachedComponent;
  if (loadPromise) return loadPromise;
  loadPromise = (async () => {
    const Plotly = (await import('plotly.js-basic-dist-min')).default;
    const createPlotComponent = (await import('react-plotly.js/factory')).default;
    cachedComponent = createPlotComponent(Plotly);
    return cachedComponent;
  })();
  return loadPromise;
}
```

Vantagens:
- Plotly só baixa quando a primeira viz aparece na UI.
- Bundle inicial do `/compare` cresce ~1 KB (só o wrapper).
- Múltiplas vizes na mesma sessão reusam o mesmo componente cacheado.
- `useEffect` + `mountedRef` previne `setState` em componente
  desmontado.

### 3.3 ✅ Defaults de tema dark no Plotly layout

`PlotlyLazy` aplica defaults sobreponíveis pelo `figure.layout`:
```ts
{
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { color: '#cbd5e1', size: 12 },
}
```

Espelha a paleta do `globals.css`. Backend pode sobrescrever (ex.:
título com cor específica) sem perder consistência visual.

### 3.4 ✅ `displaylogo: false` + remoção de tools agressivos

```ts
{
  responsive: true,
  displaylogo: false,
  modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d'],
}
```

Sem logo Plotly (visual mais limpo); seleção e auto-scale removidos
porque os charts são pequenos e não fazem sentido nesse contexto.
Mantém zoom + pan + download como PNG.

### 3.5 ✅ `<CitationCard>` com link externo target=_blank + rel=noopener

DOI clicável abre `https://doi.org/<doi>` em nova aba com
`rel="noopener noreferrer"` (padrão de segurança contra reverse
tabnabbing). Validado em teste RTL dedicado.

### 3.6 ✅ Formatação de autores: 1 nome / 2 com `&` / 3+ com `et al.`

Regra acadêmica padrão (APA-like sem ano):
- 1 autor: "Hanushek, E."
- 2 autores: "Hanushek, E. & Woessmann, L."
- 3+ autores: "Hanushek, E. et al."

Validado em 3 testes específicos.

### 3.7 ✅ Mock de `PlotlyLazy` em tests RTL

```ts
vi.mock('@/components/charts/PlotlyLazy', () => ({
  PlotlyLazy: ({ figure }) => (
    <div data-testid="plotly-mock" data-points={figure.data.length} />
  ),
}));
```

Evita download de Plotly em happy-dom (que não suporta WebGL nem
muitas APIs do browser). Os 4 testes do `<InlineChart>` validam
estrutura, props passados, não a renderização real do gráfico —
suficiente para Sprint 6.3 (validação visual fica para E2E em 6.5).

### 3.8 ✅ ContextPanel mostra citações resumidas com link doi.org

Sprint 6.2 deixava só count placeholder. Agora cada citação no
ContextPanel lateral aparece como entrada compacta:
- Título (1-2 linhas)
- "Autor et al. (ano)"
- Link `doi.org/<doi>` em mono-fonte 10px

Complementa o `<CitationPanel>` completo dentro da bolha de mensagem.

### 3.9 ⚠️ Plotly chunk só cresce o `/compare` em ~1 KB no inicial

```
Route             First Load JS
/compare          159 KB    (era 158 KB; +~1 KB do wrapper Lazy)
```

Plotly real (~840 KB minified) entra como chunk separado, baixado on
demand quando o usuário recebe primeira resposta com viz. Em tela
estática (zero perguntas), Plotly nunca é carregado.

---

## 4. Métricas finais

```
Linhas TS/TSX adicionadas:     ~440 (src + tests Sprint 6.3)
Pacotes npm adicionados:       3 (plotly.js-basic-dist-min, react-plotly.js, @types/react-plotly.js)

Testes vitest TOTAL:           63 / 63 PASS (~5.7s)
  - novos Sprint 6.3:          15 testes (4 InlineChart + 11 CitationPanel/Card)

Lint:                          ✅ 0 warnings ESLint
Build:                         ✅ next build OK
First Load JS /compare:        159 KB (era 158 KB; alvo < 600 KB)
                               Plotly em chunk separado (~840 KB lazy)
```

Saída do `npm test`:

```
✓ tests/unit/api-client.test.ts        (5 tests) 11ms
✓ tests/unit/profileStore.test.ts      (4 tests) 5ms
✓ tests/unit/chatStore.test.ts         (4 tests) 8ms
✓ tests/unit/cn.test.ts                (4 tests) 11ms
✓ tests/unit/streaming.test.ts         (4 tests) 21ms
✓ tests/unit/sse-parser.test.ts        (11 tests) 18ms
✓ tests/unit/InputBox.test.tsx         (7 tests) 77ms
✓ tests/unit/AgentReasoning.test.tsx   (5 tests) 82ms
✓ tests/unit/MessageBubble.test.tsx    (4 tests) 82ms
✓ tests/unit/InlineChart.test.tsx      (4 tests) 36ms
✓ tests/unit/CitationPanel.test.tsx    (11 tests) 83ms

Test Files  11 passed (11)
     Tests  63 passed (63)
```

---

## 5. Estrutura do `frontend/` após Sprint 6.3

```
frontend/
├── components/
│   ├── ui/ (button, card)
│   ├── layout/ (Sidebar, Workspace, ContextPanel*, ProfileTheme, QueryProvider)
│   ├── chat/ (Chat, MessageBubble*, AgentReasoning, InputBox, StreamingMarkdown)
│   ├── charts/
│   │   ├── PlotlyLazy.tsx     ✅ NOVO
│   │   └── InlineChart.tsx    ✅ NOVO
│   └── citations/
│       ├── CitationPanel.tsx  ✅ NOVO
│       └── CitationCard.tsx   ✅ NOVO
└── tests/unit/
    ├── ... (existing)
    ├── InlineChart.test.tsx   ✅ NOVO
    └── CitationPanel.test.tsx ✅ NOVO
```

`*` = arquivo editado nesta sprint.

---

## 6. Próximo: Sprint 6.4 (`<DataExplorer>` + adaptação tema por perfil)

Sprint 6.4 implementa as duas peças que faltam para o workspace ficar
completo:

### 6.1 Entregáveis previstos

- `frontend/components/explorer/DataExplorer.tsx` — navegação dos 5
  marts Gold com lista + preview (consome `/api/data/catalog` e
  `/api/data/:dataset/preview`)
- `frontend/components/explorer/MartCard.tsx` — card por mart
- `frontend/lib/hooks/useCatalog.ts` — TanStack Query do catálogo
- Atualizar `app/explorer/page.tsx` (atualmente placeholder) para
  usar `<DataExplorer>`
- Refinar adaptação por perfil: garantir que researcher/policy/student
  geram mudanças visuais perceptíveis (fonte, cor primária,
  arredondamentos)
- Testes RTL ~5 (catalog list, mart card, profile theme switch)

### 6.2 Critério de avanço

Usuário navega `/explorer`, vê 5 marts com descrições, clica em um e
visualiza preview de 100 linhas. Volta para `/compare`, faz pergunta
que detecta perfil "policy" → tema visual adapta (radius diferente,
primary mais azul).

---

## 7. Pendências registradas

1. ⏳ `<DataExplorer>` + página `/explorer` real — Sprint 6.4.
2. ⏳ Geração tipos via openapi-typescript — Sprint 6.5.
3. ⏳ Testes E2E Playwright — Sprint 6.5.
4. ⏳ ADR 0004 (frontend arch) — Sprint 6.6.
5. ⚠️ Plotly em chunk separado mas precisa rodar `npm run build` para
   confirmar nome do chunk e tamanho real do JS de Plotly em produção
   (next build report mostra apenas chunks shared).
6. ⚠️ `<InlineChart>` não tem fallback para erros de render do Plotly
   (ex.: layout dict inválido). Sprint 6.4 pode adicionar
   `<ErrorBoundary>` ao redor.
7. ⚠️ `<CitationPanel>` deduplica nada — se o backend retornar 2x o
   mesmo DOI, ambos aparecem. Adicionar dedup no Citation Agent ou aqui
   se virar problema.

---

*Próximo doc: `fase-6-sprint-6.4-progresso.md` (a criar quando Sprint
6.4 começar).*
