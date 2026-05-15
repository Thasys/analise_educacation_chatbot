# Rodando o sistema

## Pré-requisitos

- Docker Engine **24+** + Compose v2
- Ollama no host com modelos baixados (`qwen2.5:32b`, `qwen2.5:14b`) —
  ver [`models-and-providers.md`](models-and-providers.md)
- `.env` configurado a partir de `.env.example`

## Sobe stack

```bash
docker compose up -d
```

Sobe 6 serviços. Tempo: ~30s para os leves, +20-40s para `agents-server`
(import de CrewAI + torch + chromadb).

| Container | Porta | Healthcheck |
|---|---|---|
| `edu_postgres` | 5432 | `pg_isready` |
| `edu_adminer` | 8080 | — |
| `edu_prefect` | 4200 | UI carrega |
| `edu_api` | 8000 | `GET /api/health` |
| `edu_agents_server` | 8001 | `GET /health` (start_period 45s) |
| `edu_frontend` | 3000 | depends_on healthy |

Verificar:

```bash
docker compose ps
docker inspect -f '{{.State.Health.Status}}' edu_api edu_agents_server
```

## Smoke tests

```bash
# Layer API
curl http://localhost:8000/api/health
curl http://localhost:8000/api/data/catalog | jq '.data[].name'

# Layer agents
curl http://localhost:8001/health

# Dados Gold reais
curl -X POST http://localhost:8000/api/data/compare \
  -H "Content-Type: application/json" \
  -d '{"indicator":"GASTO_EDU_PIB","countries":["BRA","FIN","MEX"],"year":2020,"source":"worldbank"}'
```

## Fazer uma pergunta end-to-end

### Via terminal (SSE)

```bash
curl -N -X POST http://localhost:8001/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"Compare o gasto educacional do Brasil com a Finlândia em 2020."}'
```

A stream emite ~14 eventos SSE:
1. `flow_started`
2. `agent_started/done` × 6 (Core, Retriever, Statistician, Comparativist, Citation, Synthesis)
3. `agent_started/done` × 1 (Fact Checker — pode disparar `Synthesizer (retry)`)
4. `final_answer` com payload completo (markdown, viz, citations)

Tempo total: **~7 min com mistral-nemo:12b** ou **~20 min com qwen2.5:32b**
em CPU offload (32 GB RAM, sem GPU dedicada).

### Via browser

Abra <http://localhost:3000/compare>, digite a pergunta no input,
acompanhe Reasoning Timeline (collapsável) e veja:
- Markdown adaptado ao perfil (auto-detectado)
- Gráfico Plotly inline com Brasil destacado
- Painel direito: fontes, citações, fluxo executado

## Aplicar mudanças de código

Os 4 serviços de código (`api`, `agents-server`, `frontend`, `data_pipeline`)
têm **bind mount** em `src/` ou `app/`. Mudanças em arquivos `.py`/`.tsx`
ficam visíveis no container imediatamente.

```bash
# Python (FastAPI/CrewAI não fazem hot-reload por padrão):
docker compose restart api agents-server

# Frontend (Next dev tem HMR automático):
# nada precisa fazer

# Mudanças em .env exigem recriar containers (não relê em restart):
docker compose up -d --force-recreate agents-server
```

## Derrubar

```bash
docker compose down              # mantém volumes (Postgres, Prefect)
docker compose down -v           # apaga volumes também (perde Postgres data)
```

## Troubleshooting comum

**Frontend tela branca:** veja `docker compose logs frontend` — geralmente
`agents-server` ainda subindo. Aguarde `start_period: 45s`.

**Agents-server retorna 503:** `qwen2.5:32b` provavelmente não baixado no
Ollama do host. Rode `ollama pull qwen2.5:32b` (+20 GB).

**`mart_*` retorna 404:** Gold ainda não populado. Veja
[`data-pipeline.md`](data-pipeline.md).

**Resposta diz "dados ausentes" mesmo com Gold OK:** Retriever falhou em
copiar rows do tool output. Logs do container devem mostrar
`agents.retriever.autopopulated` — se ausente, é bug no auto-populate.
Veja [`monitoring-and-debugging.md`](monitoring-and-debugging.md).
