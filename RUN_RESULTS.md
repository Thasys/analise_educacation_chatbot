# Resultados da execução — Docker Compose com `agents-server` incluído

**Data:** 2026-05-13
**Ambiente:** Windows 11 Home (10.0.26200) + Docker Desktop + WSL2
**Branch do repo:** `main` (clone fresco de `Thasys/analise_educacation_chatbot`)

---

## 1. Mudanças aplicadas

### 1.1 [`agents/Dockerfile`](agents/Dockerfile)

Antes: instalava só `[dev]` e o `CMD` era um `print("agents container OK")` — placeholder.

Depois:

- `pip install -e ".[agents,rag]"` → instala CrewAI, Anthropic SDK, FastAPI, ChromaDB, sentence-transformers.
- `pip install "uvicorn[standard]>=0.30"` → uvicorn explícito (não é mais transitivo confiável).
- `EXPOSE 8001`.
- `CMD ["uvicorn", "src.server.main:app", "--host", "0.0.0.0", "--port", "8001"]`.

Tamanho final da imagem: **9.86 GB** (torch + transformers + chromadb dominam — esperado).

### 1.2 [`docker-compose.yml`](docker-compose.yml)

Novo serviço `agents-server` adicionado entre `prefect` e `frontend`:

```yaml
agents-server:
  build:
    context: ./agents
    dockerfile: Dockerfile
  container_name: edu_agents_server
  restart: unless-stopped
  environment:
    ENVIRONMENT: ${ENVIRONMENT:-development}
    LOG_LEVEL: ${LOG_LEVEL:-INFO}
    ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
    AGENTS_GATEWAY_BASE_URL: http://api:8000        # comunicação interna por DNS do compose
    AGENTS_RAG_PERSIST_DIR: /data/chromadb/edu_literature
    AGENTS_CORS_ORIGINS: ${AGENTS_CORS_ORIGINS:-http://localhost:3000}
    OTEL_SDK_DISABLED: "true"
    CREWAI_DISABLE_TELEMETRY: "true"
  ports:
    - "8001:8001"
  volumes:
    - ./agents/src:/app/src   # hot reload do código fonte
    - ./data:/data            # acesso a ChromaDB/DuckDB
  depends_on:
    - api
```

Frontend também ganhou a env `NEXT_PUBLIC_AGENTS_BASE_URL=http://localhost:8001` e `depends_on: agents-server` para ordem de start.

---

## 2. Build

| Etapa | Tempo |
|---|---|
| Download deps Python (torch, transformers, chromadb, crewai) | ~10 min |
| Compilação de wheels nativos (tokenizers, sentencepiece) | ~3 min |
| Exporting layers + unpacking | 219 s (3.7 min) |
| **Total** | **~17 min** |

Exit code: **0**.

---

## 3. Testes — bateria de smoke nos 6 serviços

Executados com `curl` direto do host Windows após `docker compose up -d agents-server`.

| # | Serviço | URL testada | HTTP | Latência | Resultado |
|---|---|---|---|---|---|
| 1 | Postgres | `pg_isready` interno | — | — | `accepting connections` ✅ |
| 2 | Adminer | http://localhost:8080 | **200** | 50 ms | UI carrega ✅ |
| 3 | Prefect UI | http://localhost:4200 | **200** | 30 ms | dashboard carrega ✅ |
| 4 | Prefect API | http://localhost:4200/api/health | **200** | 35 ms | `true` ✅ |
| 5 | FastAPI docs | http://localhost:8000/docs | **200** | 76 ms | Swagger UI ✅ |
| 5 | FastAPI health | http://localhost:8000/api/health | **200** | 138 ms | JSON ok ✅ |
| 6 | Frontend root | http://localhost:3000 | **307** | 767 ms | redirect para `/compare` ✅ |
| 6 | Frontend /compare | http://localhost:3000/compare | **200** | 261 ms | página chat carrega ✅ |
| 6 | Frontend /explorer | http://localhost:3000/explorer | **200** | 84 ms | ✅ |
| 6 | Frontend /library | http://localhost:3000/library | **200** | 82 ms | ✅ |
| 7 | **Agents /health** | http://localhost:8001/health | **200** | 55 ms | `{"status":"ok","service":"agents-server","version":"0.1.0"}` ✅ |

### 3.1 Bodies confirmados

**FastAPI health (`/api/health`):**
```json
{"status":"ok","service":"edu-api","version":"0.1.0","timestamp":"2026-05-13T14:37:00.888168Z"}
```

**Agents-server health (`/health`):**
```json
{"status":"ok","service":"agents-server","version":"0.1.0"}
```

**FastAPI catalog (`/api/data/catalog`) — 503 esperado:**
```json
{"detail":"DuckDB nao disponivel. Verifique se `dbt build` foi executado e o arquivo data/duckdb/education.duckdb existe."}
```
Comportamento correto — o projeto está na Fase 0 (Bootstrap). O DuckDB só é populado nas Fases 2/3 (`dbt build`).

### 3.2 Rotas expostas pela API FastAPI (`/openapi.json`)

```
/api/data/catalog
/api/data/compare
/api/data/ranking
/api/data/timeseries
/api/health
```

### 3.3 Rotas expostas pelo agents-server (`/openapi.json`)

```
/health
/api/chat/stream
```

### 3.4 Postgres — bancos criados pelo init.sql

```
educacao_metadata  (banco da API)
prefect            (backend do Prefect 3)
postgres           (default)
template0, template1
```

Versão: `PostgreSQL 16.13 on x86_64-pc-linux-musl`.

---

## 4. Teste de integração: streaming SSE do `agents-server`

Requisição:

```bash
curl -X POST http://localhost:8001/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"O que e PISA?"}'
```

Resposta (SSE):

```
event: flow_started
data: {"type": "flow_started", "question": "O que e PISA?", "ts": 1778683035.3348005}

event: agent_started
data: {"type": "agent_started", "agent": "Core (Orchestrator + Profiler)", "ts": 1778683035.334853}

event: error
data: {"type": "error", "error": "Error code: 401 - ... 'message': 'invalid x-api-key' ...", "ts": 0.0}
```

**O que isso confirma:**

1. ✅ O endpoint POST aceita JSON e abre `text/event-stream`.
2. ✅ O **master flow CrewAI** está sendo invocado (`flow_started`).
3. ✅ A **Core Crew** (Orchestrator + Profiler) inicializa (`agent_started`).
4. ✅ A integração com a Anthropic SDK está carregada e fez a chamada HTTP.
5. ✅ O **tratamento de erros** funciona — o 401 (chave vazia no `.env`) foi capturado e emitido como `event: error` em vez de derrubar a conexão.
6. ❌ O fluxo completo só roda com `ANTHROPIC_API_KEY` real no `.env` (obtida em https://console.anthropic.com/settings/keys).

---

## 5. Status final dos containers

```
NAMES               STATUS                 PORTS
edu_agents_server   Up 8 minutes           0.0.0.0:8001->8001/tcp
edu_frontend        Up 3 hours             0.0.0.0:3000->3000/tcp
edu_adminer         Up 3 hours             0.0.0.0:8080->8080/tcp
edu_prefect         Up 3 hours             0.0.0.0:4200->4200/tcp
edu_api             Up 3 hours             0.0.0.0:8000->8000/tcp
edu_postgres        Up 3 hours (healthy)   0.0.0.0:5432->5432/tcp
```

Logs de startup do agents-server:

```
agents.server.ready  cors_origins=['http://localhost:3000']  version=0.1.0
INFO:     Started server process [1]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

---

## 6. O que ficou funcionando e o que ainda falta

### Funcionando (Fase 0 + Fase 5 stack carregado)

- Toda a infraestrutura Docker (6 serviços, healthchecks OK).
- API gateway com `/api/health` e endpoints REST disponíveis (mesmo que retornem 503 sem DuckDB).
- Frontend Next.js servindo as 3 páginas (`/compare`, `/explorer`, `/library`).
- Agents-server carregando todo o stack pesado (CrewAI + ChromaDB + sentence-transformers + Anthropic SDK) e expondo streaming SSE.
- Comunicação interna `agents-server → api` por DNS (`http://api:8000`).
- CORS configurado para `http://localhost:3000`.

### Ainda pendente (fora do escopo da Fase 0)

| Item | Como destravar |
|---|---|
| Chave Anthropic | Preencher `ANTHROPIC_API_KEY=` no `.env` e `docker compose restart agents-server` |
| `/api/data/*` retornando dados | Rodar Fases 1–3 (coletores Prefect + `dbt build` no DuckDB) |
| RAG ChromaDB com literatura | Popular `data/chromadb/edu_literature/` (script `agents/src/rag/ingest.py`) |
| Healthchecks no compose para os serviços novos | `agents-server`, `api`, `frontend` não têm `healthcheck:` — adicionar `curl --fail http://localhost:PORT/health` melhora o `depends_on: condition: service_healthy` |

---

## 7. Comandos úteis

```powershell
# subir tudo
cd C:\Users\thars\analise_educacation_chatbot
docker compose up -d

# rebuild só do agents-server depois de alterar Dockerfile ou pyproject.toml
docker compose build agents-server
docker compose up -d agents-server

# logs em tempo real
docker compose logs -f agents-server

# derrubar (preservando volumes)
docker compose down

# derrubar e apagar tudo (incluindo o banco)
docker compose down -v
```
