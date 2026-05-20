# Changelog

Todas as mudanças notáveis do projeto. Formato baseado em
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); versões usam
[SemVer](https://semver.org/spec/v2.0.0.html) — pré-1.0, breaking changes
podem aparecer em minor releases.

## [Não publicado]

### Added

- **2026-05-19** — Avaliação empírica EduQuery (Fases 1+2+3 do
  [plano-avaliacao-empirica.md](docs/evaluation/plano-avaliacao-empirica.md)):
  - Pacote `agents/evaluation/` com 84 itens golden (32 factuais + 22
    comparativos + 30 adversariais em 9 categorias), 5 métricas puras
    (`numeric_accuracy`, `doi_validity`, `source_coverage`,
    `hallucination_classifier`, `guardrails_efficacy`), 3 runners
    (baseline / eduquery / red_team) + `generate_paper_table.py`.
  - 89 unit tests dedicados (todos verdes), 216/216 testes na suite
    afetada.
  - **Refactor mínimo invasivo**: `master_flow.run_master(...,
    no_guardrails: bool = False)` + propagação para
    `_run_retriever`/`_run_citation`. Default `False`; só os runners
    de baseline ativam a flag.
  - Limitações descobertas e documentadas em
    [`docs/evaluation/limitations.md`](docs/evaluation/limitations.md):
    PISA fora dos marts (`plausible_values_pending`), incompatibilidade
    Gemini × CrewAI Flow, n=1 por prazo SBIE 2026-05-20.
- **2026-05-16** — Reorganização da documentação ([D1-D4 de docs](docs/refactor/dry-pass-2026-05.md)):
  - `docs/operations/` com 4 guias vivos: running-the-system, data-pipeline,
    models-and-providers, monitoring-and-debugging.
  - `docs/architecture/layers.md`, `agents.md`, `frontend.md` (Mermaid)
    substituindo o consumo direto dos `.jsx`.
  - ADRs 0005-0008 cobrindo decisões pós-Fase 6.
  - `docs/archive/` para fases históricas e runs antigos.
- **2026-05-16** — Auto-populate determinístico do `primary_data` no Retriever
  ([ADR 0006](docs/adrs/0006-retriever-autopopulate.md)). Resolve bug do
  `qwen2.5:14b` que chama a tool mas não copia rows para o output.
- **2026-05-15** — Fact Checker pós-Synthesizer ([ADR 0007](docs/adrs/0007-fact-checker-post-synthesis.md)).
  Validador determinístico (regex + tolerância 5%) + retry 1× do Synthesizer
  com lista de divergências. Warning visível se falhar.
- **2026-05-15** — Provider Ollama com Qwen 2.5 ([ADR 0005](docs/adrs/0005-ollama-qwen-provider.md))
  — smart `qwen2.5:32b`, fast `qwen2.5:14b`. Substitui `mistral-nemo:12b`
  para eliminar alucinação numérica.
- **2026-05-14** — DRY refactor pass A+B+C ([ADR 0008](docs/adrs/0008-dry-refactor-pass.md)):
  10 padrões duplicados consolidados em helpers (`SafeTool`, `_EndpointTool`,
  `make_agent`, `run_single_agent_task`, `parse_period`, `build_data_response`,
  `WorkspaceShell`, `DoiLink`, `instantiate_with_shared_client`).
- **2026-05-14** — Quality assessment documentado em
  [`docs/quality-assessment-2026-05-14.md`](docs/quality-assessment-2026-05-14.md).
  Identificou alucinação, DOIs falsos, gráficos quebrados — base para todos
  os guardrails adicionados depois.
- **2026-05-14** — Guardrails determinísticos pós-LLM:
  - `_validate_figure` em viz_tools (QW1) — rejeita Plotly com `x`/`y` strings.
  - `is_real_doi` em rag_tools (QW3) — rejeita DOIs `10.xxxx/...`.
  - QW4: Citation Agent honesto quando RAG vazio.
  - QW5: Statistician recebe `precomputed_metrics` do mart Gold.

### Changed

- **2026-05-16** — Docstrings de código limpas: referências históricas
  `Sprint X.Y` substituídas por links para ADRs ou removidas (39 ocorrências
  em Python + TS).
- **2026-05-16** — README.md reescrito para refletir estado atual do sistema
  (era ainda da Fase 0 Bootstrap).
- **2026-05-13** — Container `agents-server` adicionado ao docker-compose
  (porta 8001, separado do `api/`). Detalhe em
  [`docs/archive/runs/2026-05-13-docker-up.md`](docs/archive/runs/2026-05-13-docker-up.md).

### Fixed

- **2026-05-14** — Restaurada validação `min_length=3` em `RAGSearchArgs.query`
  e validações análogas em `CompareArgs.countries` e `ComputeStatsArgs.values`.
  Validações tinham sido removidas do schema Pydantic (compat GBNF Ollama)
  mas o código antigo não substituiu por checks dentro de `_run`.

---

## Histórico de fases (Fase 0 → Fase 6)

Cronologia de desenvolvimento original — detalhes em
[`docs/archive/phases/`](docs/archive/phases/).

### Fase 6 — Frontend Next.js 14 (2026-05-06)

Workspace 3 colunas (Sidebar + Workspace + ContextPanel) em `/compare`,
`/explorer`, `/library`. Streaming SSE via `agents-server:8001` + Plotly
lazy + DOIs clicáveis. 86 testes (77 vitest + 9 Playwright). Caddy
reverse proxy `:8443` para single origin. ADR 0004.

### Fase 5 — Sistema de agentes CrewAI (2026-04-30)

8 agentes em 4 crews (Core/Analysis/Synthesis/Master), 10 tools, RAG
ChromaDB com 25 papers seed, CLI dev. 119 testes mock + 2 live opt-in.
ADR 0003.

### Fase 4 — FastAPI Gateway

Endpoints `/api/data/{catalog,timeseries,compare,ranking}` consultando
DuckDB. Pydantic v2, SlowAPI rate limiting, structlog JSON.

### Fase 3 — Gold Layer

5 marts dbt analíticos: `mart_br_vs_ocde__*`, `mart_alfabetizacao__*`,
`mart_indicadores__rankings_recente`, `mart_gasto_x_alfabetizacao__*`,
`mart_br__evolucao_indicadores`.

### Fase 2 — Silver Layer + dbt

dbt Core + adapter dbt-duckdb. Staging + intermediate models. ISO-3
+ ISCED 2011. 137 testes dbt. ADR 0002.

### Fase 1 — Bronze Layer

7 coletores REST: WB, UNESCO UIS, OECD SDMX, IPEA OData, CEPAL, IBGE
SIDRA, Eurostat. Parquet imutável em `data/bronze/<fonte>/<ano>/`.

### Fase 0 — Bootstrap (2026-04-23)

Estrutura base, Docker Compose, "hello world" em todas as camadas. ADR 0001.

---

## Como contribuir com este changelog

- Adicione entradas no topo, sob `[Não publicado]`.
- Use subseções: `Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security`.
- Data em formato ISO (`YYYY-MM-DD`).
- Linkar ADRs/docs relevantes em vez de copiar conteúdo.
- Ao cortar release, mover `[Não publicado]` para `[X.Y.Z] — YYYY-MM-DD`
  e criar novo bloco vazio em cima.
