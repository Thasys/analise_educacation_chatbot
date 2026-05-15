# CLAUDE.md — Guia mestre do projeto

> **Sistema de Análise Comparada Brasil × Internacional em Educação Básica**
> Documento de contexto permanente para sessões com Claude Code.
> **Versão enxuta — 2026-05-16.** Versão original arquivada em
> [`docs/archive/CLAUDE-original-2026-05-16.md`](docs/archive/CLAUDE-original-2026-05-16.md).

## Identidade

Sistema acadêmico que combina **Data Lakehouse educacional**, **multi-agente
CrewAI**, e **frontend Next.js 14** para responder:

> **"Como a educação básica brasileira se compara à educação dos países
> desenvolvidos?"**

100% open source, on-premise. Dados de 7 fontes oficiais (WB, UNESCO, OECD,
IPEA, CEPAL, IBGE, Eurostat) em 5 marts Gold consultados por 8 agentes LLM
que produzem markdown + Plotly + citações DOI adaptadas ao perfil do usuário.

## Princípios inegociáveis

1. **Rigor acadêmico acima de velocidade**
2. **Reprodutibilidade total** — toda transformação versionada; dbt obrigatório
3. **Imutabilidade da Bronze** — dados brutos nunca alterados
4. **Plausible Values corretos** — PISA/TIMSS/PIRLS exigem BRR/Jackknife
5. **Transparência da fonte** — toda resposta mostra de onde vieram os dados
6. **Copyright e ética** — citar todas as fontes, respeitar licenças

Detalhe em [`docs/methodology.md`](docs/methodology.md).

## Documentação

Esta seção é o **mapa** — não duplica conteúdo, só aponta.

### Para começar

| Tarefa | Doc |
|---|---|
| Entender o sistema | [`README.md`](README.md) + [`docs/architecture/overview.md`](docs/architecture/overview.md) |
| Rodar localmente | [`docs/operations/running-the-system.md`](docs/operations/running-the-system.md) |
| Ver mudanças recentes | [`CHANGELOG.md`](CHANGELOG.md) |

### Aprofundar

| Domínio | Doc |
|---|---|
| Arquitetura por camada | [`docs/architecture/layers.md`](docs/architecture/layers.md) |
| Sistema de agentes | [`docs/architecture/agents.md`](docs/architecture/agents.md) |
| Frontend Next.js | [`docs/architecture/frontend.md`](docs/architecture/frontend.md) |
| Metodologia acadêmica | [`docs/methodology.md`](docs/methodology.md) |
| Convenções de código | [`docs/conventions.md`](docs/conventions.md) |
| Decisões arquiteturais | [`docs/adrs/`](docs/adrs/) — 8 ADRs |
| 40+ bases catalogadas | [`docs/references/data-sources.md`](docs/references/data-sources.md) |

### Operações do dia a dia

| Necessidade | Doc |
|---|---|
| Subir/derrubar containers | [`docs/operations/running-the-system.md`](docs/operations/running-the-system.md) |
| Recolher dados + dbt build | [`docs/operations/data-pipeline.md`](docs/operations/data-pipeline.md) |
| Trocar de modelo LLM | [`docs/operations/models-and-providers.md`](docs/operations/models-and-providers.md) |
| Debugar quando algo falha | [`docs/operations/monitoring-and-debugging.md`](docs/operations/monitoring-and-debugging.md) |

## Regras de ouro para sessões com Claude Code

1. **Leia primeiro o doc certo** — este arquivo é entry point; aprofunde no
   `docs/` apropriado conforme a tarefa.
2. **Nunca pule fases do roadmap original** — código incremental por camada.
3. **Commits atômicos** — uma feature funcional por commit (Conventional
   Commits).
4. **Testes ANTES do código** quando razoável (TDD).
5. **Documente decisões arquiteturais** em `docs/adrs/` quando desviar do
   plano. Padrão em [`docs/conventions.md`](docs/conventions.md#quando-criar-uma-adr).
6. **Peça confirmação** antes de mudanças destrutivas (drop tabelas, delete
   arquivos, force-push, mudança de modelo LLM).
7. **Use Plan Mode** para tarefas complexas — revise antes de executar.
8. **Mantenha o docker-compose rodando** — se quebrar algo, restaure antes
   de continuar.
9. **Atualize o `CHANGELOG.md`** em mudanças relevantes — não polua
   docstrings com histórico.
10. **Se tiver dúvida sobre metodologia** (especialmente plausible values),
    PAUSE e pergunte ao usuário.

## Estrutura de diretórios (resumo)

```
.
├── CLAUDE.md ← você está aqui
├── CHANGELOG.md
├── README.md
├── docker-compose.yml
├── .env.example
│
├── api/                # FastAPI gateway (camada 5)
├── agents/             # CrewAI multi-agente (camada 4)
├── data_pipeline/      # Coletores Prefect (camadas 1-2)
├── dbt_project/        # Transformações SQL (camada 3)
├── frontend/           # Next.js 14 (camada 6)
├── r_scripts/          # PISA/TIMSS/PIRLS — plausible values
├── infra/              # Postgres, Prefect, Caddy
│
├── docs/
│   ├── architecture/   # overview + layers + agents + frontend
│   ├── operations/     # running, pipeline, models, debugging
│   ├── methodology.md
│   ├── conventions.md
│   ├── adrs/           # 8 ADRs
│   ├── refactor/       # análises DRY recentes
│   ├── references/     # data-sources.md
│   ├── quality-assessment-*.md
│   └── archive/        # histórico das 6 fases + runs antigos
│
└── data/               # NÃO versionado
    ├── bronze/         # raw imutável
    ├── duckdb/         # education.duckdb (Silver + Gold)
    └── chromadb/       # vector store RAG
```

Estrutura completa em [`README.md`](README.md#estrutura-do-projeto).

---

*Este documento é fino por design. Conteúdo detalhado vive em
[`docs/`](docs/). Qualquer mudança arquitetural significativa deve ser
registrada em uma ADR nova e mencionada no [`CHANGELOG.md`](CHANGELOG.md).*
