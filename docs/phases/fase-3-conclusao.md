# Fase 3 — Conclusão e Estado do Sistema

> **Análise Educacional Comparada Brasil × Internacional**
> Documento de fechamento da Fase 3 (Gold Layer / Marts).
> **Data de fechamento:** 2026-04-29
> **Status:** ✅ Concluída — pronta para iniciar Fase 4 (FastAPI Gateway).

---

## 1. Sumário executivo

A Fase 3 transforma a Silver canônica em **5 marts analíticos** que
respondem perguntas de pesquisa diretamente em SQL puro. Cada mart é
"largo" (uma linha por unidade analítica, várias colunas de valores e
derivados), facilitando consumo por dashboards, agentes CrewAI e
respostas em linguagem natural.

### Em uma frase

> Saímos de "Silver canônica empilhando 6 fontes" (Fase 2) para "5
> marts Gold com 1.180 linhas analíticas + indicadores derivados
> (z-score, percentil, gap, trend slope) + suite de qualidade
> pytest+dbt validando distribuições, correlações e cobertura."

---

## 2. Atualizações implementadas

### 2.1 Sprints da Fase 3

| Sprint | Entregáveis | Linhas SQL | Testes |
|---|---|---|---|
| **3.0 — Setup + macros** | `tag:gold`, 4 macros derivadas (zscore, percentile, gap, trend) | ~100 | — |
| **3.1 — Marts diretos** | `mart_br_vs_ocde__gasto_educacao_timeseries`, `mart_alfabetizacao__latam_2020s` | ~250 | +24 |
| **3.2 — Mart de rankings** | `mart_indicadores__rankings_recente` (long format cross-indicador) | ~80 | +5 |
| **3.3 — Marts de cruzamento** | `mart_gasto_x_alfabetizacao__correlacao`, `mart_br__evolucao_indicadores` | ~250 | +13 |
| **3.4 — Custom tests + GE** | `accepted_range` test, suite pytest @quality (11 testes) | ~250 | +37 dbt + 11 pytest |
| **3.5 — Docs + OpenMetadata stub** | `dbt docs generate`, `infra/openmetadata/README.md` | ~150 doc | — |
| **3.6 — Conclusão** | Este documento | — | — |

**Total Fase 3: ~1.080 linhas SQL/Python adicional, 157 testes dbt verdes
+ 191 testes Python (180 unit + 11 quality).**

### 2.2 Marts Gold (5)

| Mart | Linhas | Países | Cobertura | Pergunta atendida |
|---|---|---|---|---|
| `mart_br_vs_ocde__gasto_educacao_timeseries` | 491 | 39 | 2010-2023 | "Como BR se compara com OCDE em gasto?" |
| `mart_alfabetizacao__latam_2020s` | 38 | 14 | 2020-2024 | "Onde BR está em alfabetização vs LATAM?" |
| `mart_indicadores__rankings_recente` | 134 | 16+ | latest year | "Top-N países em cada indicador-fonte?" |
| `mart_gasto_x_alfabetizacao__correlacao` | 391 | 63 | 2000-2023 | "Quanto gasto se converte em alfabetização?" |
| `mart_br__evolucao_indicadores` | 126 | 1 (BR) | 2000-2024 | "Trajetória completa do BR em todos os indicadores?" |
| **TOTAL** | **1.180** | | | |

### 2.3 Macros derivadas (4)

Reutilizadas em 3-5 marts, garantindo consistência metodológica:

- `compute_zscore(value_col, partition_by)` — z-score com `nullif(stddev,0)`.
- `compute_percentile_rank(value_col, partition_by, ascending=true)` — percentil ∈ [0,1].
- `compute_gap_to_mean` / `compute_gap_to_median` / `compute_gap_pct_to_mean` — diferenças.
- `compute_trend_slope` / `compute_trend_r2` — regressão linear via DuckDB `regr_*`.

### 2.4 Testes (qualidade aumentada)

**dbt declarative tests**: 157 (de 100 antes)
- 37 novos `accepted_range` em colunas de valor, z-score, percentil, ano.

**pytest @quality**: 11 testes Python contra DuckDB direto:
- Distribuições esperadas (média gasto ∈ [3.5, 6.5]; média alfab ∈ [80, 99]).
- Correlações cross-fonte (WB == UIS por par, max diff < 0.01pp).
- Cobertura mínima (≥30 países OECD mart, ≥10 LATAM mart, BRA presente).
- Consistência lógica (`coalesce` correto, rank ∈ [1, count]).
- Sanidade de derivados (z-score ∈ [-5, 5], slope ∈ [-1, 1]).

**Total**: 348 testes verdes (157 dbt + 191 Python).

---

## 3. Insights revelados

### 3.1 Gasto educação BR — top 25% OCDE consistente

`mart_br_vs_ocde__gasto_educacao_timeseries`:

| Ano | BRA gasto % PIB | OCDE mean | BRA Z-score | BRA Percentil |
|---|---|---|---|---|
| 2018 | 6.09 | 5.04 | +0.85σ | 0.79 |
| 2020 | 5.77 | 5.41 | +0.29σ | 0.78 |
| 2022 | 5.62 | 5.01 | +0.60σ | 0.82 |

Brasil **consistentemente acima da média OCDE** em gasto educação,
permanecendo no top 22-28% dos países OCDE. Trend slope ≈ 0 (gasto
estável ao longo da década).

### 3.2 Alfabetização BR — abaixo da média LATAM

`mart_alfabetizacao__latam_2020s`:

| País | Literacy 2020 | Gap vs LATAM mean | Percentil LATAM |
|---|---|---|---|
| Argentina | 99.14 | +4.24 | 1.00 |
| Uruguai | 98.96 | +4.06 | 0.90 |
| Colômbia | 95.64 | +0.74 | 0.80 |
| México | 95.25 | +0.35 | 0.70 |
| **Brasil** | **94.74** | **-0.16** | **0.60** |

Brasil **levemente abaixo da média LATAM** e atrás de cones-sul
(Argentina/Uruguai). Percentil 60º entre 14 países LATAM.

### 3.3 Cruzamento gasto × alfabetização — paradoxo BR

`mart_gasto_x_alfabetizacao__correlacao`:

| Ano | BRA gasto | BRA alfab | Z-gasto | Z-alfab | Z-diff (alfab-gasto) |
|---|---|---|---|---|---|
| 2018 | 6.09 | 93.23 | +2.05σ | +0.31σ | -1.74 |
| 2020 | 5.77 | 94.74 | +0.96σ | +0.23σ | -0.74 |
| 2022 | 5.62 | 94.38 | +2.04σ | +0.45σ | -1.59 |

**BR investe muito acima da média** (+2σ) **mas alfabetiza próximo da
média** (+0.3-0.45σ). `Z-diff` consistentemente negativo significa
que o resultado é **abaixo do esperado** dado o nível de gasto. Tema
clássico (Hanushek & Woessmann, 2011): gastar mais não converte
linearmente em resultados.

Top-3 países mais "eficientes" (z-diff alto): Indonésia, Sri Lanka,
Albânia — alfabetização ~92-97% com gasto < 3.5% PIB. (Ressalva: como
documentado no SQL, países já saturados próximos a 100% parecem
artificialmente eficientes.)

### 3.4 Mart 5 (BR longitudinal) revela qualidade dos dados

`mart_br__evolucao_indicadores` mostra todas as fontes lado-a-lado por
ano para BR:

- **Gasto OECD**: rank #2 LATAM-OCDE; #9-12 OCDE total. Cobertura 2010-2020.
- **Gasto WB/UIS**: rank #4-5 LATAM (21 países); rank #7-9 OCDE (38 países).
- **Alfabetização UNESCO/WB**: rank #5-8 LATAM (11 países).
- **Alfabetização IPEA**: rank #1 (so BR aparece) — 94.7% em 2024.

Visível também a **diferença sistemática IPEA vs UNESCO** (~0.7pp acima)
documentada como diferença metodológica esperada na ADR 0002.

---

## 4. Decisões aplicadas (vs `fase-3-analise.md`)

### 4.1 ✅ Schema largo nos marts

Confirmado. Marts 1, 2, 3 são wide (1 linha por country-year com
colunas value_<source>); Marts 3 e 5 são long (1 linha por
indicador-source-país-ano) por necessidade analítica.

### 4.2 ✅ Macros derivadas centralizadas

`compute_zscore`, `compute_percentile_rank`, `compute_trend_slope`
foram reusadas em 4 dos 5 marts sem divergência.

### 4.3 ✅ Materialização `table` para todos marts

Build completo dos 5 marts em ~3.4s, queries downstream instantâneas.

### 4.4 ✅ Tag `gold` global aplicada

Permite `dbt run --select tag:gold`. Sub-tags semânticas (`gasto`,
`alfabetizacao`, `cross`, `rankings`, `br`) habilitam refresh seletivo.

### 4.5 ⚠️ Bug detectado durante Sprint 3.3 — cartesian explosion

Mart 5 inicial tinha cartesian explosion quando IPEA tinha 2 séries
(PNADCA + Atlas DH) no mesmo ano: 2 × 2 × 2 = 8 linhas duplicadas.
**Fix**: dedup com `MAX(value)` GROUP BY antes do rank, e preservação
de `source_indicator_id` no JOIN final. Documentado no SQL.

### 4.6 ⚠️ Eurostat fora do mart de gasto

`int_indicadores__gasto_educacao` empilha WB + UIS + OECD apenas, não
Eurostat — porque o dataset Eurostat coletado (`educ_uoe_fine01`) traz
absolutos, não % PIB. Para incluir, precisaria de coletor adicional
(`t2020_42` ou similar). Documentado em ADR 0002.

---

## 5. Avanço do sistema

### 5.1 Por camada do CLAUDE.md

| Camada | Estado pré-Fase 3 | Estado pós-Fase 3 |
|---|---|---|
| **0. Fontes** | 6 com dados reais | 6 (idem) |
| **1. Ingestão** | ✅ | ✅ |
| **2. Bronze** | 3,2M obs | 3,2M obs (idem) |
| **3. Silver** | 7 stagings, 5 intermediates | 7 stagings, 5 intermediates (idem) |
| **4. Gold** | ⏳ vazia | ✅ **5 marts, 1.180 linhas analíticas** |
| **5. FastAPI** | 🟡 health | 🟡 idem (Fase 4 próxima) |
| **6. CrewAI** | ⏳ | ⏳ |
| **7. Frontend** | 🟡 hello world | 🟡 idem |

### 5.2 Métricas finais

```
Marts Gold publicados:        5
Macros derivadas:             4 (zscore, percentile, gap, trend)
Linhas Gold materializadas:   1.180 (491+38+134+391+126)
dbt build time:               ~5.3s
Tests dbt:                    157 / 157 (PASS=157, ~5.3s)
Tests Python total:           191 / 191 (180 unit + 11 quality)
Custom test accepted_range:   aplicado em 19 colunas
```

### 5.3 Histórico de commits da Fase 3

```
9a1c3a8 feat(dbt): Fase 3 sprints 3.0-3.2 — primeiros marts Gold com derivados
ac1bc95 feat(dbt): Fase 3 sprint 3.3 — marts de cruzamento e perfil-pais BR
eb4a03e feat(quality): Fase 3 sprints 3.4-3.5 — accepted_range, GE pytest, OpenMetadata stub
<próximo> docs(phases): Fase 3 sprint 3.6 — fase-3-conclusao
```

---

## 6. Próximos passos — Fase 4 (FastAPI Gateway)

A Fase 4 expõe os marts via REST/SSE para que o frontend e os agentes
CrewAI consumam dados. Não há mais SQL/transformação aqui — só servir.

### 6.1 O que entra na Fase 4

#### Endpoints prioritários

```
POST /api/data/compare
    Body: {"indicator": "GASTO_EDU_PIB", "countries": ["BRA","FIN"], "year": 2022}
    Backend: SELECT a partir de mart_br_vs_ocde ou mart_indicadores

POST /api/data/timeseries
    Body: {"indicator": "GASTO_EDU_PIB", "country": "BRA", "start": 2010, "end": 2023}
    Backend: SELECT a partir de mart_br__evolucao_indicadores

POST /api/data/ranking
    Body: {"indicator": "LITERACY_15M", "year": 2023, "grouping": "latam"}
    Backend: SELECT a partir de mart_indicadores__rankings_recente

GET  /api/data/catalog
    Backend: lista de tabelas com descricoes (manifest.json do dbt)
```

#### Convenções

- **SQL pré-validado**: agentes não escrevem SQL livre, FastAPI valida
  inputs e monta queries seguras (decisão chave da CLAUDE.md).
- **Streaming SSE** para `/api/chat/stream` (Fase 5+).
- **OpenAPI auto-gerado** via Pydantic v2.
- **`openapi-typescript`** gera types para o frontend.

### 6.2 O que **NÃO** entra na Fase 4

- LLM calls (são da Fase 5 — agentes CrewAI).
- Streaming bidirecional (WebSocket — só se Fase 5 demandar).
- Authentication (sistema acadêmico privado — adiável).

### 6.3 Bloqueadores conhecidos

Nenhum bloqueador novo. FastAPI bootstrap da Fase 0 já existe; basta
adicionar routers + service layer + integração DuckDB read-only.

### 6.4 Estimativa Fase 4

| Sprint | Tarefa | Estimativa |
|---|---|---|
| 4.0 | Setup routers + service + DuckDB pool | 1 dia |
| 4.1 | Endpoints `/api/data/*` (4 endpoints) | 2-3 dias |
| 4.2 | Validacao Pydantic + tipos TypeScript | 1 dia |
| 4.3 | Rate limiting (SlowAPI) + middleware | 0.5 dia |
| 4.4 | Testes integracao | 1.5 dias |
| 4.5 | Documentacao OpenAPI + ADR | 1 dia |
| **Fase 4 completa** | | **~7 dias úteis** |

---

## 7. Débitos técnicos registrados

Maioria herdada da Fase 1.5/2, alguns novos:

1. **R não executado** — bloqueia `mart_pisa_rankings` futuro.
2. **Coletores INEP não executados** — bloqueia `mart_ideb_municipal`.
3. **Eurostat sem dataset de % PIB** — `t2020_42` ou similar precisaria
   ser coletado para Eurostat entrar em `gasto_educacao`.
4. **Trend slope é constante por país** — não há rolling 5-year
   window. Se análises pedirem evolução do slope, criar
   `compute_trend_slope_rolling` em sprint posterior.
5. **OpenMetadata stub não configurado** — documentado em
   `infra/openmetadata/README.md`, configurar quando agentes CrewAI
   começarem.
6. **Subnacional brasileiro** — IPEA/SIDRA UFs/municípios não modelados
   em mart. Adiar até quando análises subnacionais forem demandadas.
7. **Fontes adicionais EUROSTAT/OECD não exploradas** — atualmente
   apenas 3+2 datasets. Catálogo é grande; expandir conforme demanda.
8. **Suite GE em formato pytest, não Great Expectations propriamente** —
   simplificação intencional. Se necessitar reports formais, migrar
   para `great_expectations` package.

---

## 8. Conclusão

A Fase 3 entrega o **primeiro nível analítico** do sistema. Pesquisadores
agora podem responder perguntas como:

- "BR está acima da média OCDE em gasto?" → `SELECT zscore, percentile FROM mart_br_vs_ocde WHERE country_iso3='BRA'`
- "Como BR evoluiu em alfabetização vs LATAM?" → `SELECT gap_to_latam_mean FROM mart_alfabetizacao__latam_2020s WHERE country_iso3='BRA'`
- "BR tem ineficiência de gasto?" → `SELECT zscore_diff_alfab_minus_gasto FROM mart_gasto_x_alfabetizacao`

Cada query roda em milisegundos sobre tabelas materializadas no DuckDB.

O insight central revelado pelos marts — **BR investe acima da média
OCDE mas alfabetiza abaixo da média LATAM** — exemplifica o tipo de
narrativa que o sistema é capaz de construir. Diferenças metodológicas
entre fontes (~1pp WB-vs-OECD para gasto; ~1pp UIS-vs-IPEA para alfab)
ficam documentadas e visíveis, não escondidas.

A próxima fase (FastAPI) começa de uma Gold pronta, testada e
documentada. Os 4 endpoints planejados consumirão exatamente as 5
tabelas existentes, sem necessidade de retrabalho.

---

*Próxima fase: ver `fase-4-analise.md` (a criar). Documento de migração
para outra máquina permanece em
[`fase-2-sprint-2.0-progresso.md`](./fase-2-sprint-2.0-progresso.md).*
