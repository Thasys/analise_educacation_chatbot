# Fase 6 — Sprint 6.1 (Endpoint SSE + Parser SSE) — Progresso

> Estado da Sprint 6.1 da Fase 6 (Frontend Next.js 14).
> Complementa [`fase-6-analise.md`](./fase-6-analise.md) e
> [`fase-6-sprint-6.0-progresso.md`](./fase-6-sprint-6.0-progresso.md).
> **Data:** 2026-04-30
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Conectar **agentes ↔ frontend** via streaming Server-Sent Events:

1. Mini FastAPI server no `agents/` (porta `:8001`) com endpoint
   `POST /api/chat/stream` que executa `run_master` em background e
   emite eventos por etapa.
2. `run_master` ganhou parâmetro opcional `on_event: Callable[[dict], None]`
   — callback invocado a cada agent_started/done/final_answer.
3. Parser SSE no frontend (`SseParser` + `parseSseStream`) para consumir
   o stream via `fetch` + `ReadableStream` (`EventSource` não suporta POST).
4. Cliente alto-nível `streamChat(question, callbacks)` que conecta
   tudo e devolve `Promise<FinalAnswer>`.

---

## 2. Entregáveis

### 2.1 Backend (`agents/`)

| Arquivo | Linhas | Descrição |
|---|---|---|
| `agents/src/server/__init__.py` | 18 | Reexport `app` do `main.py` |
| `agents/src/server/main.py` | 60 | FastAPI app + CORS + `/health` + router chat |
| `agents/src/server/schemas.py` | 50 | `ChatStreamRequest`, `ChatStreamEvent` |
| `agents/src/server/chat_stream.py` | 105 | `POST /api/chat/stream` + async generator que drena `asyncio.Queue` populada pelo callback do `run_master` |
| `agents/src/crews/master_flow.py` | +75 | `EventCallback` type + parâmetro `on_event` em `run_master`; emit por etapa (Core, Retriever, Stat, Comp, Citation, Synthesis, final_answer) |
| `agents/tests/server/test_chat_stream.py` | 110 | 5 testes (`/health`, SSE válido, validação 422, error event em falha) |
| `agents/tests/agents/test_master_flow.py` | +85 | 2 testes novos (`on_event` recebe eventos, callback exception não quebra pipeline) |

### 2.2 Frontend (`frontend/`)

| Arquivo | Linhas | Descrição |
|---|---|---|
| `frontend/lib/sse-parser.ts` | 110 | `SseParser` stateful (feed/flush) + `parseSseStream(stream)` async generator |
| `frontend/lib/streaming.ts` | 130 | `streamChat(question, callbacks)` + `getAgentsBaseUrl()` |
| `frontend/tests/unit/sse-parser.test.ts` | 100 | 11 testes (single event, default type, multi-data, comments, chunked input, flush, id, no-data, ReadableStream) |
| `frontend/tests/unit/streaming.test.ts` | 100 | 4 testes (onEvent+onFinal, error event, 4xx, stream sem final_answer) |

### 2.3 Edições

| Arquivo | Mudança |
|---|---|
| `agents/pyproject.toml` | adicionado `fastapi>=0.110` em extras `[agents]` |

**Total Sprint 6.1: ~700 linhas TS/Python (src + tests).**

---

## 3. Decisões aplicadas

### 3.1 ✅ Mini-server no `agents/` (não no `api/`)

**Por quê.** Instalar CrewAI + Anthropic + ChromaDB + sentence-transformers
+ torch no `api/.venv` (~200 MB) o levaria a ~1.9 GB. Separação física:

| Serviço | Porta | Responsabilidade |
|---|---|---|
| `api` (FastAPI) | 8000 | Dados Gold (catalog, timeseries, compare, ranking) |
| `agents-server` (FastAPI) | 8001 | Streaming chat (executa `run_master`) |

Frontend usa duas env vars: `NEXT_PUBLIC_API_BASE_URL` (dados) e
`NEXT_PUBLIC_AGENTS_BASE_URL` (chat). Sprint 6.5 pode adicionar Caddy
proxy reverso para single origin (`/api/data/*` → :8000, `/api/chat/*`
→ :8001).

### 3.2 ✅ `run_master` recebe `on_event` opcional

Mantém backward compat (default `None` = no-op). Cada etapa do
pipeline emite evento estruturado:

```
flow_started      → {question}
agent_started     → {agent: "Core (Orchestrator + Profiler)"}
agent_done        → {agent: "...", result?: {flow, profile, ...}}
agent_started     → {agent: "Retriever"}    (data flow)
agent_done        → {agent: "Retriever", tool_calls: 1}
... (Stat, Comparativist, Citation, Synthesis)
final_answer      → {elapsed_s, payload: <FinalAnswer JSON>}
error             → {error: str}            (em caso de exception)
```

Validado em `test_master_flow_emits_events_via_on_event_callback`.

### 3.3 ✅ Callback exception NÃO quebra o pipeline

`_emit()` envolve a invocação do callback em try/except. Se o
consumidor (ex.: cliente SSE caiu) levantar, o pipeline continua e
loga um warning. Validado em
`test_master_flow_callback_exception_does_not_break_pipeline`.

### 3.4 ✅ `asyncio.Queue` + `loop.call_soon_threadsafe` para bridge thread→loop

`run_master` é síncrono e bloqueante (~30-60s com Anthropic real). No
endpoint `/api/chat/stream`:

1. `asyncio.to_thread(run_master, ...)` roda em executor.
2. Callback `on_event` (chamado da thread) usa
   `loop.call_soon_threadsafe(queue.put_nowait, event)` para enfileirar
   no main loop.
3. Async generator drena a queue e formata SSE.
4. Sentinela `_END_OF_STREAM` sinaliza fim (após `run_master` retornar
   ou falhar).

Padrão clássico para bridge sync→async em FastAPI.

### 3.5 ✅ Erro vira `event: error`, não 500

Se `run_master` levanta, capturamos no `_run_in_executor`, emitimos
`{"type": "error", "error": str(exc)}` para o cliente, e fechamos a
stream limpa. Status HTTP continua 200 (a stream já foi aberta com
sucesso). Validado em `test_chat_stream_emits_error_event_on_failure`.

### 3.6 ✅ Headers SSE para atravessar proxies

```
Content-Type: text/event-stream
Cache-Control: no-cache, no-transform
X-Accel-Buffering: no
Connection: keep-alive
```

`X-Accel-Buffering: no` desabilita buffer do nginx (irrelevante em dev,
crítico para Caddy/produção).

### 3.7 ✅ Parser SSE manual no frontend (não `EventSource`)

`EventSource` API só suporta GET. Nosso endpoint é POST com body JSON
(question pode ser longa). Solução: `fetch` retorna `Response.body`
como `ReadableStream<Uint8Array>`; `parseSseStream` é async generator
que aplica `TextDecoder` + `SseParser` stateful (acumula buffer entre
chunks parciais).

### 3.8 ✅ `SseParser` segue spec W3C

- `event: <type>` (default `message`)
- `data: <text>` (linhas múltiplas concatenadas com `\n`)
- `id: <...>` opcional
- Linhas `:comment` ignoradas
- Bloco termina com `\n\n`
- Espaço após `:` é stripado (`event:  spaced` → `' spaced'`, mantém o segundo)
- `flush()` drena buffer residual (último chunk pode não terminar em `\n\n`)

Cobertura 100% dos paths em 11 testes.

### 3.9 ⚠️ Mapping `agent_done` → `tool_called` (provisório)

`StreamEvent` em `frontend/types/domain.ts` não tem `agent_done`
explícito; mapeamos como `tool_called` reaproveitando `tool` e `args`.
Sprint 6.2 vai refinar quando o componente `<AgentReasoning>` for
implementado e exigir distinção.

---

## 4. Métricas finais

```
Linhas Python adicionadas:     ~395 (server + master_flow callback + tests)
Linhas TS adicionadas:         ~310 (sse-parser + streaming + tests)
Testes pytest TOTAL agents:    126 / 126 PASS (~98s)
  - server (test_chat_stream): 5 testes (~4.5s)
  - master_flow (eventos):     +2 testes
Testes vitest TOTAL frontend:  32 / 32 PASS (~2.3s)
  - sse-parser:                11 testes
  - streaming:                 4 testes

Lint frontend:                 ✅ 0 warnings
Build frontend:                ✅ 108 KB First Load JS (sem regressao)
```

---

## 5. Como rodar

### 5.1 Subir os 2 servidores em terminais separados

```bash
# Terminal 1: api de dados (Fase 4)
cd api
.venv/Scripts/uvicorn src.main:app --port 8000

# Terminal 2: agents-server (Sprint 6.1)
cd agents
.venv/Scripts/uvicorn src.server.main:app --port 8001 --reload
```

### 5.2 Testar SSE com curl

```bash
curl -N -X POST http://localhost:8001/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"Como BR vs FIN em gasto educacional 2020?"}'
```

Saída esperada:

```
event: flow_started
data: {"type":"flow_started","question":"...","ts":...}

event: agent_started
data: {"type":"agent_started","agent":"Core (...)","ts":...}

event: agent_done
data: {"type":"agent_done","agent":"Core (...)","result":{...},"ts":...}

... (Retriever, Stat, Comp, Citation, Synthesis)

event: final_answer
data: {"type":"final_answer","elapsed_s":34.2,"payload":{...}}
```

### 5.3 Frontend dev

```bash
cd frontend
npm run dev
# Abre http://localhost:3000/compare
# (Sprint 6.2 vai conectar a UI ao streamChat — agora ainda eh placeholder)
```

---

## 6. Próximo: Sprint 6.2 (`<Chat>` + `<AgentReasoning>` + streaming UI)

Sprint 6.2 conecta o `streamChat` ao componente Chat real e renderiza
streaming progressivo no browser.

### 6.1 Entregáveis previstos

- `frontend/components/chat/Chat.tsx` — substitui `ChatPlaceholder`
- `frontend/components/chat/MessageBubble.tsx` — bolha user/assistant
- `frontend/components/chat/AgentReasoning.tsx` — collapse com timeline de eventos
- `frontend/components/chat/InputBox.tsx` — textarea + enter+ctrl
- `frontend/components/chat/StreamingMarkdown.tsx` — react-markdown progressivo
- Hook `frontend/lib/hooks/useChat.ts` — orquestra `streamChat` + `chatStore`
- Detecção de perfil → atualiza `profileStore` quando chega
  `agent_done` da Core Crew
- Tests RTL para componentes principais

### 6.2 Critério de avanço

Usuário digita pergunta no `/compare`, vê:
- Loading spinner enquanto Core roda
- Lista de "Core ✓ → Retriever ✓ → Statistician..." progressivo
- Markdown da resposta sendo renderizado conforme chega
- Final state: markdown completo + (placeholder de) viz + sources

---

## 7. Pendências registradas

1. ⏳ `<InlineChart>` Plotly — Sprint 6.3.
2. ⏳ `<CitationPanel>` com DOIs clicáveis — Sprint 6.3.
3. ⏳ Geração automática de tipos via `openapi-typescript` — adiada
   para Sprint 6.5 (depende dos endpoints estáveis em api e agents).
4. ⚠️ `agent_done` mapeado como `tool_called` no `StreamEvent` —
   refinar em Sprint 6.2 quando o `<AgentReasoning>` precisar
   distinguir.
5. ⚠️ `flow_started` mapeado como `agent_started` com `agent="flow"`
   — também provisório.
6. ⚠️ Mini-server agents não tem rate limiting nem auth. Em produção,
   Caddy reverso aplica os limites.
7. ⚠️ Toda a stream fica em memória do servidor até o cliente consumir
   (`asyncio.Queue` sem max size). Em pratica `run_master` produz < 20
   eventos por pergunta, então OK; documentar caso vire problema.

---

*Próximo doc: `fase-6-sprint-6.2-progresso.md` (a criar quando Sprint
6.2 começar).*
