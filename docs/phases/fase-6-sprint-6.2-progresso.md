# Fase 6 — Sprint 6.2 (`<Chat>` real + streaming UI) — Progresso

> Estado da Sprint 6.2 da Fase 6 (Frontend Next.js 14).
> Complementa [`fase-6-analise.md`](./fase-6-analise.md) e
> [`fase-6-sprint-6.1-progresso.md`](./fase-6-sprint-6.1-progresso.md).
> **Data:** 2026-04-30
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Substituir o `ChatPlaceholder` por um componente `<Chat>` real que:

- Consome o stream SSE via hook `useChat` → `streamChat` (Sprint 6.1)
- Renderiza markdown progressivo do `FinalAnswer` via `react-markdown`
- Mostra timeline de agentes em colapsável `<AgentReasoning>`
- Auto-detecta perfil quando chega `agent_done` da Core Crew (atualiza
  `profileStore` se ainda não houve override manual)
- Suporta envio via Ctrl+Enter ou botão
- Trata erros (banner com mensagem do servidor)

---

## 2. Entregáveis

### 2.1 Hook + componentes

| Arquivo | Linhas | Descrição |
|---|---|---|
| `frontend/lib/hooks/useChat.ts` | 80 | hook `useChat()` orquestrando streamChat + chatStore + auto-detecção de perfil; estado loading/error |
| `frontend/components/chat/Chat.tsx` | 105 | container com header (perfil selector), lista de messages, EmptyState com perguntas exemplo, footer com InputBox |
| `frontend/components/chat/MessageBubble.tsx` | 100 | bolha user/assistant com `<AgentReasoning>` + `<StreamingMarkdown>` + footer (sources/warnings/follow-ups) |
| `frontend/components/chat/AgentReasoning.tsx` | 110 | timeline collapsável Radix com status (running/done/error) por agente; deduplica started+done por nome |
| `frontend/components/chat/InputBox.tsx` | 60 | textarea + botão Send; Ctrl+Enter envia, Enter sozinho insere quebra |
| `frontend/components/chat/StreamingMarkdown.tsx` | 38 | wrapper de `ReactMarkdown` + `remark-gfm` com classes Tailwind para tabelas/blockquote/code/links |

### 2.2 Edições

| Arquivo | Mudança |
|---|---|
| `frontend/types/domain.ts` | `StreamEvent` ganhou variants `flow_started` e `agent_done` discriminados (campos opcionais: result, tool_calls, method, sample_size, items, chart_type) |
| `frontend/lib/streaming.ts` | `toStreamEvent` mapeia eventos do servidor para os novos discriminantes (sem mais reuso "criativo" de `tool_called`) |
| `frontend/app/compare/page.tsx` | troca `<ChatPlaceholder>` por `<Chat>` |
| `frontend/components/chat/ChatPlaceholder.tsx` | **removido** (substituído por Chat real) |
| `frontend/package.json` | +3 deps: `react-markdown@^9`, `remark-gfm@^4`, `@radix-ui/react-collapsible@^1.1` |

### 2.3 Testes novos (RTL)

| Arquivo | Linhas | Testes |
|---|---|---|
| `frontend/tests/unit/InputBox.test.tsx` | 65 | 7 (placeholder, Ctrl+Enter, Enter sozinho, disabled, clear after submit, initialValue) |
| `frontend/tests/unit/AgentReasoning.test.tsx` | 60 | 5 (vazio sem loading, timeline buildup, count singular/plural, error icon) |
| `frontend/tests/unit/MessageBubble.test.tsx` | 80 | 4 (user content, assistant final markdown + footer, "Processando…" loading state, error banner) |

**Total Sprint 6.2: ~700 linhas TS/TSX.**

---

## 3. Decisões aplicadas

### 3.1 ✅ `StreamEvent` ganhou `agent_done` discriminado

Sprint 6.1 mapeou `agent_done` como `tool_called` (gambiarra para
caber na união existente). Sprint 6.2 introduziu `agent_done` como
variant próprio com campos opcionais tipados (`result`, `tool_calls`,
`method`, `sample_size`, `items`, `chart_type`). Permite ao
`<AgentReasoning>` distinguir e formatar metadata por etapa.

### 3.2 ✅ Auto-detecção de perfil dentro do `useChat`

```ts
if (event.type === 'agent_done' && event.agent.startsWith('Core')) {
  const detected = event.result?.profile;
  if (isProfileKind(detected)) setProfile(detected); // respeita manualOverride
}
```

`profileStore.setProfile(p, manual=false)` ignora a chamada se o
usuário já clicou manualmente em outro perfil. Resultado: tema visual
adapta automaticamente sem sobrescrever escolha do usuário.

### 3.3 ✅ `AgentReasoning` deduplica started/done por nome

Cada agente aparece UMA vez na timeline (não 2 — `started` e `done`).
O status (`started` → `done` → `error`) evolui e o ícone reflete o
estado atual. Mais limpo visualmente para fluxo data com 6 agentes.

### 3.4 ✅ Markdown via classes Tailwind utility (não @tailwindcss/typography)

Em vez de adicionar `@tailwindcss/typography` (~30 KB plugin + estilo
genérico), usamos classes utility direto no wrapper `<StreamingMarkdown>`
com `[&>h1]:...` etc. Vantagens:
- Bundle menor.
- Estilo sob nosso controle (combina com tema dark + variáveis CSS).
- Sem opinião pre-built sobre tipografia.

### 3.5 ✅ Ctrl+Enter envia, Enter sozinho insere quebra

Padrão usado em Slack/Discord. Mais ergonômico para perguntas longas
multi-linha. `event.ctrlKey || event.metaKey` cobre Mac (Cmd) e
Linux/Windows (Ctrl).

### 3.6 ✅ `<EmptyState>` mostra perguntas exemplo clicáveis

Quando `messages.length === 0`, renderiza Card de boas-vindas + 3
perguntas de exemplo (gasto educacional, alfabetização, ISCED). Click
popula o `<InputBox>` via key prop (re-monta com `initialValue`).

### 3.7 ⚠️ `partial_markdown` event ainda não emitido

O servidor (Sprint 6.1) não emite `partial_markdown` ainda — o
Synthesizer só retorna o markdown completo no `final_answer`. Por isso
o `<StreamingMarkdown>` mostra a resposta de uma vez quando `final`
chega, não progressivamente word-by-word. Sprint futuro pode adicionar
streaming token-by-token no master_flow se o LLM provider expor.

### 3.8 ⚠️ Bundle do `/compare` cresceu para 158 KB First Load JS

`react-markdown` (~30 KB gzip) + `remark-gfm` (~15 KB gzip) +
`@radix-ui/react-collapsible` (~5 KB gzip) somaram ~50 KB ao bundle
inicial. Ainda muito abaixo do alvo 600 KB. Plotly (Sprint 6.3) vai
em chunk separado via dynamic import.

---

## 4. Métricas finais

```
Linhas TS/TSX adicionadas:     ~700 (hook + 5 componentes + 3 test files)
Pacotes npm adicionados:       3 (react-markdown, remark-gfm, radix-collapsible)

Testes vitest TOTAL:           48 / 48 PASS (~2.4s)
  - unit (Sprint 6.0+6.1):     32 testes
  - RTL (Sprint 6.2):          16 testes (7 InputBox + 5 AgentReasoning + 4 MessageBubble)

Lint:                          ✅ 0 warnings ESLint
Build:                         ✅ next build OK
First Load JS /compare:        158 KB (era 108 KB; +50 KB de markdown libs)
                               Alvo: < 600 KB. Margem ~440 KB para Plotly.
```

Saída do `npm test`:

```
✓ tests/unit/api-client.test.ts     (5 tests) 11ms
✓ tests/unit/chatStore.test.ts      (4 tests) 7ms
✓ tests/unit/cn.test.ts             (4 tests) 11ms
✓ tests/unit/profileStore.test.ts   (4 tests) 5ms
✓ tests/unit/sse-parser.test.ts     (11 tests) 18ms
✓ tests/unit/streaming.test.ts      (4 tests) 21ms
✓ tests/unit/InputBox.test.tsx      (7 tests) 72ms
✓ tests/unit/AgentReasoning.test.tsx (5 tests) 76ms
✓ tests/unit/MessageBubble.test.tsx  (4 tests) 80ms

Test Files  9 passed (9)
     Tests  48 passed (48)
  Duration  2.37s
```

---

## 5. Como testar manualmente

### 5.1 Subir backend (3 terminais)

```bash
# Terminal 1: api de dados
cd api && .venv/Scripts/uvicorn src.main:app --port 8000

# Terminal 2: agents-server (chat streaming)
cd agents && .venv/Scripts/uvicorn src.server.main:app --port 8001 --reload

# Terminal 3: frontend dev
cd frontend && npm run dev
```

### 5.2 Abrir `http://localhost:3000/compare`

Sem fazer pergunta:
- Layout 3 colunas (Sidebar 260px / Workspace / ContextPanel 320px)
- EmptyState com 3 perguntas exemplo clicáveis
- Seletor de perfil no header (3 botões)

Ao fazer uma pergunta (precisa de `ANTHROPIC_API_KEY` no `.env` do agents):
- Mensagem do usuário aparece no topo da lista
- Bolha do assistant aparece com `<AgentReasoning>` mostrando "Core (Orchestrator + Profiler) — running"
- Status muda para "done" + metadata (`flow=data, profile=researcher`)
- Sequência continua: Retriever → Stat → Comp → Citation → Synthesis
- Quando chega `final_answer`: markdown renderizado + footer com fontes/warnings/follow-ups
- Tema visual atualiza automaticamente se Orchestrator detectou perfil novo (e não houve override)

---

## 6. Próximo: Sprint 6.3 (`<InlineChart>` Plotly + `<CitationPanel>`)

Sprint 6.3 implementa as duas peças que faltam para a resposta visual
ficar completa:

### 6.1 Entregáveis previstos

- `frontend/components/charts/PlotlyLazy.tsx` — wrapper `next/dynamic` com `ssr: false` para `react-plotly.js`
- `frontend/components/charts/InlineChart.tsx` — recebe `VizSpec`, renderiza Plotly figure
- `frontend/components/citations/CitationPanel.tsx` — lista DOIs com snippets, link externo crossref/doi.org
- `frontend/components/citations/CitationCard.tsx` — bullet por citation
- Integrar viz e citations dentro do `<MessageBubble>` (acima do footer)
- Atualizar `<ContextPanel>` para mostrar lista resumida (já tem stub)
- 3+ testes RTL (InlineChart com viz `none`, CitationPanel com 0 e N items)

### 6.2 Critério de avanço

Pergunta canônica ("BR vs FIN gasto 2020") produz na UI:
- Markdown completo com formatação
- Gráfico bar_vertical interativo Plotly (hover, zoom)
- Painel lateral com 1-3 citações DOI clicáveis (abrem doi.org em nova aba)

---

## 7. Pendências registradas

1. ⏳ Plotly via dynamic import — Sprint 6.3.
2. ⏳ Renderização de citações com DOIs clicáveis — Sprint 6.3.
3. ⏳ Geração tipos via openapi-typescript — Sprint 6.5.
4. ⚠️ `partial_markdown` event não emitido pelo servidor; markdown
    aparece "de uma vez" no fim. Sprint futuro pode pluggar streaming
    token-by-token do Anthropic.
5. ⚠️ `<EmptyState>` re-monta `<InputBox>` via `key={seed}` quando
    usuário clica em pergunta exemplo. Funciona mas é hack — refinar
    com state controlado em Sprint 6.4.
6. ⚠️ Sem teste E2E ainda (Playwright entra em Sprint 6.5).
7. ⚠️ Animation `animate-pulse-subtle` referenciada em `MessageBubble`
    não existe no `tailwind.config.ts`. Adicionar keyframe customizada
    em Sprint 6.4 ou remover.

---

*Próximo doc: `fase-6-sprint-6.3-progresso.md` (a criar quando Sprint
6.3 começar).*
