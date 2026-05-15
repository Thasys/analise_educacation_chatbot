# Data pipeline — Bronze → Silver → Gold + RAG

O sistema usa padrão **Medallion** (Bronze raw → Silver clean → Gold analytical)
implementado em `data_pipeline/` (coletores Prefect) + `dbt_project/`
(transformações SQL).

## Visão geral

```
Coletores Python (Prefect)  →  data/bronze/<fonte>/<ano>/*.parquet
                                              ↓
                              dbt build (staging → intermediate → marts)
                                              ↓
                              data/duckdb/education.duckdb
                              schemas:
                                main_staging      (1:1 Bronze tipado)
                                main_intermediate (Silver)
                                main_marts        (Gold — consumido por /api/data/*)
```

## Estado atual

| Camada | Local | Conteúdo |
|---|---|---|
| Bronze | `data/bronze/<fonte>/` | 7 fontes (cepalstat, eurostat, ibge, ipea, oecd, unesco, worldbank) |
| Silver | DuckDB `main_intermediate` | ~5,3k linhas em 5 tabelas |
| Gold | DuckDB `main_marts` | 1.182 linhas em 5 marts |

## Recoletar Bronze (Prefect)

```bash
# Container on-demand:
docker compose --profile tools run --rm data_pipeline \
  python -m src.flows.<fonte>

# Exemplos por fonte:
docker compose --profile tools run --rm data_pipeline python -m src.flows.worldbank
docker compose --profile tools run --rm data_pipeline python -m src.flows.unesco
docker compose --profile tools run --rm data_pipeline python -m src.flows.ibge_sidra
```

Coletores escrevem em `data/bronze/<fonte>/<ano>/*.parquet`. Operação
idempotente — re-execução não duplica.

## Rodar `dbt build` (Silver + Gold)

```bash
docker compose --profile tools run --rm -w /dbt data_pipeline \
  dbt build --profiles-dir . --project-dir .
```

Tempo: ~30-60s. Executa em sequência:
1. `staging/` (1:1 com Bronze, tipagem)
2. `intermediate/` (Silver: joins, ISCED, ISO-3)
3. `marts/` (Gold: tabelas analíticas)
4. Roda **todos** os 137 testes dbt (`not_null`, `unique`, ranges plausíveis)

Para rodar só uma camada:

```bash
# Apenas marts:
docker compose --profile tools run --rm -w /dbt data_pipeline \
  dbt run --select marts

# Apenas testes:
docker compose --profile tools run --rm -w /dbt data_pipeline \
  dbt test
```

## Marts publicados (Gold)

| Mart | Linhas | Função |
|---|---|---|
| `mart_br_vs_ocde__gasto_educacao_timeseries` | 491 | Brasil + 38 OCDE em gasto edu (% PIB), 2010-2023, com zscore/percentile/gap |
| `mart_alfabetizacao__latam_2020s` | 38 | Alfabetização 15+ Brasil + LATAM, 2020-2024 |
| `mart_indicadores__rankings_recente` | 135 | Rankings cross-indicador no ano mais coberto |
| `mart_gasto_x_alfabetizacao__correlacao` | 392 | Cruzamento gasto×alfab com efficiency_ratio |
| `mart_br__evolucao_indicadores` | 126 | Trajetória completa do Brasil em todos os indicadores Silver |

Ver descrições e schemas: `dbt_project/models/marts/schema.yml` ou
`curl http://localhost:8000/api/data/catalog | jq`.

## Popular o RAG (uma vez)

```bash
docker compose run --rm agents-server python -c "
from src.rag.ingest import ingest_manifest
print(ingest_manifest('/app/src/rag/seeds/manifest.yaml'))
"
```

Manifest atual: 25 papers seed (Hanushek, Carnoy, Schleicher, etc.) em
[`agents/src/rag/seeds/manifest.yaml`](../../agents/src/rag/seeds/manifest.yaml).
Persistido em `data/chromadb/edu_literature/`.

Para verificar:

```bash
docker compose exec agents-server python -c "
from src.rag.client import get_rag_client
print('docs:', get_rag_client().count())
"
```

## Adicionar nova fonte ou novo indicador

1. **Coletor Python** em `data_pipeline/src/collectors/<fonte>/` — herda de
   `BaseCollector` e implementa `build_url` + `parse_payload`. Use os helpers
   `_http_fetch_json` / `_http_fetch_paginated` da base.

2. **Staging dbt** em `dbt_project/models/staging/stg_<fonte>__<dataset>.sql` —
   tipagem + renomeação 1:1 com Bronze.

3. **Intermediate** em `dbt_project/models/intermediate/` — harmonização
   (ISO-3, ISCED 2011, etc.).

4. **Mart** em `dbt_project/models/marts/` — agregação analítica final
   com testes em `schema.yml`.

5. **Schema** atualizado em `api/src/schemas/common.py` + `agents/src/schemas.py`
   (espelhamento). Tipo `IndicatorId` ganha novo literal.

6. **Tool agent** se necessário em `agents/src/tools/` (geralmente reusa as 4
   existentes via parâmetros).

## Limpar e recomeçar

```bash
# Apaga apenas Silver/Gold (mantém Bronze):
docker compose --profile tools run --rm -w /dbt data_pipeline \
  dbt run-operation drop_main_schemas
# (ou: rm data/duckdb/education.duckdb && dbt build)

# Apaga RAG:
rm -rf data/chromadb/

# Apaga TUDO (cuidado):
docker compose down -v && rm -rf data/{bronze,silver,gold,chromadb,duckdb}
```
