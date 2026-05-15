# Monitoramento e debugging

## Logs estruturados

Todos os serviços Python usam **structlog** com saída JSON. Em desenvolvimento
saem coloridos no stdout do container.

```bash
docker compose logs -f api               # FastAPI gateway
docker compose logs -f agents-server     # CrewAI master flow
docker compose logs -f data_pipeline     # Prefect flows (quando rodando)
docker compose logs -f --tail 100 frontend
```

### Eventos-chave (structlog `event` field)

#### `api` (gateway FastAPI)

| Event | Significado |
|---|---|
| `agents.gateway.request` | HTTP recebido — `method`, `path`, `status`, `elapsed_ms`, `request_id` |

#### `agents-server` (master flow)

| Event | Significado |
|---|---|
| `agents.master_flow.start` | Pergunta recebida |
| `agents.master_flow.core_done` | Roteamento — `flow`, `profile`, `confidence` |
| `agents.master_flow.done` | Fim — `elapsed_s`, `markdown_len`, `n_citations`, `chart_type` |
| `agents.analysis_crew.retriever_done` | `primary_data_rows`, `primary_meta_keys`, `calls` ★ chave para debugar alucinação |
| `agents.retriever.autopopulated` | Auto-populate disparou — `tool`, `rows`, `meta_keys` |
| `agents.retriever.autopopulate_failed` | Auto-populate falhou — checar `error` |
| `agents.citation.rag_empty_skip` | QW4 disparou (RAG vazio) — citações puladas com nota honesta |
| `agents.citation.placeholders_filtered` | Guardrail `is_real_doi` removeu DOIs `10.xxxx/...` |
| `agents.master_flow.fact_check_failed` | Markdown teve >20% números divergentes — retry disparado |
| `agents.master_flow.fact_check_failed_after_retry` | Mesmo após retry, ainda inconsistente — warning visível |

## Eventos SSE em tempo real

Endpoint `POST /api/chat/stream` emite eventos a cada etapa. Útil para
observar o pipeline sem perder cold-start de modelos.

```bash
curl -N -X POST http://localhost:8001/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"question":"..."}' \
  | grep --line-buffered "^event:"
```

Sequência esperada (fluxo `data`):

```
flow_started
agent_started "Core (Orchestrator + Profiler)"
agent_done   (result: flow, profile, indicator, countries)
agent_started "Retriever"
agent_done   (tool_calls, primary_data_rows, primary_meta_keys)
agent_started "Statistician"
agent_done   (sample_size, method)
agent_started "Comparativist"
agent_done
agent_started "Citation"
agent_done   (items)
agent_started "Synthesis (Visualizer + Synthesizer)"
agent_done   (chart_type)
agent_started "Fact Checker"
agent_done   (is_consistent, divergences)
[opcional] agent_started/done "Synthesizer (retry)"
final_answer
```

## Diagnóstico por sintoma

### Sintoma: "resposta diz 'dados ausentes' mesmo com Gold populado"

1. Cheque o evento `agent_done Retriever`:
   ```
   primary_data_rows: 0     ← problema
   primary_data_rows: 3     ← OK
   ```
2. Se `0`, o LLM não copiou rows da tool. Deveria disparar auto-populate.
   Cheque logs:
   ```bash
   docker compose logs agents-server | grep "agents.retriever.autopopulate"
   ```
3. Se `autopopulate_failed` aparece: o gateway está respondendo? Teste:
   ```bash
   curl -X POST http://localhost:8000/api/data/compare \
     -H "Content-Type: application/json" \
     -d '{"indicator":"GASTO_EDU_PIB","countries":["BRA"],"year":2020,"source":"worldbank"}'
   ```

### Sintoma: "Citation Agent emite DOIs falsos"

1. Confira `items` no evento `agent_done Citation`:
   - `items: 0` → guardrail rejeitou tudo (RAG provavelmente vazio).
   - `items: N` → veja `citations` no `final_answer` payload.
2. Confira nota no `Citations.notes`:
   - `"N cita(coes) tiveram DOI placeholder removido"` → `is_real_doi`
     pegou DOIs `10.xxxx/...`.
   - `"RAG local vazio — citacoes nao disponiveis"` → QW4 disparou,
     RAG não populado. Veja [`data-pipeline.md`](data-pipeline.md#popular-o-rag).

### Sintoma: "fact-checker reprovou minha resposta"

Procure no payload:

```json
"warnings": [
  "Fact-check: 3 valores no markdown nao correspondem ao dado real (tolerancia 5%). Divergentes: 4.7, 5.3, 6.9. Trate como ilustrativo, nao final."
]
```

Significa: o Synthesizer alucinou ≥1 número e o retry também falhou.
Causa típica:
- Modelo `mistral-nemo:12b` — trocar para `qwen2.5:32b`.
- `primary_data` veio vazio (ver sintoma anterior).
- Tolerância de 5% muito apertada para arredondamentos legítimos —
  ajustar `max_divergence_ratio` em `agents/src/crews/_helpers.py:check_numeric_consistency`.

### Sintoma: agents-server demora 5+ min para responder

Normal com `qwen2.5:32b` em CPU offload — ver [`models-and-providers.md`](models-and-providers.md).
Para acelerar:
1. Modelo menor: `qwen2.5:14b` no smart também.
2. Ollama com GPU offload (CUDA/ROCm) se disponível.
3. Provider remoto (Anthropic, OpenAI) — incorre custo.

## Prefect UI

<http://localhost:4200> — dashboard dos flows de ingestão. Útil para
acompanhar runs de coleta, retries automáticos, status histórico.

## Adminer (Postgres)

<http://localhost:8080> — login com `POSTGRES_USER` / `POSTGRES_PASSWORD`
do `.env`. Inspeciona:
- Database `educacao_metadata` — logs de ingestão
- Database `prefect` — estado dos flows

## DuckDB shell

```bash
docker compose exec api duckdb /data/duckdb/education.duckdb

# Dentro do duckdb:
SHOW ALL TABLES;
SELECT * FROM main_marts.mart_br_vs_ocde__gasto_educacao_timeseries LIMIT 5;
```

## Telemetria desligada

Ambos `OTEL_SDK_DISABLED=true` e `CREWAI_DISABLE_TELEMETRY=true` em
`docker-compose.yml`. Mensagens "HTTPSConnectionPool: telemetry.crewai.com"
aparecem ocasionalmente — são tentativas de retry interno do SDK, **não**
afetam o pipeline e podem ser ignoradas.
