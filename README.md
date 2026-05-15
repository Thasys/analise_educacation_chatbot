# Análise Educacional Comparada — Brasil × Internacional

> Sistema acadêmico que responde:
> **"Como a educação básica brasileira se compara à educação dos países desenvolvidos?"**

Data Lakehouse educacional + sistema multi-agente conversacional + interface web. Stack 100% open source, roda on-premise.

- **Fonte de verdade arquitetural:** [`docs/architecture/overview.md`](docs/architecture/overview.md)
- **Convenções e princípios:** [`docs/conventions.md`](docs/conventions.md), [`docs/methodology.md`](docs/methodology.md)
- **Como operar o sistema no dia a dia:** [`docs/operations/`](docs/operations/)
- **Decisões arquiteturais:** [`docs/adrs/`](docs/adrs/)
- **Histórico de mudanças:** [`CHANGELOG.md`](CHANGELOG.md)

---

## Estado atual (2026-05-16)

| Camada | Status | Detalhes |
|---|---|---|
| Bronze (raw) | ✅ | 7 fontes coletadas (WB, UNESCO, OECD, IPEA, CEPAL, IBGE, Eurostat) |
| Silver (limpo) | ✅ | 5 tabelas intermediate em DuckDB (~5,3k linhas) |
| Gold (analítico) | ✅ | 5 marts dbt (1.182 linhas) — `mart_br_vs_ocde__*`, `mart_alfabetizacao__*`, etc. |
| API (FastAPI) | ✅ | `/api/data/{catalog,timeseries,compare,ranking}` — porta 8000 |
| Agentes (CrewAI) | ✅ | 8 agentes em 4 crews + Fact Checker — porta 8001 |
| RAG (ChromaDB) | ✅ | 25 papers seed indexados |
| Frontend (Next.js 14) | ✅ | Workspace 3 colunas, SSE streaming — porta 3000 |
| **LLM provider** | Ollama local | `qwen2.5:32b` (smart) + `qwen2.5:14b` (fast) — ver [ADR 0005](docs/adrs/0005-ollama-qwen-provider.md) |

---

## Quick start

### Pré-requisitos

- Docker Engine **24+** e Docker Compose **v2**
- 32 GB RAM (para rodar qwen2.5:32b localmente)
- 8 GB VRAM opcional (acelera modelos via GPU)
- **Ollama** instalado no host: <https://ollama.com/download>
- Git, Python 3.11+ e Node 20+ apenas para desenvolvimento fora do container

### 1. Configurar e baixar modelos LLM

```bash
git clone <url-do-repo> analise_educacation_chatbot
cd analise_educacation_chatbot
cp .env.example .env

# Baixar modelos via Ollama (uma vez):
ollama pull qwen2.5:32b   # ~20 GB
ollama pull qwen2.5:14b   # ~9 GB
```

### 2. Subir o stack

```bash
docker compose up -d
```

Validar serviços (~30s para subir):

| Serviço | URL | Esperado |
|---|---|---|
| Frontend | <http://localhost:3000> | Workspace EduCompara |
| API docs | <http://localhost:8000/docs> | Swagger com `/api/data/*` |
| API health | <http://localhost:8000/api/health> | `{"status":"ok"}` |
| Agents health | <http://localhost:8001/health> | `{"status":"ok"}` |
| Prefect UI | <http://localhost:4200> | Dashboard Prefect |
| Adminer | <http://localhost:8080> | UI Postgres |

### 3. Popular o sistema (uma vez)

```bash
# Bronze + Silver + Gold (data_pipeline + dbt — alguns minutos)
docker compose --profile tools run --rm data_pipeline dbt build \
  --profiles-dir /dbt --project-dir /dbt

# RAG ChromaDB com 25 papers seed
docker compose run --rm agents-server python -c "
from src.rag.ingest import ingest_manifest
print(ingest_manifest('/app/src/rag/seeds/manifest.yaml'))
"
```

### 4. Fazer uma pergunta

```bash
curl -N -X POST http://localhost:8001/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"Compare gasto educacional Brasil, Finlândia e México em 2020."}'
```

Ou abra <http://localhost:3000/compare> e use o chat.

---

## Estrutura do projeto

```text
.
├── CLAUDE.md              # Entry point — links para docs detalhadas
├── CHANGELOG.md           # Histórico de mudanças
├── docker-compose.yml     # Orquestração dos 6 serviços
├── .env.example           # Template de variáveis (LLM provider, DB, etc.)
│
├── api/                   # FastAPI gateway (Camada 5) — :8000
├── agents/                # CrewAI multi-agente (Camada 4) — :8001
├── data_pipeline/         # Coletores Prefect + dbt (Camadas 1-3)
├── dbt_project/           # Transformações SQL — Silver + Gold
├── frontend/              # Next.js 14 + Tailwind + shadcn (Camada 6) — :3000
├── r_scripts/             # Scripts R (PISA/TIMSS/PIRLS — plausible values)
├── infra/                 # Configs de Postgres, Prefect, Caddy
│
├── docs/
│   ├── operations/        # Como rodar/operar o sistema (vivo)
│   ├── architecture/      # Camadas e diagramas
│   ├── methodology.md     # Plausible values, ISCED, copyright
│   ├── conventions.md     # Padrões Python/TS/Git/SQL
│   ├── adrs/              # Architecture Decision Records
│   ├── refactor/          # Análises de refactor recentes
│   ├── references/        # data-sources.md (40+ bases)
│   ├── quality-assessment-2026-05-14.md
│   └── archive/           # Docs históricas (fases, runs antigos)
│
└── data/                  # Data lake Medallion (NÃO versionado)
    ├── bronze/            # Dados brutos, imutáveis
    ├── silver/            # (intermediate em DuckDB)
    ├── gold/              # (marts em DuckDB)
    ├── chromadb/          # Vector store RAG
    └── duckdb/            # education.duckdb
```

---

## Documentação por necessidade

| Quero... | Leia |
|---|---|
| Entender o que o sistema faz | Este README + [`docs/architecture/overview.md`](docs/architecture/overview.md) |
| Rodar o sistema localmente | [`docs/operations/running-the-system.md`](docs/operations/running-the-system.md) |
| Recoletar/atualizar dados | [`docs/operations/data-pipeline.md`](docs/operations/data-pipeline.md) |
| Trocar de LLM ou provider | [`docs/operations/models-and-providers.md`](docs/operations/models-and-providers.md) |
| Debugar quando algo falha | [`docs/operations/monitoring-and-debugging.md`](docs/operations/monitoring-and-debugging.md) |
| Saber por que tal escolha foi feita | [`docs/adrs/`](docs/adrs/) |
| Detalhes metodológicos (PISA, ISCED) | [`docs/methodology.md`](docs/methodology.md) |
| Catálogo completo das bases | [`docs/references/data-sources.md`](docs/references/data-sources.md) |
| Contribuir com código | [`docs/conventions.md`](docs/conventions.md) |

---

## Princípios inegociáveis

1. **Rigor acadêmico acima de velocidade** — resultados estatisticamente inválidos são piores que nenhum resultado.
2. **Reprodutibilidade total** — toda transformação versionada no Git; dbt obrigatório.
3. **Imutabilidade da camada Bronze** — dados brutos nunca são alterados.
4. **Plausible Values corretos** — PISA/TIMSS/PIRLS exigem BRR/Jackknife.
5. **Transparência da fonte** — toda resposta ao usuário mostra de onde vieram os dados.
6. **Copyright e ética** — citar todas as fontes, respeitar licenças.

---

## Licença

A definir (projeto acadêmico). Dados ingeridos permanecem sob as licenças das respectivas fontes oficiais.
