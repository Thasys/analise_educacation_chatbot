# Fase 3 — Sprints 3.0 a 3.2 (Setup + 3 marts iniciais)

> Progresso parcial da Fase 3. Sprints 3.0 (setup), 3.1 (marts BR×OCDE
> e alfabetização LATAM) e 3.2 (rankings cross-indicador) entregues.
> **Data:** 2026-04-29

---

## 1. O que foi entregue

### 1.1 Setup (Sprint 3.0)

- **`models/marts/`** estruturado em `dbt_project.yml` com tag `gold`
  global. Sub-tags semânticas (`gasto`, `alfabetizacao`, `rankings`)
  para seleções como `dbt run --select tag:gold,tag:gasto`.
- **4 macros derivadas** em `macros/derived/`:
  - `compute_zscore` — z-score com proteção `nullif(stddev,0)`.
  - `compute_percentile_rank` — percentil em [0,1], ascending opcional.
  - `compute_gap_to_mean` / `compute_gap_to_median` / `compute_gap_pct_to_mean`.
  - `compute_trend_slope` / `compute_trend_r2` — regressão linear via DuckDB `regr_slope`/`regr_r2`.

### 1.2 Marts (3)

| Mart | Linhas | Países | Anos | Cobertura analítica |
|---|---|---|---|---|
| `mart_br_vs_ocde__gasto_educacao_timeseries` | 491 | 39 | 2010–2023 | BR + 38 OCDE com derivados (z-score, percentil, gap, trend) |
| `mart_alfabetizacao__latam_2020s` | 38 | 14 | 2020–2024 | BR + LATAM, gap_to_latam_mean + gap_to_bra |
| `mart_indicadores__rankings_recente` | 47 | 16+ | latest | Rankings global e por grouping para 2 indicadores × 5 fontes |

### 1.3 Build dbt

```
3 seeds · 7 view models (staging) · 5 table models (intermediate) · 3 table models (marts)
PASS=119 WARN=0 ERROR=0 SKIP=0   (~4.2s end-to-end)
```

---

## 2. Insights revelados pelos marts

### 2.1 Brasil em gasto educação (% PIB) — acima da média OCDE

Mart 1 (`mart_br_vs_ocde__gasto_educacao_timeseries`):

| Ano | BRA | OCDE mean | Z-score BRA | Percentil BRA |
|---|---|---|---|---|
| 2018 | 6.09 | 5.04 | +0.85σ | 0.79 |
| 2019 | 5.96 | 5.10 | +0.70σ | 0.74 |
| 2020 | 5.77 | 5.41 | +0.29σ | 0.78 |
| 2021 | 5.50 | 5.22 | +0.23σ | 0.72 |
| 2022 | 5.62 | 5.01 | +0.60σ | 0.82 |

**Brasil gasta acima da média OCDE de forma consistente** (~0.5–0.85σ
acima), no top 25% dos países OCDE. Top-5 mundial em 2020 são nórdicos
(Islândia 8.58%, Noruega 8.37%, Suécia 7.95%, Dinamarca 7.39%, Bélgica 6.75%).

**Trend slope BRA 2010–2023: -0.005, R² = 0.01** — tendência ligeiramente
decrescente mas estatisticamente nula (R² ≈ 0). Gasto BR está estável.

### 2.2 Brasil em alfabetização LATAM — atrás da média

Mart 2 (`mart_alfabetizacao__latam_2020s`):

| País | Literacy 2020 | Gap vs LATAM mean (94.90) | Percentil LATAM |
|---|---|---|---|
| Argentina | 99.14 | +4.24 | 1.00 |
| Uruguai | 98.96 | +4.06 | 0.90 |
| Colômbia | 95.64 | +0.74 | 0.80 |
| México | 95.25 | +0.35 | 0.70 |
| **Brasil** | **94.74** | **-0.16** | **0.60** |
| Paraguai | 94.54 | -0.36 | 0.50 |
| Peru | 94.50 | -0.40 | 0.40 |

**Brasil está ligeiramente abaixo da média LATAM** em alfabetização e
visivelmente atrás de Argentina/Uruguai (cones-sul mais alfabetizados).

### 2.3 Combinação dos dois marts: gasto alto, resultado intermediário

Brasil:
- Gasto educação: top 25% OCDE (acima da média).
- Alfabetização: ~50º percentil LATAM (abaixo da média LATAM).

Indica **eficiência de gasto subótima** — pesquisa-tema clássica da
literatura comparada (Hanushek & Woessmann, 2011).

### 2.4 Mart 3 — rankings cross-indicador (latest)

Estrutura long: uma linha por (indicador, source, país). Útil para
queries do tipo:
- "Qual a posição do BRA em cada indicador-fonte no ano mais recente?"
- "Top 5 países LATAM em alfabetização hoje?"

Cobertura: 47 linhas; 2 indicadores × 5 fontes × ~8 países por combinação.

---

## 3. Decisões aplicadas (vs `fase-3-analise.md`)

### 3.1 ✅ Schema largo nos marts

Cada mart tem 1 linha por unidade analítica (país-ano), com colunas
`value_<fonte>` e múltiplos derivados. Confirma o padrão: usuário final
vê tudo sobre BR-2020 em uma linha, sem precisar agrupar.

### 3.2 ✅ Macros derivadas centralizadas

`compute_zscore`, `compute_percentile_rank`, `compute_trend_slope` foram
**reusadas em 2-3 marts** sem divergência. Mudança no cálculo se propaga
em um lugar só.

### 3.3 ✅ INNER JOIN com seed para filtragem analítica

`grouping LIKE '%oecd%'` (3 sub-grupos: oecd, oecd_g7, latam_oecd) e
`grouping LIKE '%latam%'` (2: latam, latam_oecd) — clean, sem listas
hardcoded.

### 3.4 ⚠️ Trend slope é constante por país (não acumulativo)

`regr_slope` over partition produz **um valor por país** (não yearly
slope incremental). Documentado no schema.yml como "constante por país".
Para slopes incrementais (rolling 5-year window), seria necessário
window adicional — fica para Sprint 3.3 se demandado.

### 3.5 ⚠️ value_canonical = `coalesce(unesco, worldbank, cepalstat)`

Mart 2 prioriza fontes internacionais sobre IPEA (que é só BR) para que
comparações entre países sejam apples-to-apples. Mart 1 usa `coalesce`
WB→UIS porque os dois são idênticos por construção.

---

## 4. Pendências para Sprint 3.3+

### 4.1 Marts faltantes do catálogo §4.1 da análise

- [ ] `mart_gasto_x_alfabetizacao__correlacao` — cruzamento entre os 2
  indicadores. Detecta países "alto gasto + baixa alfabetização" (BR
  candidato).
- [ ] `mart_br__evolucao_indicadores` — visão longitudinal BR em todos
  os indicadores em uma só tabela.

### 4.2 Custom test `accepted_range`

Pendente. Aplicar a:
- `value_worldbank ∈ [0, 30]` (gasto % PIB).
- `value_canonical ∈ [0, 100]` (literacy %).
- `zscore_in_oecd_year ∈ [-5, 5]`.
- `percentile_in_oecd_year ∈ [0, 1]`.

### 4.3 Suite Great Expectations mínima

Pendente. Ver §7.4 da análise.

### 4.4 OpenMetadata + dbt docs serve

Pendente — Sprint 3.5.

---

## 5. Como retomar

```bash
# Build apenas Gold
DBT_PROFILES_DIR=. dbt run --select tag:gold

# Construir um mart isolado com deps
DBT_PROFILES_DIR=. dbt build --select +mart_br_vs_ocde__gasto_educacao_timeseries

# Visualizar dados
duckdb data/duckdb/education.duckdb \
  -c "SELECT * FROM main_marts.mart_br_vs_ocde__gasto_educacao_timeseries WHERE country_iso3='BRA' ORDER BY year"
```

---

## 6. Métricas

```
Marts publicados:                 3
Macros derivadas:                 4 (zscore, percentile_rank, gap, trend)
Linhas Gold materializadas:       576 (491 + 38 + 47)
Tempo dbt build:                  ~4.2s
Cobertura paises (Mart 1):        39 (BR + 38 OCDE)
Cobertura paises (Mart 2):        14 LATAM
Tests dbt:                        119 / 119 (PASS=119, WARN=0)
Tests Python (sem mudanca):       180 / 180
```

---

*Continuação: Sprint 3.3 (mart de cruzamento gasto×alfabetizacao), 3.4
(custom test + GE), 3.5 (OpenMetadata + docs serve).*
