# OpenMetadata — Catálogo de dados (planejado)

Esta pasta é um stub para integração futura com **OpenMetadata** como
catálogo de dados navegável apontando para o DuckDB do projeto.

## Status

⚠️ **Não configurado** — placeholder para Fase 3.5+. Atualmente o
catálogo é navegado via `dbt docs serve`, suficiente até o lançamento
da Camada 5 (agentes CrewAI).

## Quando configurar

Configure OpenMetadata quando:
1. Camada 5 (agentes CrewAI) começar — eles precisam de catálogo
   programático para descobrir indicadores e suas semânticas.
2. Mais de 2 desenvolvedores entrarem no projeto — OpenMetadata
   fornece UI de descoberta.
3. Houver dashboards (BI ou Streamlit) consumindo marts — facilita
   debugging via lineage.

## Setup mínimo proposto

### Via Docker Compose (recomendado para on-premise)

Adicionar ao [`docker-compose.yml`](../../docker-compose.yml) raiz do
projeto:

```yaml
services:
  openmetadata:
    image: openmetadata/server:latest
    ports:
      - "8585:8585"
    depends_on:
      - postgres
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_USER: ${POSTGRES_USER}
      DB_PASSWORD: ${POSTGRES_PASSWORD}
      DB_DATABASE: openmetadata_db
      ELASTICSEARCH_HOST: elasticsearch
    volumes:
      - om_data:/opt/openmetadata
```

E criar o database `openmetadata_db` no Postgres existente.

### Conector DuckDB

OpenMetadata tem conector nativo para DuckDB desde v1.4. Cadastrar via
UI ou via Python SDK:

```python
from metadata.workflow.metadata import MetadataWorkflow

config = {
    "source": {
        "type": "duckdb",
        "serviceName": "education_duckdb",
        "serviceConnection": {
            "config": {
                "type": "Duckdb",
                "databaseName": "education",
                "databaseUri": "/data/duckdb/education.duckdb",
            }
        },
        "sourceConfig": {"config": {"type": "DatabaseMetadata"}},
    },
    # ...
}
workflow = MetadataWorkflow.create(config)
workflow.execute()
```

### Lineage do dbt

Importar `target/manifest.json` do dbt como source de lineage. Após
qualquer `dbt run`, executar:

```bash
metadata ingest -c openmetadata-dbt-config.yml
```

Onde o YAML aponta para `dbt_project/target/manifest.json` e
`run_results.json`. Resultado: lineage Bronze → Silver → Gold visível
no UI do OpenMetadata.

### Glossário e termos

OpenMetadata permite criar Glossary terms apontando para colunas. Útil
para que agentes CrewAI saibam:
- "GASTO_EDU_PIB" → glossary term "Gasto público em educação como % do PIB"
- "country_iso3" → glossary term "ISO-3166 alpha-3 country code"

## Alternativa intermediária: dbt docs serve

Enquanto OpenMetadata não estiver configurado:

```bash
cd dbt_project
DBT_PROFILES_DIR=. dbt docs generate
DBT_PROFILES_DIR=. dbt docs serve --port 8081
```

Acessar em [http://localhost:8081](http://localhost:8081). Lineage
HTML navegável com descrições de modelo e coluna. Cobre 80% do uso
de catálogo até OpenMetadata estar pronto.

## Referências

- [OpenMetadata DuckDB connector docs](https://docs.open-metadata.org/connectors/database/duckdb)
- [dbt connector docs](https://docs.open-metadata.org/connectors/ingestion/workflows/metadata/dbt)
- ADR planejado: `docs/adrs/0003-openmetadata-integration.md` (a criar)
