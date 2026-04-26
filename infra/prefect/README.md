# Prefect — configurações do servidor

O servidor Prefect 3 sobe via `docker-compose.yml` com backend Postgres
(banco dedicado `prefect`, criado em [`../postgres/init.sql`](../postgres/init.sql)).

- **UI**: <http://localhost:4200>
- **API**: <http://localhost:4200/api>

## Deployments

Os flows Prefect ficam em [`../../data_pipeline/src/flows/`](../../data_pipeline/src/flows/)
e serão registrados a partir da Fase 1 usando `prefect deploy`.

## Work pool (a criar na Fase 1)

```bash
# Após data_pipeline estar configurado:
prefect work-pool create --type process "default-agent-pool"
```
