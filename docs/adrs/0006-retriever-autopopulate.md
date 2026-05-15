# ADR 0006 — Auto-populate determinístico do `primary_data` no Retriever

- **Status:** aceito
- **Data:** 2026-05-16
- **Fase:** pós-Fase 6 (operação)

## Contexto

O Retriever Agent ([`agents/src/agents/retriever.py`](../../agents/src/agents/retriever.py))
recebe a pergunta + entidades extraídas e:
1. Escolhe a tool apropriada (`data_compare`, `data_timeseries`, `data_ranking`, `data_catalog`).
2. Chama a tool com argumentos derivados.
3. **Deve copiar** o resultado da tool (`{"ok": true, "data": [...], "meta": {...}}`)
   para os campos `primary_data` e `primary_meta` do output Pydantic `RetrievedData`.

Em testes live com `qwen2.5:14b` (provider Ollama — ADR 0005), o passo 3
**falha consistentemente**: o LLM chama a tool corretamente
(`tool_calls=1`, `rows_returned=3`), mas devolve `primary_data: []`.

Tentativa de mitigar via prompt — adicionando exemplo concreto passo-a-passo
+ regras "PROIBIDO deixar `primary_data: []` quando `rows_returned > 0`" —
**não funcionou**. O modelo simplesmente não reproduz arrays JSON grandes
no output estruturado.

Como o `Statistician` e o `Synthesizer` dependem de `primary_data`, isso
deriva em respostas tipo *"dados ausentes para o indicador GASTO_EDU_PIB"*
mesmo quando o gateway retornou 3 rows corretas.

## Decisão

**Pós-processamento determinístico em [`analysis_crew._autopopulate_primary_data`](../../agents/src/crews/analysis_crew.py)**:

Após o LLM produzir o `RetrievedData`, se `primary_data` está vazio mas
`tool_calls` registra uma tool bem-sucedida, **re-executar a tool**
diretamente via `EduGatewayClient` em Python e popular `primary_data` /
`primary_meta` com o resultado real.

```python
if not retrieved.primary_data and retrieved.tool_calls:
    retrieved = _autopopulate_primary_data(retrieved, gateway_client)
```

O helper procura a primeira `tool_call` com `status="ok"`, reconstrói os
args via schema Pydantic (`CompareArgs`, `TimeseriesArgs`, `RankingArgs`)
e chama `client.{compare|timeseries|ranking}(args)` — o mesmo método que
a tool CrewAI usa por trás.

## Alternativas consideradas

1. **Trocar para modelo maior só no Retriever** (ex.: `qwen2.5:32b`) — testes
   mostraram que o problema é estrutural (cópia de arrays no output JSON),
   não de capacidade. `qwen2.5:32b` no Synthesizer também tem dificuldade
   similar quando o array é grande, embora menos pronunciada.

2. **Hooks do CrewAI para capturar tool output** — CrewAI 1.x não expõe
   um caminho limpo para "interceptar o tool result entre execução e
   roteamento ao LLM seguinte". Seria mais frágil que pós-processar.

3. **Mudar o schema para tornar `primary_data` opcional / deduzir do
   gateway no Statistician** — duplica responsabilidade e quebra a
   convenção "RetrievedData é fonte única de verdade para a Analysis Crew".

4. **LLM como fact-correction loop** — pedir ao LLM "complete o `primary_data`
   com base no tool output" custa +1 chamada (~50s com qwen 14b) e ainda
   sujeito ao mesmo bug.

A opção escolhida custa **+1 HTTP local (<100 ms)** para um ganho de
correção 100%.

## Consequências

**Positivas:**
- Dados reais sempre chegam ao Statistician/Synthesizer.
- Custo determinístico mínimo (1 chamada HTTP local).
- Funciona com qualquer LLM, qualquer provider — não acopla ao modelo.

**Negativas:**
- Duplica trabalho: o LLM JÁ chamou a tool (via CrewAI runtime),
  e o Python re-executa. Em produção com Ollama isso é irrelevante (~100 ms
  vs ~1 min do LLM), mas com providers pagos por chamada de gateway custaria
  2× (negligível para nosso uso).
- Adiciona acoplamento entre `analysis_crew` e `EduGatewayClient` (antes só
  as tools tinham essa dependência).

**Débitos:**
- Se trocar de gateway (REST → gRPC, por exemplo), o helper precisa
  atualização. Acoplamento mitigado pela abstração `EduGatewayClient`.
- Modelos futuros podem corrigir o bug original. O auto-populate é
  idempotente (só dispara se `primary_data` está vazio), então não
  prejudica modelos que copiam corretamente — pode ficar.

## Como observar

Evento SSE `agent_done Retriever` agora inclui `primary_data_rows` e
`primary_meta_keys`. Em logs estruturados, procurar:

- `agents.retriever.autopopulated` — auto-populate rodou com sucesso.
- `agents.retriever.autopopulate_failed` — bug no helper (gateway down?).

Detalhe em [`docs/operations/monitoring-and-debugging.md`](../operations/monitoring-and-debugging.md).
