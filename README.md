# Análise Educacional Comparada — Brasil × Internacional

> Sistema acadêmico de análise e visualização de dados educacionais que responde:
> **"Como a educação básica brasileira se compara à educação dos países desenvolvidos?"**

Um Data Lakehouse educacional + sistema multi-agente conversacional + interface web unificada. Stack 100% open source, pensado para rodar on-premise.

A fonte de verdade arquitetural do projeto é o [`CLAUDE.md`](./CLAUDE.md) — leia-o antes de qualquer contribuição.

---

## Quick start (Fase 0 — Bootstrap)

### Pré-requisitos

- Docker Engine **24+** e Docker Compose **v2**
- Git
- Python **3.11+** (opcional, para desenvolvimento local fora dos containers)
- Node.js **20+** (opcional, para desenvolvimento local do frontend)
- R **4.3+** (somente nas fases de extração de PISA/TIMSS/PIRLS)

### 1. Clonar e configurar variáveis de ambiente

```bash
git clone <url-do-repo> analise_education_chatbot
cd analise_education_chatbot

cp .env.example .env
# Edite .env e preencha pelo menos:
#   - POSTGRES_PASSWORD (troque a senha padrão)
#   - ANTHROPIC_API_KEY (só necessário a partir da Fase 5)
```

### 2. Subir todos os serviços

```bash
docker compose up -d
```

Aguarde ~30s e valide que cada serviço respondeu:

| Serviço      | URL                             | O que esperar                   |
| ------------ | ------------------------------- | ------------------------------- |
| Frontend     | <http://localhost:3000>         | Página "hello world" estilizada |
| FastAPI docs | <http://localhost:8000/docs>    | Swagger UI com `/api/health`    |
| Health check | <http://localhost:8000/api/health> | JSON `{"status": "ok", ...}` |
| Prefect UI   | <http://localhost:4200>         | Dashboard do Prefect Server     |
| Adminer      | <http://localhost:8080>         | Login no Postgres               |

### 3. Derrubar quando terminar

```bash
docker compose down
# Para apagar também os volumes (dados do Postgres/Prefect):
docker compose down -v
```

---

## Instalação local (sem Docker)

Cada serviço Python tem seu próprio `pyproject.toml` e um virtualenv isolado. Recomendamos [`uv`](https://docs.astral.sh/uv/) para velocidade.

```bash
# API
cd api && uv venv && uv pip install -e ".[dev]" && cd ..

# Data pipeline
cd data_pipeline && uv venv && uv pip install -e ".[dev]" && cd ..

# Agents
cd agents && uv venv && uv pip install -e ".[dev]" && cd ..

# Frontend
cd frontend && npm install && cd ..
```

### Rodar FastAPI localmente

```bash
cd api
source .venv/bin/activate   # ou .venv/Scripts/activate no Windows
uvicorn src.main:app --reload --port 8000
```

### Rodar frontend localmente

```bash
cd frontend
npm run dev
```

### Rodar os testes

```bash
# API
cd api && pytest -v

# Data pipeline
cd data_pipeline && pytest -v
```

---

## Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
# Rodar manualmente em todos os arquivos:
pre-commit run --all-files
```

Os hooks verificam: `ruff` (lint + format Python), `prettier` (JS/TS/MD/YAML), chaves privadas, whitespace, arquivos grandes.

---

## Estrutura do projeto

```text
.
├── CLAUDE.md              # Guia mestre (arquitetura, roadmap, convenções)
├── docker-compose.yml     # Orquestração dos serviços
├── .env.example           # Template de variáveis de ambiente
├── api/                   # FastAPI gateway (Camada 5)
├── agents/                # Sistema CrewAI (Camada 4)
├── data_pipeline/         # Coletores e flows Prefect (Camada 1)
├── dbt_project/           # Transformações SQL (Camada 3)
├── frontend/              # Next.js 14 (Camada 6)
├── r_scripts/             # Scripts R (PISA/TIMSS/PIRLS)
├── infra/                 # Configs de Postgres, Prefect, Caddy
├── docs/
│   ├── architecture/      # Diagramas JSX interativos
│   ├── references/        # data-sources.md, methodology-notes.md
│   └── adrs/              # Architecture Decision Records
└── data/                  # Data lake Medallion (NÃO versionado)
    ├── bronze/            # Dados brutos, imutáveis
    ├── silver/            # Dados limpos e harmonizados
    ├── gold/              # Datasets analíticos
    ├── chromadb/          # Vector store para RAG
    └── duckdb/            # education.duckdb
```

---

## Roadmap (6 fases)

| Fase | Semanas | Escopo                                       |
| ---- | ------- | -------------------------------------------- |
| 0    | 1       | **Bootstrap** — estrutura, Docker, hello world |
| 1    | 2–4     | Ingestão e Bronze Layer (10 bases)           |
| 2    | 5–7     | Silver Layer + dbt + testes                  |
| 3    | 8–9     | Gold Layer + OpenMetadata                    |
| 4    | 10–11   | FastAPI Gateway completo                     |
| 5    | 12–15   | Sistema de agentes CrewAI                    |
| 6    | 16–19   | Frontend Next.js completo                    |

Detalhes em [`CLAUDE.md`](./CLAUDE.md#roadmap-de-desenvolvimento-6-fases).

---

## Princípios inegociáveis

1. **Rigor acadêmico acima de velocidade** — resultados estatisticamente inválidos são piores que nenhum resultado.
2. **Reprodutibilidade total** — toda transformação versionada no Git; dbt obrigatório.
3. **Imutabilidade da camada Bronze** — dados brutos nunca são alterados.
4. **Plausible Values corretos** — PISA/TIMSS/PIRLS exigem metodologia BRR/Jackknife.
5. **Transparência da fonte** — toda resposta ao usuário mostra de onde vieram os dados.
6. **Copyright e ética** — citar todas as fontes, respeitar licenças de uso.

---

## Licença

A definir (projeto acadêmico). Os dados ingeridos permanecem sob as licenças das respectivas fontes oficiais.
