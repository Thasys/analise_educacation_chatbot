# Convenções de desenvolvimento

## Python

- **Versão:** 3.11+ (containers usam 3.13 via uv)
- **Formatter/Linter:** [`ruff`](https://docs.astral.sh/ruff/) (substitui black + flake8 + isort)
- **Type checking:** `mypy` em modo strict para módulos novos
- **Docstrings:** Google style. Foco em **WHY > WHAT** (ver seção abaixo)
- **Testes:** `pytest` + `pytest-cov` (mínimo 70% em módulos críticos)
- **Dependências:** `uv` (mais rápido que pip) ou `poetry`
- **Virtualenv:** uma por serviço (`data_pipeline`, `api`, `agents`)

### Docstrings — padrão WHY > WHAT

❌ **Evitar** (o que o código já diz):
```python
def parse_period(period: str | int | None) -> tuple[int | None, int | None]:
    """Converte um valor de periodo em uma tupla (start, end)."""
```

❌ **Evitar** (jargão histórico que polui):
```python
def build_comparativist():
    """Sprint 5.5: ganhou RAGSearchTool. Sprint 5.6 vai paralelizar."""
```

✅ **Preferir** (o porquê das escolhas não-óbvias):
```python
def parse_period(period: str | int | None) -> tuple[int | None, int | None]:
    """Parsing canônico de períodos dos 5 coletores REST.

    Centraliza a lógica que estava duplicada (DRY #8 do refactor pass).
    Aceita "YYYY" / "YYYY-YYYY" / "all" / None.
    """
```

✅ **Quando referenciar contexto histórico**, linkar ADR:
```python
def _autopopulate_primary_data(retrieved, gateway_client):
    """Workaround para qwen2.5:14b não copiar arrays de tools.

    Ver ADR 0006 para o porquê. Helper idempotente — só dispara
    quando primary_data está vazio.
    """
```

## TypeScript / Next.js

- **Modo strict:** `true`
- **Linter:** `eslint` + `prettier`
- **Imports:** absolutos com alias `@/`
- **Componentes:** Server Components por padrão; Client Components apenas
  com `"use client"` quando necessário (interação, estado)
- **Estado global:** Zustand; local: `useState`
- **Data fetching:** TanStack Query no cliente; `fetch` direto em Server
  Components
- **Testes:** Vitest (unit) + Playwright (E2E)

### Convenções de componente

- Um componente por arquivo em `frontend/components/<dominio>/`.
- Hook customizado em `frontend/lib/hooks/`.
- Store Zustand em `frontend/lib/stores/`.
- Utilidades puras em `frontend/lib/utils/`.

## Git

- **Branches:** `main` (estável), `dev` (integração), `feature/<descricao>` (trabalho)
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`)
- **PRs:** mesmo sendo solo, usar PRs com revisão (Claude Code, code-reviewer agent)
- **Tags:** versionamento semântico (`v0.1.0`, etc.) — atualmente pré-1.0

### Commit subject

- Máximo 70 caracteres.
- Imperativo: "adicionar feature X", não "adicionado feature X".
- Em português ou inglês — consistente dentro de uma branch.

### CHANGELOG

Atualizado a cada release no [`CHANGELOG.md`](../CHANGELOG.md) raiz.
Entradas mais recentes no topo.

## SQL (dbt / DuckDB)

- **Estilo:** SQLFluff com dialeto DuckDB
- **Nomes:** `snake_case` para tabelas e colunas
- **CTEs:** sempre nomeadas, nunca aninhadas profundamente
- **Comentários:** obrigatórios em modelos de mart
- **Testes dbt:**
  - Toda tabela Gold tem `not_null` em chaves primárias
  - Toda métrica tem teste de range plausível
  - Todo modelo tem descrição no `schema.yml`

### Padrão de nomenclatura dbt

```
stg_<fonte>__<dataset>        # staging (1:1 com Bronze)
int_<dominio>__<topico>       # intermediate (Silver)
mart_<area>__<analise>        # marts (Gold)
```

## Segurança

- **Segredos:** nunca no Git. Usar `.env` + `direnv` (opcional)
- **API keys LLM:** em `.env`, nunca hardcoded
- **Logs:** redação de PII e tokens via `structlog` processors
- **CORS:** lista explícita de origens em `AGENTS_CORS_ORIGINS` /
  `API_CORS_ORIGINS`

## Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files   # executar em todo o repo
```

Hooks ativos (`.pre-commit-config.yaml`):
- `ruff` (lint + format Python)
- `prettier` (JS/TS/MD/YAML)
- Detecção de chaves privadas
- Whitespace trailing / final-of-file
- Tamanho de arquivos grandes

## Organização de testes

### Python

```
agents/tests/
├── conftest.py              # fixtures compartilhadas (mock_llm_call, etc.)
├── tools/                   # testes unitários de tools
├── agents/                  # testes de agents + crews
├── server/                  # mini-server FastAPI
├── rag/                     # ChromaDB ingest + search
└── e2e/                     # opcional, `pytest -m e2e`
```

Markers:
- `@pytest.mark.live` — exige `ANTHROPIC_API_KEY` ou Ollama up
- `@pytest.mark.integration` — toca APIs externas
- `@pytest.mark.slow` — pula em CI rápido

### Frontend

```
frontend/tests/
├── unit/                    # vitest (jsdom)
└── e2e/                     # playwright
```

## Quando criar uma ADR

Crie em `docs/adrs/000N-<slug>.md` quando:
- Decisão arquitetural com trade-off não-trivial.
- Mudança de tecnologia (provider LLM, banco, framework).
- Workaround estrutural (não cosmético).
- Convenção que afeta múltiplos serviços.

Template em [`adrs/0001-bootstrap-fase-0.md`](adrs/0001-bootstrap-fase-0.md):
contexto, decisão, alternativas, consequências, links.

## Quando NÃO criar comentário

- O código já diz: deletar.
- Histórico de quando foi feito: vai pro CHANGELOG.
- TODO sem contexto: prefira issue do tracker.
- "Hack" sem explicação: ou justifica ou refatora.
