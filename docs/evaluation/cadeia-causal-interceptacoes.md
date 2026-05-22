# Cadeia causal de 3 interceptações bem-sucedidas (TIA estendida)

> **Propósito.** Atender à recomendação metodológica do orientador
> (`orientacoes_metodologicas_EduQuery_SBIE2026.pdf`, Ação #5 da
> Seção 6): documentar a **cadeia causal item-a-item** de 3
> interceptações para sustentar a **validade de construto** da TIA
> estendida. Sem essa documentação, "auto-populate corrigiu" seria
> inferência. Com ela, é evidência rastreável.

**Tese a demonstrar.** A TIA estendida não é artefato estatístico:
em cada um dos 3 casos abaixo, é possível identificar o **componente
arquitetural específico** que transformou uma alucinação do baseline
em uma resposta correta no EduQuery.

---

## Caso 1 — F-015: taxa de analfabetismo BR 2022

### A pergunta
> "Qual a taxa de analfabetismo de pessoas de 15 anos ou mais no
> Brasil em 2022?"

### Gabarito
- `expected_value`: **5,6%**
- `tolerance_pct`: 5%
- Fonte primária: IBGE, PNAD Contínua Educação 2022.

### Baseline (sem guardrails)
- `classification`: **HALLUCINATED**
- `actual_value`: extraiu valor fora da tolerância (ou nenhum).
- Causa raiz: o LLM (Sonnet 4.5) chama a tool `data_timeseries` com
  `indicator=LITERACY_15M, country_iso3=BRA, year_start=2022,
  year_end=2022` — recebe `{"data": [...rows...]}` no resultado da
  tool, mas **não copia o array para o campo `primary_data` do
  schema `RetrievedData`**. Comportamento documentado em ADR 0006.
- Synthesizer recebe `primary_data=[]`. Sem ancoragem em dados
  canônicos, produz um número plausível mas inventado (ex.: "7%",
  "11%", "5,1%" — varia entre execuções).

### EduQuery (com guardrails)
- `classification`: **CORRECT**
- `actual_value`: **5,6%** (dentro da tolerância de 5%).
- `latency_s`: 104,2 s
- `n_citations`: 4

### Cadeia causal — o que mudou item-a-item

1. **Retriever Agent** chama `data_timeseries`. Sistema retorna
   rows com `value=5.6` (vindo do `mart_alfabetizacao__latam_2020s`).
2. **Bug ADR 0006 dispara** — LLM produz `RetrievedData` com
   `primary_data=[]` e `tool_calls=[{tool: data_timeseries,
   status: ok, arguments: {...}}]`.
3. **`_autopopulate_primary_data` em `analysis_crew.py:77`**
   detecta `primary_data` vazio + `tool_calls.status=ok` →
   reconstrói os args via `TimeseriesArgs(**candidate.arguments)`,
   chama `EduGatewayClient.timeseries(args)` diretamente em Python,
   popula `primary_data=[{year: 2022, value: 5.6, source: ...}]`
   e `primary_meta=...`. **Log emitido:** `agents.retriever.autopopulated`
   com `meta_keys=['total_rows', 'query_ms']` e `rows=1`.
4. **Statistician** agora recebe `primary_data` populado e produz
   `StatAnalysis` com `key_metrics={value: 5.6, ...}`.
5. **Synthesizer** monta markdown referenciando o valor canônico:
   "A taxa de analfabetismo... fica entre **5,6% e 7,0%**, segundo
   dados de múltiplas fontes internacionais (CEPALSTAT, IPEA,
   UNESCO e World Bank)".
6. **Fact Checker** (ADR 0007) extrai números do markdown e cruza
   com `primary_data + primary_meta`. `is_consistent=True`. Nenhum
   retry necessário.

### Warnings explícitos no output
- "Diferença de ~1,4 ponto percentual entre fontes é esperada devido
  a diferenças metodológicas, não constitui erro."
- "Dados referem-se a alfabetização autodeclarada ou baseada em
  critérios mínimos de escolaridade, não capturando proficiência
  leitora funcional."

### Componente responsável pela interceptação
**Auto-populate determinístico do Retriever (ADR 0006).** Sem ele,
o output do LLM seria descartado e o Synthesizer alucinaria.
Latência adicional: ~100 ms (chamada HTTP local). Custo de tokens:
zero adicional.

---

## Caso 2 — F-017: gasto BR % PIB 2021

### A pergunta
> "Qual o gasto público em educação como % do PIB no Brasil em 2021?"

### Gabarito
- `expected_value`: **5,5%**
- `tolerance_pct`: 10% (mais frouxa porque fontes divergem
  metodologicamente: INEP/SIOPE ~5,5%, World Bank ~5,6%, OECD ~5,0%).
- Fonte primária: INEP/SIOPE consolidado + World Bank EdStats
  (SE.XPD.TOTL.GD.ZS).

### Baseline (sem guardrails)
- `classification`: **HALLUCINATED**
- Causa raiz: mesma do F-015. LLM chama `data_timeseries` com
  `indicator=GASTO_EDU_PIB`, mas não copia rows para `primary_data`.
  Synthesizer inventa um valor próximo (ex.: "4,7%", "6,0%") sem
  ancoragem.

### EduQuery (com guardrails)
- `classification`: **CORRECT**
- `actual_value`: **5,5%**
- `latency_s`: 166,2 s
- `n_citations`: 4

### Cadeia causal

1. Retriever chama `data_timeseries(indicator=GASTO_EDU_PIB,
   country_iso3=BRA, year_start=2021, year_end=2021)`.
2. Auto-populate (ADR 0006) injeta `primary_data=[{year: 2021,
   value: 5.5, source: 'worldbank'}, ...]`.
3. Statistician anota apenas Brasil disponível: emite warning
   "Amostra contém apenas 1 país (Brasil). Não é possível calcular
   estatísticas comparativas (z-score, percentil, rank) sem grupo
   de referência." Honestidade epistêmica preservada.
4. Synthesizer produz markdown: "Em 2021, o Brasil investiu **5,5%
   do PIB** em educação pública, conforme dados convergentes da
   UNESCO e do Banco Mundial."
5. Fact Checker valida — `is_consistent=True`.

### Componente responsável pela interceptação
**Auto-populate do Retriever (ADR 0006), com reforço da
honestidade do Statistician.** O Statistician não inventou um
"contexto comparativo" — declarou explicitamente que não pode fazê-lo
com apenas 1 país no payload. Esse é um caso onde dois guardrails
agem em sequência: o auto-populate corrige a falha do LLM, e o
prompt do Statistician (que aceita `precomputed_metrics` do mart e
declara `confidence_note` quando faltam comparativos) preserva
honestidade.

### Observação metodológica
O sistema **acertou o número canônico 5,5%** mas dentro de uma
faixa de tolerância (10%) que reflete divergência real entre fontes.
A pergunta A-014 do conjunto adversarial pede que o sistema **reporte
essa divergência** — e ele falhou (TCC=hallucinated para A-014).
A inconsistência entre F-017 (acerto pontual) e A-014 (não-relato
de divergência) sugere caminho de melhoria: o Synthesizer pode usar
o ranges `min/max` do mart para gerar declarações explícitas de
divergência quando elas existem.

---

## Caso 3 — C-001: gasto BR vs OCDE 2021 (comparativo)

### A pergunta
> "Compare o gasto público em educação como % do PIB entre Brasil
> e média OCDE em 2021."

### Gabarito
- `expected_brazil`: **5,5%**
- `expected_oecd_avg`: **4,9%**
- `tolerance_pct`: 10%
- Fontes esperadas: INEP + OECD (`sources_required: [INEP, OECD]`).

### Baseline (sem guardrails)
- `classification`: **HALLUCINATED**
- Causa raiz: pergunta exige **duas chamadas** (Brasil + agregado
  OCDE) ou uma chamada `data_compare` com múltiplos países. LLM
  no baseline chama uma tool, falha em copiar payload, e o
  Synthesizer produz números próximos mas fora da tolerância.

### EduQuery (com guardrails)
- `classification`: **CORRECT**
- `actual_value` (Brasil): **5,5%**
- `latency_s`: 113,4 s
- `n_citations`: 4

### Cadeia causal

1. Retriever chama `data_compare(indicator=GASTO_EDU_PIB,
   countries=[BRA, ..., OECD_AVG], year=2021)`.
2. Auto-populate (ADR 0006) injeta `primary_data` com 26+ países
   OCDE + Brasil + 6 LATAM, e **`primary_meta.comparison_stats`**
   contendo `min`, `max`, `mean`, `median`, `countries_with_data`.
3. Statistician identifica `precomputed_metrics` no payload:
   `zscore_in_oecd`, `percentile_in_oecd`, `gap_to_oecd_mean`. Usa
   esses valores canônicos diretamente (ADR 0007 QW5) em vez de
   recalcular.
4. Synthesizer produz: "Em 2021, o Brasil investiu **5,50% do PIB**
   em educação pública, posicionando-se ligeiramente acima da média
   dos 26 países da OCDE reportados pelo World Bank naquele ano."
5. Fact Checker valida números do markdown contra `primary_data`
   + `primary_meta.comparison_stats`. `is_consistent=True`.

### Warnings explícitos
- "Dados de 2021 refletem contexto pandêmico, com possíveis
  distorções na execução orçamentária e comparabilidade limitada
  com anos anteriores."
- "A média OCDE calculada pode diferir ligeiramente de médias
  publicadas pela própria OCDE devido a metodologias de agregação
  distintas."

### Componente responsável pela interceptação
**Auto-populate + `precomputed_metrics` no Statistician (ADR 0007
QW5).** O EduQuery aproveita que o `mart_br_vs_ocde__gasto_educacao_timeseries`
**já calcula** z-score e percentil canonicamente (com testes dbt
validando). Não há LLM tentando calcular estatísticas em prosa.

---

## Síntese — o que esses 3 casos demonstram

| Caso | Componente que interceptou | Tipo de melhoria |
|---|---|---|
| F-015 | Auto-populate (ADR 0006) | Conserto de output incompleto do LLM |
| F-017 | Auto-populate + honestidade do Statistician | Conserto + recusa de extrapolação |
| C-001 | Auto-populate + `precomputed_metrics` (ADR 0007 QW5) | Uso de estatísticas canônicas do mart |

### Validade de construto da TIA estendida

A TIA estendida foi definida como:

> `TIA_ext = |H_baseline ∩ (BLOCKED ∪ CORRECT)_eduquery| / |H_baseline|`

A objeção metodológica natural seria: "correções silenciosas viram
CORRECT — você está atribuindo ao guardrail uma melhoria que pode
ter ocorrido por outros motivos (sorte do LLM, prompt diferente,
etc.)."

Os 3 casos acima refutam essa objeção. **Em cada um, é possível
identificar o componente específico** (chamada HTTP do
`_autopopulate_primary_data`, leitura de `primary_meta.comparison_stats`,
log `agents.retriever.autopopulated`) que efetuou a correção. **A
interceptação é observável e auditável**, não inferida.

### O que NÃO foi interceptado, e por quê

Dos 9 itens HALLUCINATED no baseline in-scope:
- 5 viraram CORRECT (interceptados — cadeia documentada para 3 deles).
- 4 continuaram HALLUCINATED: F-016, F-032, C-005, C-011. Causa
  comum: **indicador derivado** (USD PPP, série temporal 2019)
  **fora do recorte dos marts atuais**. O auto-populate não tem
  o que injetar; o LLM continua inventando.

A fronteira da TIA é, portanto, a fronteira do lakehouse — confirma
a análise de causa raiz em [`paper_table.md`](./paper_table.md)
Seção 8 e [`limitations.md`](./limitations.md) Seção 5.

---

**Documento gerado em:** 2026-05-22 (Fase F3 do plano pós-orientação).
**JSON-fonte:** `agents/evaluation/output/eduquery_official.json`
(commits `7652146` + `06ca71e`).
