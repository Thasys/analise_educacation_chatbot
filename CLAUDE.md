# CLAUDE.md — Guia Mestre do Projeto

> **Sistema de Análise Comparada Brasil × Internacional em Educação Básica**
> Documento de contexto permanente para sessões com Claude Code.
> **Leia este arquivo na íntegra antes de qualquer tarefa.**

---

## 🎯 Identidade e missão do projeto

### O que estamos construindo

Um sistema acadêmico de análise e visualização de dados educacionais que responde à pergunta central: **"Como a educação básica brasileira se compara à educação dos países desenvolvidos?"**

O sistema tem três componentes integrados:

1. **Data Lakehouse educacional** — ingere, armazena e harmoniza 40+ bases de dados oficiais (INEP, IBGE, OCDE, UNESCO, World Bank, Eurostat, IEA, etc.)
2. **Sistema multi-agente conversacional** — baseado em CrewAI, permite que usuários façam perguntas em linguagem natural e recebam análises fundamentadas em dados reais
3. **Interface web unificada** — Next.js 14 com chat + dashboards + explorador de dados + biblioteca de citações acadêmicas

### Público-alvo (múltiplos perfis)

O sistema detecta automaticamente e adapta-se a três perfis:
- **Pesquisadores/acadêmicos** — linguagem técnica, SQL visível, intervalos de confiança, DOIs expandidos
- **Gestores públicos/policy makers** — gráficos simplificados, recortes territoriais, referências ao PNE
- **Estudantes/público geral** — glossário inline, analogias, sugestões de próxima pergunta

### Contexto do desenvolvimento

- **Infraestrutura**: on-premise, servidores próprios (Ubuntu 22.04 LTS)
- **Equipe**: solo developer (projeto acadêmico)
- **Orçamento de infra**: R$ 0 além do servidor (tudo open source)
- **Horizonte de escala**: pesquisa individual / institucional acadêmica
- **Hardware mínimo**: 16 GB RAM, 4 cores CPU, 500 GB SSD
- **Hardware recomendado**: 32 GB RAM, 8+ cores CPU, 1–2 TB SSD

### Princípios não-negociáveis

1. **Rigor acadêmico acima de velocidade** — resultados estatisticamente inválidos são piores que nenhum resultado
2. **Reprodutibilidade total** — toda transformação versionada no Git; dbt obrigatório
3. **Imutabilidade da camada Bronze** — dados brutos nunca são alterados
4. **Plausible Values corretos** — PISA, TIMSS, PIRLS exigem metodologia BRR/Jackknife
5. **Transparência da fonte** — toda resposta ao usuário mostra de onde vieram os dados
6. **Copyright e ética** — citar todas as fontes, respeitar licenças de uso

---

## 🏗️ Arquitetura de alto nível

O sistema é organizado em **6 camadas funcionais** que se comunicam através de interfaces bem definidas:

```
┌─────────────────────────────────────────────────────────────┐
│  CAMADA 6: INTERFACE                                        │
│  Next.js 14 · TypeScript · Tailwind · shadcn/ui             │
│  Workspace único: chat + dashboards + explorador + citações│
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / SSE streaming
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA 5: GATEWAY DE INTEGRAÇÃO                            │
│  FastAPI 0.110+ · Pydantic v2 · Uvicorn · SlowAPI          │
│  Endpoint unificado · Streaming SSE · Rate limiting         │
└───────────────────────────┬─────────────────────────────────┘
                            │ in-process Python
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA 4: SISTEMA DE AGENTES                               │
│  CrewAI 0.80+ · 8 agentes especializados · 3 crews          │
│  Processo hierárquico · LLMs Claude Sonnet 4.5 + Haiku 4.5 │
└───────────────────────────┬─────────────────────────────────┘
                            │ SQL / API calls
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA 3: PROCESSAMENTO ANALÍTICO                          │
│  DuckDB 1.x · dbt Core · pandas/polars                      │
│  Transformações versionadas · Testes de qualidade           │
└───────────────────────────┬─────────────────────────────────┘
                            │ reads
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA 2: ARMAZENAMENTO (MEDALLION)                        │
│  🥉 Bronze (raw) → 🥈 Silver (clean) → 🥇 Gold (analytical) │
│  Delta Lake · Parquet · PostgreSQL (metadados)              │
│  ChromaDB (RAG de literatura científica)                    │
└───────────────────────────┬─────────────────────────────────┘
                            │ populated by
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA 1: INGESTÃO E ORQUESTRAÇÃO                          │
│  Prefect 3 · Python collectors · EdSurvey (R) · intsvy      │
│  Agendamento · Retry · Monitoramento · Docker Compose       │
└─────────────────────────────────────────────────────────────┘
                            │ reads from
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  CAMADA 0: FONTES DE DADOS                                  │
│  APIs REST: IBGE SIDRA, IPEADATA, World Bank, UIS,          │
│  Eurostat, OECD SDMX, CEPALSTAT, UK DfE                     │
│  Downloads em lote: INEP (Censo, SAEB, ENEM), PISA, TIMSS, │
│  PIRLS, ICCS, TALIS, ERCE                                   │
│  Repositórios: Base dos Dados (BigQuery), GitHub llece/erce │
└─────────────────────────────────────────────────────────────┘
```

Os diagramas interativos detalhados estão em:
- `docs/architecture/edu-arch.jsx` — Data Lakehouse
- `docs/architecture/crewai-arch.jsx` — Sistema de Agentes
- `docs/architecture/frontend-arch.jsx` — Frontend e Integração

---

## 📦 Stack tecnológico completo

### Data Lakehouse (Camadas 1–3)

| Função | Tecnologia | Versão | Notas |
|---|---|---|---|
| Orquestração | Prefect | 3.x | UI local em :4200 |
| Ingestão Python | httpx, requests, pandas, pyarrow | latest | Pacotes: sidrapy, ipeadatapy, wbdata |
| Ingestão R | EdSurvey, intsvy, RALSA | latest | Obrigatório para PISA/TIMSS/PIRLS |
| Motor analítico | DuckDB | 1.x | Principal motor SQL |
| Transformações | dbt Core | latest | com dbt-duckdb adapter |
| Armazenamento colunar | Delta Lake + Parquet | latest | Compressão 5–10× |
| Metadados | PostgreSQL | 16 | Catálogo relacional |
| Catálogo de dados | OpenMetadata | latest | UI de descoberta |
| Qualidade de dados | Great Expectations | latest | Testes automatizados |

### Sistema de Agentes (Camada 4)

| Função | Tecnologia | Versão |
|---|---|---|
| Framework multi-agente | CrewAI | 0.80+ |
| LLM principal | Claude Sonnet 4.5 | via API Anthropic |
| LLM rápido | Claude Haiku 4.5 | classificação e tarefas simples |
| Embeddings | sentence-transformers | multilingual |
| Vector DB (RAG) | ChromaDB | embedded |
| Observabilidade | Langfuse ou LangSmith | self-hosted |

### Integração (Camada 5)

| Função | Tecnologia | Versão |
|---|---|---|
| Gateway API | FastAPI | 0.110+ |
| Validação | Pydantic | v2 |
| Servidor ASGI dev | Uvicorn | latest |
| Servidor ASGI prod | Gunicorn + UvicornWorker | latest |
| Rate limiting | SlowAPI | latest |
| Streaming | Server-Sent Events (nativo) | — |

### Frontend (Camada 6)

| Função | Tecnologia | Versão |
|---|---|---|
| Framework React | Next.js | 14 (App Router) |
| Linguagem | TypeScript | 5.x (strict) |
| Estilização | Tailwind CSS | 4.x |
| Componentes UI | shadcn/ui (Radix + Tailwind) | latest |
| Estado | Zustand | latest |
| Cache de queries | TanStack Query | v5 |
| Gráficos interativos | Plotly.js (react-plotly.js) | latest |
| Gráficos simples | Recharts | latest |
| Markdown | react-markdown + remark-gfm | latest |

### Deploy e Operações

| Função | Tecnologia |
|---|---|
| Containerização | Docker + Docker Compose |
| Proxy reverso | Caddy (HTTPS automático) |
| Versionamento | Git + Gitea (self-hosted) |
| CI local | GitHub Actions local runner OU Drone CI |

---

## 🗄️ Especificação da camada de dados

### Padrão Medallion (Bronze → Silver → Gold)

**Bronze** (`/data/bronze/<fonte>/<ano>/`)
- Dados brutos exatamente como recebidos das fontes
- Formato: Parquet (preferido), JSON, CSV, SPSS (convertido)
- **Imutável**: nunca alterado após gravação
- Particionamento: por fonte e ano
- Retenção: indefinida

**Silver** (`/data/silver/<dominio>/`)
- Dados limpos, normalizados, com codificações padronizadas
- ISCED 2011 aplicado consistentemente
- Joins-chave resolvidos (códigos IBGE, ISO-3166, ISCED)
- Schema Delta Lake com evolução controlada
- Testes Great Expectations obrigatórios

**Gold** (`/data/gold/<dataset_analitico>/`)
- Datasets analíticos prontos para consulta
- Indicadores derivados pré-calculados
- Séries temporais comparativas BR × Internacional
- Otimizado para DuckDB (Parquet, ordenado, compactado)
- Acessado pelo FastAPI e pelos agentes

### Estrutura de diretórios do data lake

```
/data/
├── bronze/
│   ├── inep/
│   │   ├── censo_escolar/2023/
│   │   ├── saeb/2023/
│   │   ├── enem/2024/
│   │   └── ideb/2023/
│   ├── ibge/
│   │   ├── pnad_continua/2024/
│   │   └── censo_demografico/2022/
│   ├── oecd/
│   │   ├── pisa/2022/
│   │   └── talis/2024/
│   ├── iea/
│   │   ├── timss/2023/
│   │   └── pirls/2021/
│   ├── unesco_uis/
│   ├── world_bank/
│   ├── eurostat/
│   └── cepalstat/
├── silver/
│   ├── educacao_basica_br/
│   ├── avaliacoes_internacionais/
│   ├── indicadores_uis/
│   └── indicadores_socioeconomicos/
└── gold/
    ├── br_vs_ocde_timeseries/
    ├── pisa_rankings/
    ├── ideb_municipal/
    ├── investimento_educacional/
    └── comparativo_latam/
```

### Modelagem dbt

A organização dos modelos dbt segue:

```
models/
├── staging/          # 1:1 com Bronze, tipagem e renomeação
│   ├── stg_inep__*
│   ├── stg_ibge__*
│   ├── stg_oecd__*
│   └── ...
├── intermediate/     # Silver: joins, codificações, limpeza
│   ├── int_educacao_basica_br__*
│   └── ...
└── marts/            # Gold: tabelas analíticas finais
    ├── mart_br_vs_ocde__*
    ├── mart_pisa_rankings__*
    └── ...
```

Regras dbt:
- Toda tabela Gold tem teste de `not_null` em chaves primárias
- Toda métrica tem teste de range plausível
- Todo modelo tem descrição no `schema.yml`
- Linhagem completa visualizável via `dbt docs generate`

---

## 🤖 Especificação do sistema de agentes

### Arquitetura das Crews

**Core Crew** (sempre ativo)
- Orchestrator Agent — roteador principal, conversa com usuário
- Profile & Intent Agent — detecta perfil e decompõe pergunta

**Analysis Crew** (ativado para perguntas com dados)
- Data Retrieval Agent — gera SQL, executa via FastAPI → DuckDB
- Statistical Analyst Agent — valida significância, aplica plausible values
- Comparative Education Agent — contextualiza comparações BR × Internacional
- Citation & Evidence Agent — RAG sobre literatura científica

**Synthesis Crew** (sempre ativo no final)
- Visualization Agent — gera Plotly specs
- Response Synthesizer Agent — adapta ao perfil e formata resposta

### Três fluxos de execução

1. **Fluxo Simples** (~5–10s, ~5k tokens)
   - Perguntas conceituais/contextuais, sem dados numéricos
   - Path: Orchestrator → Profiler → Comparativist (RAG) → Synthesizer

2. **Fluxo com Dados** (~20–40s, ~15k tokens) — padrão mais comum
   - Requer métricas reais, séries históricas, comparações numéricas
   - Path: Orchestrator → Profiler → Retriever → Statistician → Comparativist → Visualizer → Synthesizer

3. **Fluxo Deep Research** (~60–120s, ~80k tokens)
   - Análise causal/multifator com literatura
   - Path: todos os agentes + múltiplas queries + RAG extensivo

### Regra crítica: agentes NÃO escrevem SQL livre

Por razões de segurança e qualidade metodológica, os agentes **não** constroem SQL bruto. Eles chamam endpoints pré-validados do FastAPI:

- `/api/data/compare` — comparações entre países/regiões
- `/api/data/timeseries` — séries temporais de indicadores
- `/api/data/ranking` — rankings (ex: PISA)
- `/api/data/distribution` — distribuições socioeconômicas

Cada endpoint internamente constrói SQL seguro e aplica a metodologia correta (ex: plausible values para PISA).

### Ferramentas (Tools) por agente

```python
# Exemplo: estrutura de tool do CrewAI
from crewai.tools import BaseTool
import httpx

class CompareCountriesTool(BaseTool):
    name: str = "CompareCountriesTool"
    description: str = (
        "Compara indicadores educacionais entre países. "
        "Parâmetros: indicator (str), countries (list[str]), year (int). "
        "Retorna: JSON com valores, intervalos de confiança, fonte."
    )
    
    def _run(self, indicator: str, countries: list, year: int) -> str:
        response = httpx.post(
            "http://localhost:8000/api/data/compare",
            json={"indicator": indicator, "countries": countries, "year": year}
        )
        return response.json()
```

---

## 🌐 Especificação do frontend e integração

### Layout da interface (workspace único)

```
┌──────────┬──────────────────────────┬────────────────┐
│          │                          │                │
│ Sidebar  │    Workspace (chat +     │  Context       │
│ (nav)    │    visualizações)        │  Panel         │
│          │                          │                │
│ - Hist.  │    [msg usuário]         │  Fontes        │
│ - Dash.  │    [reasoning agentes]   │  Citações      │
│ - Data   │    [resposta + charts]   │  SQL usado     │
│ - Biblio │                          │  Export        │
│          │    [input box + envio]   │                │
└──────────┴──────────────────────────┴────────────────┘
```

### Endpoints FastAPI

| Método | Path | Descrição |
|---|---|---|
| POST | `/api/chat/stream` | Pergunta do usuário, retorna SSE stream |
| GET | `/api/chat/:id/reasoning` | SSE do progresso dos agentes |
| GET | `/api/data/catalog` | Lista datasets da Gold Layer |
| POST | `/api/data/query` | Query pré-validada no DuckDB |
| POST | `/api/data/compare` | Comparação entre países/regiões |
| POST | `/api/data/timeseries` | Séries temporais |
| POST | `/api/data/ranking` | Rankings PISA/TIMSS/etc |
| GET | `/api/data/:dataset/preview` | 100 linhas de amostra |
| POST | `/api/rag/search` | Busca semântica ChromaDB |
| GET | `/api/rag/citation/:doi` | Resolve DOI |
| POST | `/api/viz/generate` | Gera Plotly spec |
| GET | `/api/health` | Health check completo |
| GET | `/api/profile/detect` | Detecta perfil do usuário |

### Padrão de comunicação

- **REST síncrono**: catálogo, preview, health, busca RAG
- **Server-Sent Events**: streaming de resposta LLM + progresso dos agentes
- **WebSocket**: somente se precisar bidirecional (cancelamento, colaboração)
- **Background jobs (Prefect)**: re-indexação RAG, refresh Gold, modelos ML

---

## 📚 Bases de dados (resumo executivo)

A lista completa com 40+ bases está em `docs/references/data-sources.md`. Aqui está o essencial:

### Bases brasileiras (prioridade máxima)

1. **INEP — Censo Escolar** (anual, ZIP)
2. **INEP — SAEB** (bienal, ZIP + inputs SAS/SPSS)
3. **INEP — ENEM** (anual, ZIP)
4. **INEP — IDEB** (bienal, XLSX)
5. **IBGE — PNAD Contínua** (trimestral + módulo anual de Educação) — **tem API SIDRA**
6. **IBGE — Censo Demográfico 2022** (decenal, microdados + SIDRA)
7. **IPEADATA** — **tem API OData v4 RESTful**
8. **Atlas IDHM** (decenal, CSV)
9. **Base dos Dados** — **SQL via BigQuery** (principal atalho para microdados BR harmonizados)

### Bases internacionais (prioridade máxima)

10. **OCDE Data Explorer** — **SDMX REST** (⚠ endpoint antigo `stats.oecd.org` descontinuado em 07/2024; usar `sdmx.oecd.org`)
11. **OCDE PISA** — microdados SPSS/SAS + agregados SDMX
12. **OCDE TALIS** — microdados SPSS/SAS/CSV (2024 inclui R)
13. **UNESCO UIS** — **API + BDDS** (SDG 4)
14. **Eurostat** — **JSON-stat + SDMX**
15. **NCES NAEP** — **API JSON**
16. **World Bank EdStats** — **API JSON robusta**
17. **IEA TIMSS/PIRLS/ICCS** — downloads SPSS/SAS (sem API)
18. **UK DfE Explore Education Statistics** — **API REST**

### Bases comparativas BR × Internacional

19. **ERCE/LLECE** (Brasil participa desde SERCE 2006) — microdados em GitHub oficial
20. **Human Capital Index (World Bank)** — via API WDI
21. **Barro-Lee Educational Attainment** — XLS/CSV estáticos
22. **Harmonized Learning Outcomes (World Bank)** — base que harmoniza PISA/TIMSS/PIRLS/ERCE

### Alertas metodológicos críticos

⚠️ **Brasil NÃO participa** de PIAAC, ICILS — comparações de adultos/digital exigem análogos (INAF, TIC Educação)
⚠️ **TIMSS**: lacuna de 20 anos entre 2003 e 2023 — tendências de longo prazo são complicadas
⚠️ **PIRLS**: Brasil participou pela primeira vez em 2021
⚠️ **PISA plausible values**: SEMPRE usar `intsvy` (R) ou `EdSurvey` — análises sem BRR/Jackknife são inválidas

---

## 🛣️ Roadmap de desenvolvimento (6 fases)

### Fase 0 — Bootstrap do projeto (semana 1)

**Objetivo**: estrutura base, Docker Compose funcional, "hello world" em todas as camadas.

Tarefas:
1. Criar estrutura de diretórios completa
2. Configurar `docker-compose.yml` com: Postgres, DuckDB volume, Prefect, FastAPI, Next.js, Adminer
3. Configurar `.env.example` com todas as variáveis necessárias
4. Configurar linting: `ruff` (Python), `eslint` + `prettier` (TS/TSX)
5. Configurar `pre-commit` hooks
6. Setup Git com `.gitignore` adequado (excluir `/data/`, `.env`, `node_modules/`, `.venv/`)
7. README.md com instruções de setup
8. Testar `docker-compose up` — todos os serviços devem subir

**Critério de conclusão**: rodar `docker-compose up` sem erros; acessar Prefect UI, FastAPI docs e Next.js hello world.

### Fase 1 — Ingestão e Bronze Layer (semanas 2–4)

**Objetivo**: pipeline de ingestão funcional para 10 bases prioritárias.

Tarefas:
1. Criar coletores Prefect para:
   - IBGE SIDRA (tabelas 7136-7144, 7186-7188, 9423)
   - IPEADATA OData
   - World Bank API
   - UNESCO UIS API
   - Eurostat API (JSON-stat)
   - OCDE SDMX
   - CEPALSTAT API
2. Criar coletores em lote para:
   - INEP microdados (Censo Escolar, SAEB, ENEM, IDEB) — ZIPs
   - PISA 2022 (SPSS) — usar `pyreadstat`
   - TIMSS 2023 (SPSS)
   - PIRLS 2021 (SPSS)
3. Estruturar Bronze em `/data/bronze/<fonte>/<ano>/`
4. Salvar tudo em Parquet (exceto fontes que exigem formato específico)
5. Agendar refreshes no Prefect (anuais para maioria)
6. Logs de ingestão em PostgreSQL

**Critério de conclusão**: 10 bases em Bronze, metadados catalogados, re-execução idempotente.

### Fase 2 — Silver Layer e dbt (semanas 5–7)

**Objetivo**: dados limpos, harmonizados, testados.

Tarefas:
1. Configurar dbt com adapter `dbt-duckdb`
2. Criar `models/staging/` (1:1 com Bronze, tipagem)
3. Criar `models/intermediate/` (limpeza, codificações ISCED/ISO)
4. Configurar `schema.yml` com testes
5. Configurar Great Expectations para validações complexas
6. Documentar linhagem com `dbt docs`
7. Harmonizar códigos:
   - Países: ISO-3166-alpha3
   - UFs: códigos IBGE
   - Municípios: códigos IBGE 7 dígitos
   - Níveis: ISCED 2011

**Critério de conclusão**: `dbt build` passa todos os testes; documentação visualizável.

### Fase 3 — Gold Layer e catálogo (semanas 8–9)

**Objetivo**: datasets analíticos prontos para consulta.

Tarefas:
1. Criar `models/marts/` com as principais tabelas:
   - `mart_br_vs_ocde_timeseries`
   - `mart_pisa_rankings`
   - `mart_ideb_municipal`
   - `mart_investimento_educacional`
   - `mart_comparativo_latam`
2. Indicadores derivados: diferença em pontos padronizados, percentis, tendências
3. Configurar OpenMetadata apontando para DuckDB
4. Popular descrições e glossário
5. Configurar lineage

**Critério de conclusão**: queries analíticas típicas executam em < 2s; catálogo navegável.

### Fase 4 — FastAPI Gateway (semanas 10–11)

**Objetivo**: API unificada para agentes e frontend.

Tarefas:
1. Estruturar FastAPI com roteadores separados por domínio:
   - `/api/chat/` — streaming SSE
   - `/api/data/` — queries ao DuckDB
   - `/api/rag/` — busca semântica
   - `/api/viz/` — geração de gráficos
   - `/api/profile/` — detecção de perfil
2. Implementar endpoints pré-validados (nunca SQL livre dos agentes)
3. Adicionar middleware: CORS, rate limit (SlowAPI), logging, tracing
4. Gerar tipos TypeScript automaticamente via `openapi-typescript`
5. Documentar tudo via OpenAPI / Swagger

**Critério de conclusão**: `curl` em todos os endpoints retorna respostas válidas; docs OpenAPI completas.

### Fase 5 — Sistema de agentes CrewAI (semanas 12–15)

**Objetivo**: 8 agentes funcionais, 3 fluxos de execução.

Tarefas:
1. Configurar CrewAI com processo hierárquico
2. Implementar os 8 agentes conforme especificado
3. Criar todas as Tools (ver lista em `docs/architecture/crewai-arch.jsx`)
4. Implementar RAG com ChromaDB:
   - Popular com abstracts de SciELO, CAPES, ERIC, OCDE working papers
   - Embeddings multilingual
   - Metadados: DOI, autor, ano, revista, palavras-chave
5. Implementar roteamento de fluxos no Orchestrator
6. Configurar observabilidade (Langfuse)
7. Testes end-to-end dos 3 fluxos

**Critério de conclusão**: perguntas de exemplo retornam respostas coerentes com citações e gráficos válidos.

### Fase 6 — Frontend Next.js (semanas 16–19)

**Objetivo**: interface unificada completa.

Tarefas:
1. Scaffold Next.js 14 com App Router + TypeScript + Tailwind + shadcn/ui
2. Layout de 3 colunas (sidebar + workspace + context panel)
3. Componentes principais:
   - `<Chat>` com streaming SSE
   - `<AgentReasoning>` mostrando steps
   - `<InlineChart>` renderizando Plotly
   - `<CitationPanel>` com links DOI
   - `<DataExplorer>` para navegar Gold Layer
   - `<DashboardEmbed>` para Superset iframes
4. Estado com Zustand (perfil detectado, histórico, configurações)
5. Cache com TanStack Query
6. Adaptação automática ao perfil (3 temas visuais sutis)
7. Deploy via Docker + Caddy (HTTPS interno)

**Critério de conclusão**: usuário faz pergunta e recebe resposta completa com gráfico + citações em < 10s.

### Fase 7 (opcional) — Refinamentos e MLOps

- MLflow para modelos preditivos (se relevante)
- A/B testing de prompts
- Métricas de qualidade das respostas
- Feedback loop do usuário
- Relatórios Quarto para publicação acadêmica

---

## 📁 Estrutura de diretórios do projeto

```
educacao-comparada/
├── CLAUDE.md                          # ESTE ARQUIVO
├── README.md                           # Quick start para humanos
├── docker-compose.yml                  # Orquestração de todos os serviços
├── .env.example                        # Variáveis de ambiente (template)
├── .gitignore
├── .pre-commit-config.yaml
│
├── docs/
│   ├── architecture/
│   │   ├── edu-arch.jsx               # Diagrama Data Lakehouse
│   │   ├── crewai-arch.jsx            # Diagrama Agentes
│   │   └── frontend-arch.jsx          # Diagrama Frontend
│   ├── references/
│   │   ├── data-sources.md            # Lista completa 40+ bases
│   │   └── methodology-notes.md       # Notas metodológicas críticas
│   └── adrs/                          # Architecture Decision Records
│
├── infra/
│   ├── prefect/                       # Config Prefect
│   ├── postgres/                      # init.sql, config
│   ├── caddy/                         # Caddyfile
│   └── openmetadata/
│
├── data_pipeline/                     # Python (ingestão + orquestração)
│   ├── pyproject.toml
│   ├── src/
│   │   ├── collectors/                # Coletores por fonte
│   │   │   ├── inep/
│   │   │   ├── ibge/
│   │   │   ├── oecd/
│   │   │   ├── iea/
│   │   │   ├── unesco/
│   │   │   ├── worldbank/
│   │   │   ├── eurostat/
│   │   │   └── cepalstat/
│   │   ├── flows/                     # Prefect flows
│   │   ├── transforms/                # Transformações Python
│   │   └── utils/
│   └── tests/
│
├── r_scripts/                         # Scripts R (PISA/TIMSS/PIRLS)
│   ├── renv.lock
│   ├── pisa_extraction.R
│   ├── timss_extraction.R
│   └── pirls_extraction.R
│
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   ├── tests/
│   ├── macros/
│   └── seeds/
│
├── api/                                # FastAPI gateway
│   ├── pyproject.toml
│   ├── src/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── chat.py
│   │   │   ├── data.py
│   │   │   ├── rag.py
│   │   │   ├── viz.py
│   │   │   └── profile.py
│   │   ├── services/
│   │   ├── schemas/                   # Pydantic models
│   │   └── dependencies/
│   └── tests/
│
├── agents/                             # CrewAI system
│   ├── pyproject.toml
│   ├── src/
│   │   ├── crews/
│   │   │   ├── core_crew.py
│   │   │   ├── analysis_crew.py
│   │   │   └── synthesis_crew.py
│   │   ├── agents/
│   │   │   ├── orchestrator.py
│   │   │   ├── profiler.py
│   │   │   ├── retriever.py
│   │   │   ├── statistician.py
│   │   │   ├── comparativist.py
│   │   │   ├── citation.py
│   │   │   ├── visualizer.py
│   │   │   └── synthesizer.py
│   │   ├── tools/
│   │   ├── prompts/                   # System prompts dos agentes
│   │   └── rag/
│   │       ├── ingest.py              # popula ChromaDB
│   │       └── search.py
│   └── tests/
│
├── frontend/                           # Next.js 14
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.js
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                   # home
│   │   ├── compare/
│   │   │   └── page.tsx               # chat principal
│   │   ├── dashboards/
│   │   ├── explorer/
│   │   ├── library/
│   │   └── api/                       # proxy routes
│   ├── components/
│   │   ├── ui/                        # shadcn/ui
│   │   ├── chat/
│   │   ├── charts/
│   │   └── context-panel/
│   ├── lib/
│   │   ├── api-client.ts              # gerado via openapi-typescript
│   │   ├── stores/                    # Zustand
│   │   └── utils/
│   └── types/
│
└── data/                               # NÃO VERSIONAR
    ├── bronze/
    ├── silver/
    ├── gold/
    ├── chromadb/                      # vector store
    └── duckdb/
        └── education.duckdb
```

---

## 🧰 Convenções de desenvolvimento

### Python

- **Versão**: 3.11+
- **Formatter/Linter**: `ruff` (substitui black + flake8 + isort)
- **Type checking**: `mypy` em modo strict para módulos novos
- **Docstrings**: Google style
- **Testes**: `pytest` + `pytest-cov` (mínimo 70% em módulos críticos)
- **Dependências**: `uv` (mais rápido que pip) ou `poetry`
- **Virtualenv**: uma por serviço (data_pipeline, api, agents)

### TypeScript / Next.js

- **Modo strict**: `true`
- **Linter**: `eslint` + `prettier`
- **Imports**: absolutos com alias `@/`
- **Componentes**: Server Components por padrão; Client Components só quando necessário (`"use client"`)
- **Estado global**: Zustand; local: `useState`
- **Data fetching**: TanStack Query no cliente; `fetch` direto em Server Components

### Git

- **Branches**: `main` (estável), `dev` (integração), `feature/<descricao>` (trabalho)
- **Commits**: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`)
- **PRs**: mesmo sendo solo, usar PRs para revisão com Claude Code
- **Tags**: versionamento semântico por fase (`v0.1.0-fase-0`, etc.)

### SQL (dbt / DuckDB)

- **Estilo**: SQLFluff com dialeto DuckDB
- **Nomes**: snake_case para tabelas e colunas
- **CTEs**: sempre nomeadas, nunca aninhadas profundamente
- **Comentários**: obrigatórios em modelos de mart

### Segurança

- **Segredos**: nunca no Git. Usar `.env` + `direnv`
- **API keys LLM**: em `.env`, nunca hardcoded
- **Logs**: redact de PII e tokens
- **CORS**: lista explícita de origens permitidas

---

## ⚠️ Notas metodológicas críticas

Estas regras existem para garantir **validade acadêmica dos resultados**. Violar qualquer uma invalida a pesquisa.

### 1. Plausible Values (PISA, TIMSS, PIRLS)

Microdados de avaliações internacionais usam **10 plausible values** em vez de um único score. Análises corretas:
- Sempre usar pacotes especializados: `intsvy`, `EdSurvey`, `RALSA` (todos R)
- Ou em Python: `pisapy` ou exportar agregados pré-calculados via OECD Data Explorer
- **NUNCA tirar média simples dos PVs** — viesa erros-padrão
- Aplicar pesos BRR ou Jackknife conforme metodologia do estudo
- Referência: OECD PISA Data Analysis Manual (2024)

### 2. Harmonização de códigos

- Países: **ISO-3166-alpha3** (BRA, FIN, USA, etc.)
- UFs: códigos IBGE (2 dígitos)
- Municípios: códigos IBGE 7 dígitos (não usar IBGE 6 dígitos legado)
- Níveis educacionais: **ISCED 2011**
  - 0: ECEC
  - 1: Ensino Fundamental Anos Iniciais
  - 2: Ensino Fundamental Anos Finais
  - 3: Ensino Médio
  - 4+: pós-secundário

### 3. Comparabilidade temporal

- **TIMSS**: Brasil tem lacuna 2003–2023. Tendências longas exigem ressalvas explícitas
- **PIRLS**: Brasil só desde 2021
- **PISA**: Brasil desde 2000 (comparável)
- **Censo Escolar**: ruptura metodológica em 2007 (Educacenso)
- **SAEB**: antes de 2019 se chamava ANEB/Prova Brasil — escalas diferentes

### 4. Brasil não participa

- **PIAAC** (adultos): usar INAF (Instituto Paulo Montenegro) como análogo
- **ICILS** (letramento digital): usar TIC Educação (CETIC.br)

### 5. Copyright e citação

- Citar sempre a fonte oficial em toda resposta ao usuário
- Não reproduzir mais de 15 palavras literais de qualquer fonte sem aspas
- Para citações acadêmicas, usar DOI sempre que disponível
- Respeitar licença Open Government dos datasets

### 6. API deprecada

- `stats.oecd.org` foi **descontinuado em 01/07/2024**
- Usar sempre `sdmx.oecd.org/public/rest/`
- Rate limit: 60 queries/hora/IP (sem autenticação)

---

## 🚀 Comandos de setup inicial

Execute em ordem após clonar o repositório:

```bash
# 1. Variáveis de ambiente
cp .env.example .env
# editar .env com suas credenciais (Anthropic API key, Postgres password, etc.)

# 2. Pre-commit hooks
pip install pre-commit
pre-commit install

# 3. Ambiente Python por serviço
cd data_pipeline && uv venv && uv pip install -e ".[dev]" && cd ..
cd api && uv venv && uv pip install -e ".[dev]" && cd ..
cd agents && uv venv && uv pip install -e ".[dev]" && cd ..

# 4. Ambiente R para PISA/TIMSS/PIRLS
cd r_scripts && Rscript -e 'renv::restore()' && cd ..

# 5. Frontend
cd frontend && npm install && cd ..

# 6. dbt
cd dbt_project && dbt deps && dbt debug && cd ..

# 7. Subir infraestrutura
docker-compose up -d

# 8. Verificar saúde
curl http://localhost:8000/api/health
curl http://localhost:3000
open http://localhost:4200  # Prefect UI
```

---

## 💬 Prompts iniciais para sessões Claude Code

Use estes prompts em ordem. Cada um corresponde a um marco de desenvolvimento.

### Sessão 1: Validação do CLAUDE.md
```
Leia o CLAUDE.md e o docs/references/data-sources.md na íntegra.
Depois, me apresente:
1. Um resumo de 200 palavras do projeto
2. Três perguntas que você tem sobre o escopo
3. Qual deve ser o primeiro comando a executar na Fase 0
```

### Sessão 2: Bootstrap (Fase 0)
```
Estamos iniciando a Fase 0 (Bootstrap) descrita no CLAUDE.md.
Crie a estrutura de diretórios completa conforme especificado,
gere o docker-compose.yml com todos os serviços necessários,
configure .gitignore, .env.example, pre-commit e README.md.
Ao final, me mostre como testar que tudo subiu corretamente.
```

### Sessão 3: Primeiro coletor (Fase 1)
```
Estamos na Fase 1. Vamos começar pelo coletor mais simples:
IBGE SIDRA para tabelas de educação da PNAD Contínua.

Crie:
1. data_pipeline/src/collectors/ibge/sidra_educacao.py
2. O flow Prefect correspondente
3. Testes pytest
4. Documentação dos metadados salvos

Use a tabela SIDRA 7136 como exemplo inicial.
Salve em /data/bronze/ibge/pnad_continua_educacao/<ano>/ como Parquet.
```

### Sessão 4: dbt staging (Fase 2)
```
Fase 2 iniciada. Configure dbt com dbt-duckdb.
Crie o staging model para a tabela IBGE SIDRA 7136 que acabamos de ingerir.
Adicione schema.yml com testes not_null e unique onde aplicável.
Documente o modelo com uma descrição clara do que representa cada coluna.
```

### Sessão 5: FastAPI primeiro endpoint (Fase 4)
```
Fase 4. Crie a estrutura base do FastAPI em api/:
- main.py com lifespan events
- routers/health.py
- routers/data.py com o endpoint /api/data/catalog
- schemas/ com Pydantic models

Configure CORS para localhost:3000, rate limit (SlowAPI),
logging estruturado e OpenAPI docs em /docs.
```

### Sessão 6: Primeiro agente CrewAI (Fase 5)
```
Fase 5. Vamos construir o primeiro agente: Profile & Intent Agent.
Crie:
- agents/src/agents/profiler.py com o agente CrewAI
- agents/src/prompts/profiler_system.txt com o system prompt
- agents/src/tools/intent_classifier.py
- Testes com perguntas exemplo para cada perfil (pesquisador, gestor, estudante)

Use Claude Haiku 4.5 como LLM para este agente (baixo custo, alta velocidade).
```

### Sessão 7: Frontend scaffold (Fase 6)
```
Fase 6. Faça o scaffold do frontend Next.js 14:
- cd frontend && npx create-next-app@latest . --typescript --tailwind --app
- Instale shadcn/ui com os componentes: Button, Card, Dialog, Sheet, ScrollArea, Command, Badge, Collapsible
- Crie o layout de 3 colunas em app/compare/page.tsx
- Configure o cliente API com openapi-typescript apontando para FastAPI

Use o wireframe em docs/architecture/frontend-arch.jsx como referência visual.
```

---

## 🧪 Estratégia de testes

### Pirâmide de testes

```
         /\           E2E (poucos, críticos)
        /  \          - Playwright: fluxo chat completo
       /----\         
      /      \        Integração (moderado)
     /        \       - FastAPI TestClient
    /----------\      - dbt tests
   /            \     - Prefect test mode
  /--------------\    Unitários (muitos)
                      - pytest para collectors, tools, utils
                      - vitest para componentes React
```

### Cobertura-alvo

- Coletores de dados: **90%+** (crítico)
- Tools dos agentes: **85%+** (crítico)
- Endpoints FastAPI: **80%+**
- Transformações dbt: **100%** das tabelas com testes declarativos
- Componentes React: **60%+** (foco nos componentes de lógica)

### Testes de qualidade de dados

- Great Expectations suites por domínio
- dbt tests em todos os models
- Data contract tests entre Bronze/Silver/Gold
- Monitoramento de drift estatístico nas Gold tables

---

## 📊 Estratégia de observabilidade

### Logging

- **Python**: `structlog` com output JSON em produção
- **TypeScript**: `pino` com redação de PII
- **Nível padrão**: INFO em produção, DEBUG em desenvolvimento

### Métricas

- **Prometheus** (opcional): métricas de FastAPI, latência, erros
- **Grafana** (opcional): dashboards de saúde do sistema
- **Langfuse**: métricas específicas de LLM (tokens, custo, latência)

### Tracing

- **OpenTelemetry**: tracing distribuído entre FastAPI → CrewAI → DuckDB
- Span por agente, por tool call
- Exportar para Jaeger local

---

## 📖 Glossário

- **Medallion**: padrão de data lake com 3 camadas (Bronze/Silver/Gold)
- **BRR**: Balanced Repeated Replication — método de variância para amostras complexas
- **Jackknife**: técnica similar ao BRR para replicação de pesos
- **Plausible Values**: múltiplos valores simulados de proficiência (PISA/TIMSS/PIRLS)
- **ISCED**: International Standard Classification of Education
- **IDEB**: Índice de Desenvolvimento da Educação Básica (INEP)
- **SAEB**: Sistema de Avaliação da Educação Básica (INEP)
- **ENEM**: Exame Nacional do Ensino Médio (INEP)
- **PISA**: Programme for International Student Assessment (OCDE)
- **TIMSS**: Trends in International Mathematics and Science Study (IEA)
- **PIRLS**: Progress in International Reading Literacy Study (IEA)
- **ERCE**: Estudio Regional Comparativo y Explicativo (LLECE/UNESCO)
- **TALIS**: Teaching and Learning International Survey (OCDE)
- **SDMX**: Statistical Data and Metadata eXchange (padrão de APIs estatísticas)
- **UOE**: UNESCO-OCDE-Eurostat (coleta conjunta de indicadores educacionais)
- **dbt**: data build tool (transformações SQL versionadas)
- **RAG**: Retrieval-Augmented Generation
- **SSE**: Server-Sent Events
- **PNE**: Plano Nacional de Educação (Lei 13.005/2014)

---

## 🆘 Resolução de problemas comuns

### Docker Compose não sobe
- Verifique `docker --version` (>= 24.0)
- Verifique portas livres: 3000, 4200, 5432, 8000, 9200
- `docker compose logs <serviço>` para ver erros específicos

### DuckDB lento
- Aumente memória: `SET memory_limit='16GB'`
- Verifique que Parquets estão compactados: `PRAGMA parquet_metadata('file.parquet')`
- Use ORDER BY na escrita para co-locality

### Prefect flows falhando
- Verifique logs em Prefect UI (localhost:4200)
- Cheque retries na policy do flow
- Rate limits das APIs externas: respeitar 60 req/h da OCDE

### Agentes CrewAI com respostas ruins
- Revisar system prompts em `agents/src/prompts/`
- Verificar se as Tools estão retornando dados corretos
- Aumentar `max_iter` do agente se estiver cortando raciocínio
- Logar chamadas LLM com Langfuse para análise

---

## 📚 Referências bibliográficas fundamentais

Estas referências devem estar no RAG ChromaDB desde o início:

1. Schleicher, A. (2019). *World Class: How to Build a 21st-Century School System*. OECD Publishing.
2. Hanushek, E. A., & Woessmann, L. (2011). The economics of international differences in educational achievement. *Economic Policy*, 26(67).
3. Carnoy, M., Khavenson, T., Costa, L., & Marotta, L. (2015). A educação brasileira e o PISA. *Cadernos de Pesquisa*, 45(157).
4. Soares, J. F., & Alves, M. T. G. (2003). Desigualdades raciais no sistema brasileiro de educação básica. *Educação e Pesquisa*, 29(1).
5. Fernandes, R. (2007). *Índice de Desenvolvimento da Educação Básica (Ideb)*. Série Documental INEP, n.26.
6. Angrist, N., Djankov, S., Goldberg, P. K., & Patrinos, H. A. (2021). Measuring human capital using global learning data. *Nature*, 592.
7. OECD. (2024). *Education at a Glance 2024*. https://doi.org/10.1787/c00cad36-en
8. Mullis, I. V. S., et al. (2023). *PIRLS 2021 International Results in Reading*. Boston College.
9. UNESCO. (2020). *Global Education Monitoring Report 2020: Inclusion and Education*.
10. Barro, R. J., & Lee, J. W. (2013). A new data set of educational attainment in the world, 1950–2010. *Journal of Development Economics*, 104.

---

## ⚡ Regras de ouro para Claude Code

Estas regras devem ser seguidas em TODA sessão:

1. **Leia este CLAUDE.md antes de qualquer tarefa**
2. **Nunca pule fases** do roadmap — construa camada por camada
3. **Commits atômicos** — uma feature funcional por commit
4. **Testes ANTES do código** quando razoável (TDD)
5. **Documente decisões arquiteturais** em `docs/adrs/` quando desviar do plano
6. **Peça confirmação** antes de mudanças destrutivas (drop tabelas, delete arquivos)
7. **Use Plan Mode** para tarefas complexas — revise antes de executar
8. **Mantenha o docker-compose rodando** — se quebrar algo, restaure antes de continuar
9. **Atualize este CLAUDE.md** quando houver mudanças arquiteturais importantes
10. **Se tiver dúvida sobre metodologia** (especialmente plausible values), PAUSE e pergunte ao usuário

---

## 📝 Changelog

- **2026-04-23**: Versão inicial do CLAUDE.md. Arquitetura completa definida, roadmap de 6 fases, stack tecnológico confirmado.

---

*Este documento é a fonte de verdade do projeto. Qualquer desvio arquitetural significativo deve ser registrado aqui e em `docs/adrs/`.*
