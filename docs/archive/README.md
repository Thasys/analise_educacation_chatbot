# Archive — documentação histórica

Conteúdo arquivado a partir de **2026-05-16** (durante refactor de docs D1).
Mantido para auditoria e contexto histórico; **não consulte para entender o
sistema atual** — para isso, leia [`docs/operations/`](../operations/) e
[`docs/architecture/`](../architecture/).

## Estrutura

### `phases/`

Documentos de planejamento, progresso por sprint e fechamento das 6 fases
de desenvolvimento (Fase 0 — Bootstrap → Fase 6 — Frontend Next.js).
Cumpriram seu papel durante o desenvolvimento; hoje são logs históricos.

- `fase-N-analise.md`: planejamento da fase
- `fase-N-conclusao.md`: fechamento e estado entregue
- `fase-N-sprint-N.M-progresso.md`: log de cada sprint

Para reconstruir o que mudou ao longo do tempo, prefira [`CHANGELOG.md`](../../CHANGELOG.md).

### `runs/`

Logs de execuções específicas (smoke tests de docker compose, etc.).
Útil para reproduzir um setup pontual, mas substituível por documentação
viva em [`docs/operations/`](../operations/).
