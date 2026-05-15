# Camadas do sistema

Visão estática das 6 camadas + camada 0 (fontes externas). Substitui
o conteúdo do antigo [`edu-arch.jsx`](edu-arch.jsx) em formato texto.

```mermaid
flowchart TB
    L6["<b>Camada 6 — Interface</b><br/>Next.js 14 · TS · Tailwind · shadcn/ui<br/>Workspace: chat + dashboards + explorer"]
    L5["<b>Camada 5 — Gateway de Integração</b><br/>FastAPI 0.110+ · Pydantic v2 · Uvicorn · SlowAPI<br/>SSE streaming · Rate limiting"]
    L4["<b>Camada 4 — Sistema de Agentes</b><br/>CrewAI 0.80+ · 8 agentes + Fact Checker<br/>Ollama qwen2.5 (smart/fast)"]
    L3["<b>Camada 3 — Processamento Analítico</b><br/>DuckDB 1.x · dbt Core · pandas/polars<br/>Silver/Gold com testes dbt"]
    L2["<b>Camada 2 — Armazenamento (Medallion)</b><br/>Bronze (Parquet imutável) → Silver (clean)<br/>→ Gold (analítico) · ChromaDB (RAG)"]
    L1["<b>Camada 1 — Ingestão e Orquestração</b><br/>Prefect 3 · Python collectors · EdSurvey (R)<br/>Agendamento · Retry · Logging"]
    L0["<b>Camada 0 — Fontes de Dados</b><br/>APIs REST (SIDRA, IPEA, WB, UIS, OECD, Eurostat, CEPAL)<br/>Downloads ZIP (INEP, PISA, TIMSS, PIRLS)"]

    L6 -->|HTTP/SSE| L5
    L5 -->|in-process Python| L4
    L4 -->|SQL/API calls| L3
    L3 -->|reads| L2
    L1 -->|writes| L2
    L0 -->|reads| L1
```

## Por camada

### Camada 0 — Fontes de dados externos

40+ bases mapeadas em [`../references/data-sources.md`](../references/data-sources.md).
Combina:
- **APIs REST maduras** (IBGE SIDRA, IPEADATA OData, World Bank, UNESCO UIS,
  Eurostat JSON-stat, OECD SDMX, CEPALSTAT) — ingestão programática.
- **Downloads em lote** (INEP microdados, PISA/TIMSS/PIRLS SPSS) — ZIPs anuais.
- **Repositórios** (Base dos Dados via BigQuery, GitHub llece/erce).

### Camada 1 — Ingestão e orquestração

`data_pipeline/src/collectors/<fonte>/` — cada coletor herda de
[`BaseCollector`](../../data_pipeline/src/collectors/base.py) e implementa:
- `build_url(period)` — resolução da URL para o período.
- `fetch(...)` — usa `_http_fetch_json` ou `_http_fetch_paginated` da base.
- Schema canônico de saída (parquet em `data/bronze/<fonte>/<ano>/`).

Flows Prefect em `data_pipeline/src/flows/` agendam coletas. Manutenção
e retries automáticos.

### Camada 2 — Armazenamento Medallion

```
data/
├── bronze/      Parquet por fonte+ano (imutável — nunca modificado)
├── silver/      (Histórico Delta — hoje vive em DuckDB main_intermediate)
├── gold/        (Histórico Parquet — hoje vive em DuckDB main_marts)
├── chromadb/    Vector store p/ RAG (25 papers seed)
└── duckdb/      education.duckdb (~5 MB)
```

ChromaDB é a base do **Retrieval-Augmented Generation** consumido pelo
Citation Agent e Comparativist.

### Camada 3 — Processamento analítico

**dbt Core + adapter dbt-duckdb**. Modelos em `dbt_project/models/`:
- `staging/` — 1:1 com Bronze, tipagem e renomeação.
- `intermediate/` — joins, ISCED 2011, harmonização ISO-3.
- `marts/` — 5 marts analíticos finais com testes.

Toda Gold tem `not_null` em chaves primárias e range plausível em métricas.
`dbt build` roda 137 testes.

### Camada 4 — Sistema de agentes (CrewAI)

Ver [`agents.md`](agents.md) para detalhe. Resumo:
- **Core Crew** (Orchestrator + Profiler) — roteamento, fluxo, perfil.
- **Analysis Crew** (Retriever + Statistician + Comparativist + Citation) — dados + análise + literatura.
- **Synthesis Crew** (Visualizer + Synthesizer) — figure dict + markdown final.
- **Fact Checker** (determinístico) — valida números do markdown vs `primary_data`.

### Camada 5 — Gateway FastAPI

`api/src/routers/`:
- `data.py` — `/api/data/{catalog,timeseries,compare,ranking}`
- `health.py` — `/api/health`

Mais: `agents-server` (em `agents/src/server/`) na porta 8001 expõe
`/api/chat/stream` (SSE) e proxia ao master flow CrewAI.

### Camada 6 — Frontend Next.js 14

`frontend/app/` — App Router, 3 colunas (Sidebar + Workspace + ContextPanel).
Rotas:
- `/compare` — chat de análise comparada.
- `/explorer` — explorador de marts Gold.
- `/library` — biblioteca de citações.

Cliente HTTP em `frontend/lib/api-client.ts`. Tipos gerados via
`openapi-typescript` do schema OpenAPI do gateway.
