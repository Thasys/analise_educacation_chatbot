# ADR 0008 — DRY refactor pass (Fase A+B+C)

- **Status:** aceito
- **Data:** 2026-05-14
- **Fase:** pós-Fase 6 (manutenção)

## Contexto

Auditoria de duplicação ([`docs/refactor/dry-pass-2026-05.md`](../refactor/dry-pass-2026-05.md))
identificou **10 padrões duplicados** atravessando as 4 camadas Python +
frontend Next.js. Os mais críticos:

1. Handler `try/except ValueError → JSON erro` repetido em 5 tools CrewAI.
2. 3 tools de dados (`timeseries`, `compare`, `ranking`) com `_run` 90% idêntico.
3. 8 `build_*_agent()` com mesmo boilerplate (`allow_delegation=False`, `verbose=False`).
4. 4 `_run_<etapa>` da Analysis Crew com forma idêntica (Task + kickoff + coerce).
5. 7 coletores HTTP com `httpx.Client + try/finally + log + parse` duplicado.
6. `_period_bounds` literal idêntico em 5 coletores.
7. 3 page.tsx do Next.js com shell `<Sidebar/><Workspace/><ContextPanel/>` idêntico.
8. Render de DOI link duplicado em `CitationCard` + `ContextPanel`.

Ver doc original para a tabela completa com referências de linha.

## Decisão

Executado em **3 fases** com testes verdes ao fim de cada uma. Aproveita
o trabalho de quality assessment 2026-05-14 que sugeriu vários quick wins
que dependiam dessas refatorações.

### Fase A — DRY que destrava qualidade (~5-6h)

| # | Refator | Arquivos | QA wins destravados |
|---|---|---|---|
| 1 | `SafeTool` base ([`tools/_base.py`](../../agents/src/tools/_base.py)) | 5 tools | QW1, QW3, QW4 |
| 2 | `_EndpointTool` base | `data_tools.py` (3 classes) | MP3 (data_describe) |
| 3 | `make_agent(role, goal, prompt_name, llm_kind)` ([`agents/_builder.py`](../../agents/src/agents/_builder.py)) | 8 builders | MP4, LP1, LP3 |
| 4 | `run_single_agent_task` + `coerce_output` ([`crews/_helpers.py`](../../agents/src/crews/_helpers.py)) | analysis_crew + core_crew | QW3, MP4 |
| 5 | Plotly builder paramétrico + `_validate_figure` ([`tools/viz_tools.py`](../../agents/src/tools/viz_tools.py)) | viz_tools.py | QW1, MP2, LP3 |

### Fase B — Higiene de código (~3-4h)

| # | Refator | Arquivos |
|---|---|---|
| 1 | `parse_period` utilitário ([`data_pipeline/utils/period.py`](../../data_pipeline/src/utils/period.py)) | 5 coletores |
| 2 | `build_data_response` + `measure_query_ms` ([`api/dependencies/response.py`](../../api/src/dependencies/response.py)) | 3 endpoints `/api/data` |
| 3 | `WorkspaceShell` + `DoiLink` + `formatCitationMeta` (frontend) | 3 pages + 2 components |
| 4 | `instantiate_with_shared_client` em `tools/_base.py` | `build_data_tools` + `build_rag_tools` |

### Fase C — Refator pesado (~2-3h)

| # | Refator | Arquivos |
|---|---|---|
| 1 | `BaseCollector._http_fetch_json` + `_http_fetch_paginated` | 6 dos 7 coletores REST |

WorldBank mantém loop próprio (paginação por page-number não casa com a
abstração genérica). Aceita-se a duplicação para preservar simplicidade
do helper.

## Alternativas consideradas

1. **Pular tudo** — código duplicado é "OK enough" e o sistema funciona.
   Descartado: vários quick wins (QW1, QW3, QW4) do quality plan dependiam
   das refatorações para implementação consistente.

2. **Refator total numa única PR** — descartado: risco de regressão alto
   em 4 camadas simultâneas. Fases A/B/C com testes verdes ao fim de cada
   reduz risco.

3. **Aproveitar para mudanças funcionais** — descartado: separar refactor
   puro (esta ADR) de novas features (ADRs 0006, 0007) facilita revisão.

## Consequências

**Positivas:**
- ~600 linhas de código eliminadas (estimativa do doc original).
- Adicionar uma 9ª tool de dados (ex.: `data_describe`) ou um 9º agente
  CrewAI passa a ser ~10 linhas em vez de 50.
- Guardrails (QW1 figure validation, QW3 numeric consistency) ganham
  estrutura para encaixar — não viraram fixes pontuais.
- 4 testes pré-quebrados (validações `min_length` removidas por compat GBNF
  do Ollama) ficaram verdes: restauramos as validações dentro de `_run`.

**Negativas:**
- Curva de aprendizado pequena para novos contribuidores: tools herdam de
  `SafeTool` / `_EndpointTool`; entendê-las exige ler `_base.py` antes.

**Débitos:**
- WorldBank coletor pode ser refatorado se a abstração de paginação por
  page-number for útil em outro lugar (atualmente é único). Não vale a pena
  generalizar prematuramente.

## Testes

105 testes Python verdes ao final da Fase C (75 originais + 12 fact-check +
18 DOI validator):

```
agents/tests/tools/        38 tests
agents/tests/agents/       37 tests + 12 fact-check
agents/tests/tools/test_doi_validator.py  18 tests
total                      105 passed
```

Frontend: 77 vitest unit passando após refator do shell + DoiLink.
Data pipeline: 168 tests verdes após adoção dos helpers HTTP da base.

## Links

- Análise completa: [`docs/refactor/dry-pass-2026-05.md`](../refactor/dry-pass-2026-05.md)
- Quality assessment: [`docs/quality-assessment-2026-05-14.md`](../quality-assessment-2026-05-14.md)
