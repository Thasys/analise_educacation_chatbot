# Fase 5 — Sprint 5.6 (Master Flow + CLI + Suite Live) — Progresso

> Estado da Sprint 5.6 da Fase 5 (Sistema de agentes CrewAI).
> Complementa [`fase-5-analise.md`](./fase-5-analise.md) e
> [`fase-5-sprint-5.5-progresso.md`](./fase-5-sprint-5.5-progresso.md).
> **Data:** 2026-04-30
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Amarrar **todas** as crews da Fase 5 num orquestrador único e habilitar
duas formas de uso ponta-a-ponta:

- `run_master(question, *, gateway_client, rag_client) → FinalAnswer`
  rodando Core → (Analysis | placeholder simple) → Synthesis com
  citations populadas pelo Citation Agent.
- `python -m src.cli "<pergunta>"` para uso humano — imprime markdown
  formatado + sumario JSON de viz/citations/sources.
- `pytest -m live agents/tests/e2e/` opt-in para validar o pipeline com
  chamadas Anthropic reais (skipado por default).

---

## 2. Entregáveis

### 2.1 Arquivos novos

| Arquivo | Linhas | Descrição |
|---|---|---|
| `agents/src/crews/analysis_crew.py` | 165 | `run_analysis_flow(core, gateway_client, rag_client) → (RetrievedData, StatAnalysis, ComparativeContext, Citations)` rodando 4 agentes em sequência (1 Crew/agente para mocks finos) |
| `agents/src/crews/master_flow.py` | 100 | `run_master(question)` orquestrando Core → (Analysis ou placeholder simple) → Synthesis; **acopla citations no FinalAnswer**; desabilita telemetria CrewAI por default |
| `agents/src/cli.py` | 130 | argparse `python -m src.cli "<q>" [--json-only] [--gateway URL]`; valida `has_anthropic_key`; pretty print markdown + refs + warnings + follow-ups |
| `agents/tests/agents/test_analysis_crew.py` | 175 | 2 testes (data flow + plausible_values_pending para PISA) |
| `agents/tests/agents/test_master_flow.py` | 240 | 3 testes (data flow completo, simple flow pula data agents, citations vêm do Citation Agent não do Synthesizer) |
| `agents/tests/test_cli.py` | 105 | 4 testes (sucesso, json-only, sem API key, exception handling) |
| `agents/tests/e2e/test_master_flow_live.py` | 100 | 2 testes `@pytest.mark.live` (skipados por default) — 1 data flow + 1 simple flow com Anthropic real |

### 2.2 Edições

| Arquivo | Mudança |
|---|---|
| `agents/src/crews/__init__.py` | +exports `run_analysis_flow`, `run_master` |
| `agents/src/logging_config.py` | logs em `sys.__stderr__` (não stdout, e usa `__stderr__` para sobreviver capsys do pytest); evitar mistura com saída JSON do CLI |
| `agents/pyproject.toml` | filter `Remove format_exc_info` warning do structlog |

**Total Sprint 5.6: ~915 linhas Python (src + tests).**

---

## 3. Decisões aplicadas

### 3.1 ✅ 4 Crews separadas no Analysis (não 1 Crew com 4 tasks)

`run_analysis_flow` roda Retriever, Statistician, Comparativist e
Citation cada um em sua **própria** Crew de 1 agente + 1 task.
Vantagens vs uma Crew única com 4 tasks encadeadas via `task.context`:

- **Mock por agente** funciona sem ginástica — basta `mock_llm_call`
  com `by_role`.
- **Trace por etapa** em Langfuse (Sprint 5.6+ se ligado).
- **Failover granular** — falha de uma etapa não trava as outras (no
  Sprint 5.6 mantemos sequencial, mas a estrutura permite retry/skip).

Custo: ~4 invocações de `Crew.kickoff()` em vez de 1, mas overhead
desprezível vs latência das chamadas LLM.

### 3.2 ✅ Master flow roteia por `IntentDecision.flow`

- `simple` → pula Retriever + Statistician (placeholders vazios), roda
  apenas Comparativist + Citation + Synthesis. Validado via
  `mock_llm_call` que **não configura** roles do Retriever/Statistician
  e **não falha** (fixture levanta `AssertionError` se chamados).
- `data` / `deep` → caminho completo. Sprint 5.6 trata `deep` igual a
  `data`; iteração extra via RAG fica para Sprint 5+.

### 3.3 ✅ `final.citations` vem do Citation Agent, não do Synthesizer

Decisão de fonte única de verdade: o `Citation` schema só pode aparecer
na saída via Citation Agent. O Synthesizer pode (e nos testes mocks
faz) preencher `citations=[...]` no `FinalAnswer`, mas o `master_flow`
**sobrescreve** com `citations.items` do Citation Agent. Validado em
`test_master_flow_citations_come_from_citation_agent`.

Por quê: garante que toda DOI no markdown final foi validada pelo
Citation Agent contra o RAG (`cite_resolve` + `rag_search`). Synthesizer
nunca pode injetar DOI alucinado.

### 3.4 ✅ Telemetria CrewAI desabilitada por default

`run_master` faz `os.environ.setdefault("OTEL_SDK_DISABLED", "true")` e
`os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")`. Evita
tráfego PostHog não autorizado num projeto acadêmico. Pode ser
sobrescrito explicitamente via env var pré-definida.

### 3.5 ✅ Logs em `sys.__stderr__` (não `sys.stderr`)

Descoberto durante o Sprint: `structlog.PrintLoggerFactory(file=sys.stderr)`
captura referência ao `sys.stderr` do momento da configuração. pytest
substitui esse handle por test (capsys) e o fecha — gerando
`ValueError: I/O operation on closed file` em testes seguintes. Solução:
usar `sys.__stderr__` que aponta para o stderr **original** do processo
e nunca é substituído.

Side effect intencional: `pytest -s` mostra logs do agente direto no
terminal (útil para debugging), e `--json-only` do CLI tem stdout limpo
para parsing.

### 3.6 ✅ Suite live opt-in com asserts SOFT

Marker `@pytest.mark.live` (registrado em `tests/conftest.py` desde
Sprint 5.0). Skip default; rodar com `pytest -m live`. 2 testes:

- `test_live_data_flow_returns_final_answer` — gateway via
  MockTransport (isola rede), LLM real Anthropic. Asserta:
  `flow_used in {data, deep}`, markdown ≥ 100 chars, ≥ 1 viz, latência
  ≤ 180s.
- `test_live_simple_flow_returns_conceptual_answer` — sem gateway, só
  RAG seed. Asserta: `flow_used in {simple, data}`, "ISCED" no markdown.

Asserts deliberadamente soft — LLM é não-determinístico. O objetivo é
validar que o pipeline atravessa sem exceção, não que retorna texto
exato.

### 3.7 ✅ CLI imprime markdown + metadata estruturada

`python -m src.cli "Como BR vs FIN em gasto 2022?"` imprime:

```
================================================================
# Resposta em markdown
...
================================================================

REFERENCIAS:
  - Hanushek, Woessmann (2011). Title. doi:10.1162/...

VISUALIZACAO: bar_vertical — Gasto 2020
  data points: 1
  sources: ['worldbank']

PARA APROFUNDAR:
  > Pergunta extra...

[meta] perfil=researcher fluxo=data sources=['worldbank']
```

Com `--json-only`, imprime apenas o JSON do `FinalAnswer` (com indent)
em stdout, logs em stderr — parseable por scripts ou pipe para `jq`.

---

## 4. Métricas finais

```
Linhas Python adicionadas:     ~915 (src + tests Sprint 5.6)
Testes pytest TOTAL:           119 / 119 PASS (~80s) + 2 skipped (live opt-in)
Testes especificos Sprint 5.6: 9 / 9 PASS
  - analysis_crew: 2 testes (~5s)
  - master_flow: 3 testes (~5s)
  - cli: 4 testes (~3s)
  - live: 2 testes coletados, skipados sem flag -m live
Custo Anthropic:               $0.00 (LLM mockado)
```

Saída final do `pytest`:

```
tests/agents/test_analysis_crew.py ...... 2 PASSED
tests/agents/test_citation.py ........... 4 PASSED
tests/agents/test_master_flow.py ........ 3 PASSED
tests/agents/test_orchestrator_profiler.py 6 PASSED
tests/agents/test_retriever.py .......... 5 PASSED
tests/agents/test_statistician_comparativist.py 6 PASSED
tests/agents/test_visualizer_synthesizer.py 5 PASSED
tests/rag/test_rag_client_search.py ..... 17 PASSED
tests/test_api_client.py ................ 12 PASSED
tests/test_cli.py ....................... 4 PASSED
tests/test_config.py .................... 8 PASSED
tests/test_llm.py ....................... 5 PASSED
tests/tools/test_data_tools.py .......... 10 PASSED
tests/tools/test_rag_tools.py ........... 9 PASSED
tests/tools/test_stats_tools.py ......... 11 PASSED
tests/tools/test_viz_tools.py ........... 12 PASSED
================ 119 passed, 2 skipped in ~80s
```

---

## 5. Estrutura do `agents/` após Sprint 5.6

```
agents/
├── src/
│   ├── cli.py                  ✅ NOVO
│   ├── config.py
│   ├── logging_config.py        (logs em sys.__stderr__)
│   ├── api_client.py
│   ├── llm.py
│   ├── schemas.py
│   ├── agents/                  (8 agentes ja completos)
│   ├── prompts/                 (8 prompts)
│   ├── crews/
│   │   ├── core_crew.py
│   │   ├── analysis_crew.py    ✅ NOVO
│   │   ├── synthesis_crew.py
│   │   └── master_flow.py      ✅ NOVO
│   ├── tools/                   (4 grupos: data, stats, viz, rag)
│   └── rag/                     (client + ingest + search + 25 seeds)
└── tests/
    ├── agents/
    │   ├── ...
    │   ├── test_analysis_crew.py     ✅ NOVO
    │   └── test_master_flow.py       ✅ NOVO
    ├── e2e/
    │   └── test_master_flow_live.py  ✅ NOVO (opt-in)
    └── test_cli.py             ✅ NOVO
```

---

## 6. Como rodar

### 6.1 Suite completa (mock, default)

```bash
cd agents
.venv/Scripts/python -m pytest -q
# 119 passed, 2 skipped in ~80s
```

### 6.2 Suite live (Anthropic real, opt-in)

```bash
# Requer ANTHROPIC_API_KEY real no .env
cd agents
.venv/Scripts/python -m pytest -m live tests/e2e -v
# 2 testes; ~60-120s; custo ~$0.10-0.20
```

### 6.3 CLI ad-hoc

```bash
cd agents
.venv/Scripts/python -m src.cli "Como o Brasil se compara com a Finlandia em gasto educacional em 2020?"
# Imprime markdown formatado + refs + viz + meta no stdout
# Logs em stderr (filtraveis com 2>/dev/null)

.venv/Scripts/python -m src.cli "..." --json-only > resposta.json
# JSON puro em stdout, parseavel por jq/scripts
```

---

## 7. Próximo: Sprint 5.7 (Conclusão + ADR 0003)

Última sprint da Fase 5. Não adiciona código novo significativo —
finaliza a documentação e fecha a fase.

### 7.1 Entregáveis previstos

- `docs/adrs/0003-arquitetura-fastapi-crewai.md` — ADR consolidando
  decisões: separação api/agents (HTTP only), regra "tools chamam
  gateway" (R5 do plano), RAG embedded vs server, telemetria opt-out,
  routing por flow, citations sempre via Citation Agent.
- `docs/phases/fase-5-conclusao.md` — fechamento formal da Fase 5:
  métricas finais (8 sprints, ~5k linhas Python, 119 testes), insights
  por sprint, roadmap Fase 6 (frontend Next.js).
- Atualizar `CLAUDE.md` se houver mudança arquitetural relevante (ex.:
  `data/chromadb/edu_literature/` agora é parte da infraestrutura).

### 7.2 Critério de avanço

`fase-5-conclusao.md` aprovado + ADR 0003 commitado → Fase 5 oficial-
mente fechada e Fase 6 (frontend Next.js) destravada.

---

## 8. Pendências registradas

1. ⏳ ADR 0003 — Sprint 5.7.
2. ⏳ Suite live nunca foi rodada com chave Anthropic real ainda
   (depende do usuário decidir gastar ~$0.20). Asserts soft devem
   passar mas a validação final fica pendente.
3. ⚠️ `_disable_crewai_telemetry_if_default()` faz `setdefault` no
   `os.environ` no início do `run_master`. Se algum agente carregar a
   `crewai.telemetry` antes desse setdefault (ex.: import lazy), o
   default pode não ser respeitado. Em testes nunca vimos efeito;
   monitorar em produção.
4. ⚠️ `analysis_crew` roda 4 LLM calls sequenciais (~10-20s cada com
   Sonnet 4.5). Sprint 5+ pode paralelizar Comparativist || Visualizer
   (ambos consomem `RetrievedData + StatAnalysis` independentemente).
5. ⚠️ Custo médio por pergunta no fluxo `data` ainda não medido —
   estimado ~$0.05-0.10 baseado em mix Haiku/Sonnet, mas precisa
   confirmação live. Critério §10.8 do `fase-5-analise.md`
   (≤ US$0.10/pergunta) será validado na Sprint 5.7 conclusão.

---

*Próximo doc: `fase-5-conclusao.md` (Sprint 5.7).*
