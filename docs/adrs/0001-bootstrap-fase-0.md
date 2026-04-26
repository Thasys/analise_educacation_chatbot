# ADR 0001 — Bootstrap Fase 0

- **Status:** aceito
- **Data:** 2026-04-23
- **Fase:** 0 (Bootstrap)

## Contexto

A Fase 0 do roadmap (ver [`CLAUDE.md`](../../CLAUDE.md#fase-0--bootstrap-do-projeto-semana-1)) exige infraestrutura mínima funcional: `docker compose up` deve subir Prefect, FastAPI, frontend Next.js e Postgres sem erros.

## Decisões

1. **`docker-compose.yml` na raiz** — um único compose para todos os serviços. Evita fragmentação e simplifica `docker compose up`.
2. **Postgres 16-alpine como backend único** — serve metadados da aplicação *e* o Prefect (em bancos separados). Reduz complexidade operacional na Fase 0.
3. **Prefect 3 rodando via imagem oficial `prefecthq/prefect:3-latest`**, com `prefect server start`. Backend apontado para o Postgres via `PREFECT_API_DATABASE_CONNECTION_URL`.
4. **FastAPI com `uvicorn --reload`** e bind-mount de `api/src` — hot reload durante desenvolvimento. Em produção será trocado por Gunicorn + UvicornWorker.
5. **Frontend Next.js 14 minimalista** — scaffold manual (não `create-next-app`) para manter o bootstrap offline-friendly. Tailwind/shadcn/ui entram na Fase 6.
6. **Virtualenv por serviço** (`api/`, `data_pipeline/`, `agents/`) — dependências isoladas evitam conflitos (ex.: CrewAI e FastAPI podem exigir versões diferentes de Pydantic). Consistente com a especificação do CLAUDE.md.
7. **Nenhum serviço R/dbt/OpenMetadata/Langfuse no compose da Fase 0** — esses entram nas fases específicas (Fase 1 para R, Fase 2 para dbt, Fase 3 para OpenMetadata, Fase 5 para Langfuse).
8. **Volumes Docker nomeados para estado** (`edu_postgres_data`, `edu_prefect_data`) — `docker compose down` preserva dados; `docker compose down -v` limpa tudo.
9. **`data/` bind-mounted em `api`** — a API precisará ler DuckDB a partir da Fase 4, então o mount já está preparado.

## Alternativas consideradas

- **Rodar Prefect com SQLite**: descartado. Em produção é ruim, e manter a paridade dev/prod vale o custo extra de um banco Postgres.
- **Fazer scaffold do Next.js via `npx create-next-app` dentro do container no build**: descartado. Scaffold determinístico e versionado no Git é mais reprodutível.
- **Usar Nginx em vez de Caddy**: Caddy foi mantido conforme CLAUDE.md (HTTPS automático, config declarativa). Entra em jogo só na Fase 6.

## Consequências

- **Positivas:** `docker compose up` funciona out-of-the-box após `cp .env.example .env`. Testes de smoke (`pytest` + `curl /api/health`) já cobrem o mínimo.
- **Negativas:** nenhum serviço tem ainda autenticação/TLS. Aceitável até a Fase 6.
- **Débitos técnicos registrados:**
  - Substituir uvicorn `--reload` por Gunicorn em produção (Fase 4)
  - Adicionar Langfuse, OpenMetadata, ChromaDB no compose conforme fases avançam
  - Mover CLAUDE.md, data-sources.md para ChromaDB RAG quando disponível (Fase 5)
