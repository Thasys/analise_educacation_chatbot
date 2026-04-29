# Fase 3 — Análise de Desenvolvimento (Gold Layer)

> **Análise Educacional Comparada Brasil × Internacional**
> Documento analítico sobre o desenvolvimento da **Fase 3 — Gold Layer / Marts**.
> Complementa o roadmap geral em [`CLAUDE.md`](../../CLAUDE.md#fase-3--gold-layer-e-catálogo-semanas-89)
> e parte das conclusões da [`Fase 2`](./fase-2-conclusao.md).
> **Data:** 2026-04-29

---

## Sumário

1. [Contexto e ponto de partida](#1-contexto-e-ponto-de-partida)
2. [Objetivos da Fase 3](#2-objetivos-da-fase-3)
3. [Decisões arquiteturais propostas](#3-decisões-arquiteturais-propostas)
4. [Catálogo de marts](#4-catálogo-de-marts)
5. [Indicadores derivados](#5-indicadores-derivados)
6. [Padrões de modelagem](#6-padrões-de-modelagem)
7. [Estratégia de testes](#7-estratégia-de-testes)
8. [Sequência de implementação](#8-sequência-de-implementação)
9. [Riscos e mitigações](#9-riscos-e-mitigações)
10. [Critérios de aceitação](#10-critérios-de-aceitação)
11. [Apêndice: convenções rápidas](#11-apêndice-convenções-rápidas)

---

## 1. Contexto e ponto de partida

A Fase 2 entregou uma Silver com schema canônico estável para 2
indicadores cross-source (`gasto_educacao` e `alfabetizacao`), 6 fontes
funcionais e 3,2M observações queriáveis em DuckDB local. As decisões
metodológicas (UNION ALL multi-fonte, dedup defensivo, filtragem por
seed) estão registradas em [`ADR 0002`](../adrs/0002-fase-2-schema-canonico-silver.md).

A Fase 3 não harmoniza mais — **só analisa**. Aqui, "análise" significa:

- **Filtrar e fatiar** (BR vs OCDE; BR vs LATAM; OECD top-quartile vs bottom).
- **Calcular indicadores derivados** (z-scores, percentis, gaps, tendências).
- **Cruzar indicadores** (gasto × resultado; alfabetização × HCI).
- **Rankear** (top-10 países por gasto, evolução de posições no tempo).

Quem fala SQL contra a Gold acessa diretamente respostas analíticas;
não precisa entender plausible values, ISO codes, ou diferenças
metodológicas WB-vs-OECD. Esse trabalho ficou nas Camadas 2 e 3.

### Ponto de partida quantitativo

```
2 indicadores cross-source · 7 stagings · 5 intermediates · 100 testes dbt verdes
DuckDB com 3,2M observações Bronze + 5.229 Silver
0 marts em models/marts/ · 0 testes de range em metricas · 0 lineage publicado
```

---

## 2. Objetivos da Fase 3

### 2.1 Objetivos primários

1. **`dbt build` com 100% verde** incluindo todos os marts.
2. **Pelo menos 4 marts publicados**, cada um respondendo uma pergunta
   analítica concreta do projeto (não tabelas-genéricas).
3. **Indicadores derivados centralizados** em macros reusáveis
   (`compute_zscore`, `compute_percentile`, `compute_trend_slope`).
4. **`dbt docs serve` navegável** mostrando lineage de fontes →
   stagings → intermediates → marts.
5. **Schema rotulado** — toda coluna de mart tem `description` com
   unidade e fórmula explícitas.

### 2.2 Objetivos secundários

6. **Custom dbt test `accepted_range`** para validar plausibilidade
   estatística (`% ∈ [0, 100]`, `z-score ∈ [-5, 5]`, etc.).
7. **OpenMetadata apontando para DuckDB** com metadados básicos
   (descrições, lineage, glossário).
8. **Quality dashboards mínimos** (Streamlit ou Quarto) consumindo
   marts diretamente, para validação visual antes da Fase 6.

### 2.3 Não-objetivos (escopo da Fase 4+)

- FastAPI servindo marts (vai para Fase 4).
- Refresh agendado dos marts (Prefect orquestrando dbt — Fase 4).
- Frontend consumindo marts (Fase 6).
- Cache distribuído de queries (não necessário para escala atual).

---

## 3. Decisões arquiteturais propostas

### 3.1 Marts como `table` materializadas no DuckDB

Justificativa:

- Marts agregam várias intermediates com window functions e CTEs
  pesadas — recomputar em cada query é desperdício.
- DuckDB armazena tabelas internamente em formato colunar otimizado
  (Vortex/Roaring Bitmap-like). 5k-50k linhas por mart fica < 5MB.
- `dbt run --select tag:gold` reconstrói tudo em < 10s.

Onde a Camada 5 (FastAPI) precisar do mart como Parquet externo (para
leitura zero-copy via `read_parquet`), trocaremos pra `external`
materialization na Fase 4 — não antecipamos.

### 3.2 Schema dos marts: largo, não longo

A Silver é "longa" (`UNION ALL` empilha fontes em linhas). A Gold é
**larga** (uma linha por unidade analítica, colunas por dimensão e por
indicador derivado). Exemplo:

```
mart_br_vs_ocde__gasto_educacao_timeseries
  country_iso3 · year · value_worldbank · value_unesco · value_oecd
                       · oecd_mean · oecd_p25 · oecd_p75 · gap_to_oecd_mean
                       · zscore_within_oecd · trend_5y_slope
```

Razão: usuário final faz `SELECT *` esperando "tudo sobre BR em 2020 em
uma linha", não 3 linhas (uma por fonte). A canonização cross-source
fica visível via colunas `value_<fonte>` — quem quer média explicita
calcula no SELECT.

### 3.3 Indicadores derivados em macros, não em SQL inline

Cada cálculo derivado vira macro Jinja em `dbt_project/macros/derived/`:

```sql
-- macros/derived/compute_zscore.sql
{% macro compute_zscore(value_col, partition_by) %}
    ({{ value_col }} - avg({{ value_col }}) over (partition by {{ partition_by }}))
    / nullif(stddev({{ value_col }}) over (partition by {{ partition_by }}), 0)
{% endmacro %}
```

Razão: 4-5 marts vão querer z-score, percentil, gap. Inline cria
divergência (um mart usa `stddev_samp`, outro `stddev_pop`) e bugs
silenciosos. Macros centralizadas garantem consistência.

### 3.4 Convenção de nomenclatura

```
mart_<DOMINIO>__<UNIDADE_ANALITICA>_<RECORTE>
```

Exemplos:
- `mart_br_vs_ocde__gasto_educacao_timeseries` — BR comparado a OCDE em série temporal.
- `mart_alfabetizacao__latam_2020s` — alfabetização LATAM no 2020s.
- `mart_indicadores__rankings_recente` — rankings cross-indicador no ano mais recente.
- `mart_gasto_x_resultados__correlacao` — cruza gasto com indicador de resultado.

Domínio `mart_<x>__` agrupa por pergunta de pesquisa. Recorte distingue
fatias (timeseries, ranking, comparativo, latest).

### 3.5 Tags dbt para gerenciamento

Marts ganham tag `gold` em `config(tags=['gold', '<DOMAIN>'])` para
seletores como `dbt run --select tag:gold` ou `tag:gold,tag:gasto`.
Importante para Fase 4 (refresh seletivo via Prefect).

### 3.6 Documentação inline obrigatória

Toda coluna de mart precisa de:
1. **Unidade explícita** no description (ex.: "% PIB", "anos", "score 0-100").
2. **Fórmula quando derivada** (ex.: "(value - country_mean) / country_std").
3. **Fonte agregada quando aplicável** (ex.: "media de WB+UIS+OECD").

Razão: marts são consumidos por agentes CrewAI (Fase 5) que precisam
entender semântica para responder perguntas em linguagem natural.

---

## 4. Catálogo de marts

Marts da Fase 3 ordenados por valor analítico × esforço:

### 4.1 Marts construíveis com Silver atual (5)

| # | Mart | Fontes Silver | Linhas est. | Pergunta atendida |
|---|---|---|---|---|
| 1 | `mart_br_vs_ocde__gasto_educacao_timeseries` | gasto_educacao | ~2.000 | "Como evoluiu o gasto BR vs média OCDE 2010-2023?" |
| 2 | `mart_alfabetizacao__latam_2020s` | alfabetizacao | ~600 | "Onde está BR no contexto LATAM 2020-2024?" |
| 3 | `mart_indicadores__rankings_recente` | gasto + alfabetizacao | ~200 | "Top 10 países em cada indicador no ano mais recente" |
| 4 | `mart_gasto_x_alfabetizacao__correlacao` | ambos | ~1.500 | "Quanto gasto se correlaciona com alfabetização?" |
| 5 | `mart_br__evolucao_indicadores` | ambos | ~50 | "Trajetória BR ao longo do tempo (todos os indicadores)" |

### 4.2 Marts que dependem de novas Silvers ou ingestão (~3, futuros)

| # | Mart | Bloqueio |
|---|---|---|
| 6 | `mart_pisa_rankings` | Precisa R + microdados PISA + `int_indicadores__avaliacoes_estudantes` |
| 7 | `mart_ideb_municipal` | Precisa coletor INEP IDEB executado em produção |
| 8 | `mart_subnacional_br__indicadores_uf` | Precisa intermediate `int_indicadores__*_subnacional` (não existe) |

Estes ficam para Fase 3.5 quando os bloqueios forem resolvidos.

---

## 5. Indicadores derivados

Padronizados em macros, aplicados em vários marts:

### 5.1 Z-score dentro de grupo

```
zscore_<group>(value) = (value - mean(value over group)) / stddev(value over group)
```

Útil para BR vs OCDE: BR -1.5 σ significa 1.5 desvios-padrão abaixo da
média OCDE. Macro: `compute_zscore(value_col, partition_by='year')` com
particionamento explícito por ano (caso contrário compara entre anos
distintos, nonsense).

### 5.2 Percentil dentro de grupo

```
percentile_<group>(value) = percent_rank() over (partition by group order by value)
```

BR percentile=0.25 entre OCDE significa BR está no 25º percentil — pior
que 75% dos OCDE. Mais intuitivo que z-score para apresentação.

### 5.3 Gap em relação à referência

```
gap_to_<ref>(value, ref_value) = value - ref_value
gap_to_<ref>_pct(value, ref_value) = (value - ref_value) / ref_value * 100
```

`ref` pode ser BRA, mediana OCDE, top-quartil, etc. Comparações
absolutas e relativas separadas (% pode enganar quando ref é pequeno).

### 5.4 Tendência (slope linear N anos)

```
trend_Ny_slope(value) = covar(value, year) / var(year)  ; over (partition by country, last N years)
```

Slope positiva = crescendo; negativa = caindo. Combinada com R² para
filtrar tendências ruidosas. Pode ser implementada como `regr_slope` no
DuckDB (suporte SQL standard).

### 5.5 Diferença ano-a-ano

```
yoy_change(value) = value - lag(value, 1) over (partition by country, indicator order by year)
yoy_change_pct(value) = yoy_change / lag(value, 1) * 100
```

Útil para detectar choques (impacto pandemia 2020, ajustes fiscais).

### 5.6 Convergência/divergência relativa

```
gap_change(country) = gap_to_oecd_mean(year=t) - gap_to_oecd_mean(year=t-N)
```

Negativo = BR convergiu para OCDE; positivo = divergiu. Métrica chave
para análise de políticas públicas.

---

## 6. Padrões de modelagem

### 6.1 Estrutura típica de um mart timeseries

```sql
{{ config(materialized='table', tags=['gold', 'gasto']) }}

with base as (
    select * from {{ ref('int_indicadores__gasto_educacao') }}
    where year >= 2010
),

by_source as (
    select country_iso3, year,
        max(case when source='worldbank' then value end) as value_worldbank,
        max(case when source='unesco'    then value end) as value_unesco,
        max(case when source='oecd'      then value end) as value_oecd
    from base
    group by 1, 2
),

with_oecd_stats as (
    select b.*,
        avg(value_worldbank) over (partition by year) as oecd_mean,
        percentile_cont(0.25) within group (order by value_worldbank)
            over (partition by year) as oecd_p25
    from by_source b
    where country_iso3 in (select country_iso3
                           from {{ ref('int_geografia__paises_harmonizados') }}
                           where grouping like 'oecd%')
),

with_derived as (
    select w.*,
        {{ compute_zscore('value_worldbank', "year, 'oecd'") }} as zscore_in_oecd,
        value_worldbank - oecd_mean as gap_to_oecd_mean
    from with_oecd_stats w
)

select * from with_derived
order by country_iso3, year
```

Observações:
- **Filtros explícitos** (`year >= 2010`) ficam **no topo** para LIMIT
  early. DuckDB não predica push-down em todos os casos.
- **Pivoteamento por `source`** logo cedo — depois disso o mart é wide.
- **Window functions** com `partition by year` são essenciais — sem
  isso, comparações entre anos misturam contextos.
- **Subselect contra `paises_harmonizados`** com `grouping LIKE 'oecd%'`
  filtra OCDE+OCDE_G7 do nosso seed.

### 6.2 Estrutura de mart de ranking

```sql
{{ config(materialized='table', tags=['gold']) }}

with latest_year_per_indicator as (
    select indicator_id, max(year) as latest_year
    from {{ ref('int_indicadores__gasto_educacao') }}
    group by 1
),

ranked as (
    select g.*,
        rank() over (partition by g.indicator_id, g.year, g.source order by g.value desc)
            as rank_global,
        rank() over (partition by g.indicator_id, g.year, g.source, p.grouping order by g.value desc)
            as rank_in_grouping
    from {{ ref('int_indicadores__gasto_educacao') }} g
    inner join latest_year_per_indicator l
        on g.indicator_id = l.indicator_id and g.year = l.latest_year
    inner join {{ ref('int_geografia__paises_harmonizados') }} p
        using (country_iso3)
)

select * from ranked
```

### 6.3 Materialização: sempre `table`

Marts são leitos por consumidores diversos (BI, Streamlit, agentes,
FastAPI). Recomputar window functions a cada query é proibitivo.
`table` no DuckDB é fast-write, fast-read — não há ganho em usar
`view` aqui.

---

## 7. Estratégia de testes

### 7.1 Pirâmide na Fase 3

```
        /\
       /GE\         Suite Great Expectations: distribuicoes, correlacoes esperadas
      /----\        (5-10 expectativas, executadas no pre-publish da Fase 4)
     /  dbt \       
    /accepted\      Custom dbt test accepted_range para metricas plausibilidade
   /  range   \     
  /------------\    
 / dbt declare\     Tests existentes (not_null, unique, accepted_values, relationships)
/--------------\    Sao replicados em cada mart.
```

### 7.2 Testes obrigatórios por mart

Para todo mart com colunas de **valor original**:
- `not_null` em chaves (`country_iso3`, `year`).
- `accepted_range` em valores conforme indicador (% em [0, 100], anos
  em [1990, 2030], scores em range conhecido).

Para todo mart com **colunas derivadas**:
- `accepted_range` em z-score (≈ ±5).
- `accepted_range` em percentile_rank (∈ [0, 1]).
- `not_null` em gap quando ambos lados têm dado (lógica em `dbt_utils.expression_is_true`).

### 7.3 Custom test `accepted_range`

```sql
-- tests/generic/test_accepted_range.sql
{% test accepted_range(model, column_name, min_value=none, max_value=none, where=none) %}
    select {{ column_name }}
    from {{ model }}
    where ({{ column_name }} is not null)
    {% if where %} and {{ where }} {% endif %}
    {% if min_value is not none %} and {{ column_name }} < {{ min_value }} {% endif %}
    {% if max_value is not none %} and {{ column_name }} > {{ max_value }} {% endif %}
{% endtest %}
```

Aplicado a marts:
- `% PIB ∈ [0, 30]` (limite generoso; valores acima são erro de unidade).
- `literacy_rate ∈ [0, 100]`.
- `zscore ∈ [-5, 5]` (alerta, não erro — extremos são raros mas possíveis).

### 7.4 Suite Great Expectations mínima

- Distribuição de `value_worldbank` em `mart_br_vs_ocde__gasto_educacao_timeseries`:
  média ≈ 5%, desvio ≈ 1.5%.
- Correlação `value_worldbank × value_unesco` por país-ano: ρ > 0.95
  (deveriam bater perfeito, divergência indica bug).
- Cobertura: `count(distinct country_iso3) > 30` em cada mart cross-OCDE.

GE roda em pre-publish (gate manual antes de promover mart para Fase 4).
Não bloqueia builds incrementais.

---

## 8. Sequência de implementação

| Sprint | Duração | Entregáveis |
|---|---|---|
| **3.0 — Setup + macros** | 0.5 dia | `models/marts/` configurado em `dbt_project.yml`, macros `compute_zscore` / `compute_percentile_rank` / `compute_gap` / `compute_trend_slope` em `macros/derived/`. |
| **3.1 — Marts diretos** | 2 dias | Marts 1 (BR vs OCDE gasto timeseries) e 2 (alfabetização LATAM 2020s) implementados, testados, documentados. |
| **3.2 — Mart de rankings cross-indicador** | 1 dia | Mart 3 (rankings recente). |
| **3.3 — Marts de cruzamento** | 1.5 dia | Marts 4 (gasto x alfabetização correlação) e 5 (BR evolução indicadores). |
| **3.4 — Custom tests + GE** | 1 dia | `accepted_range` test, suite GE básica, integração com pytest. |
| **3.5 — OpenMetadata + dbt docs** | 1 dia | OpenMetadata apontado para DuckDB, descrições populadas, lineage navegável. |
| **3.6 — Conclusão** | 0.5 dia | `fase-3-conclusao.md`, atualização do `CLAUDE.md` se necessário. |
| **Total** | **~7 dias úteis** | (≈ 1.5 semanas) |

Encaixa na janela "semanas 8-9" do CLAUDE.md.

### 8.1 Ordem dentro de Sprint 3.1

Implementar Mart 1 primeiro (gasto BR vs OCDE), 100% até dbt test verde,
**depois** Mart 2 (alfabetização LATAM). Razão: o primeiro estabelece o
template (CTEs, macros derivadas, schema.yml) que o segundo só copia
adaptando filtros e fontes. Implementar paralelamente trava bugs em
duas frentes.

---

## 9. Riscos e mitigações

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| **Window functions lentas em DuckDB com volume médio** | Baixa | Médio | Marts < 5k linhas após filtragem; window OK. Se ficar lento, materializar intermediates auxiliares (`int_*__oecd_stats_per_year`). |
| **`grouping` na seed não cobrir todos os países OCDE** | Média | Baixo | Antes de Sprint 3.1, validar manualmente que os 38 países OCDE oficiais estão todos com `grouping LIKE 'oecd%'`. Atualizar seed se faltar. |
| **Z-score explodir quando stddev=0 (poucos países)** | Baixa | Médio | Macro `compute_zscore` usa `nullif(stddev, 0)`. Resultado vira NULL, não Infinity. |
| **Métrica derivada divergir entre marts** | Média | Médio | Macros centralizadas (Decisão 3.3). Code review em PRs valida que ninguém escreve cálculo inline. |
| **OECD data sub-conjunto temporal (2010-2021) limita comparações pré-2010** | Alta | Baixo | Marts de timeseries marcam `coverage_start_year` no schema.yml. Análises pré-2010 saem só com WB/UIS. |
| **Conflito de UNIT entre fontes (PT_B1GQ ≠ %)** | Baixa | Alto | Já resolvido em Silver (decimal coerente em todos `int_indicadores__*` para `%`). Mart confia na Silver. |

---

## 10. Critérios de aceitação

A Fase 3 está concluída quando todos os itens são verdadeiros:

- [ ] **Pelo menos 4 marts** publicados em `models/marts/` (mínimo: 1, 2, 3, 4 do catálogo §4.1).
- [ ] **`dbt build` verde** em < 30s incluindo todos os marts.
- [ ] **Cada mart com `description` e `columns:` no schema.yml** com unidade e fórmula.
- [ ] **Macros derivadas reusadas em ≥ 2 marts** (não escritas inline).
- [ ] **Custom test `accepted_range`** registrado e aplicado em ≥ 5 colunas.
- [ ] **`dbt docs generate` produz lineage** end-to-end (Bronze → Silver → Gold) sem nodes órfãos.
- [ ] **Suite Great Expectations mínima** com 5+ expectativas cobrindo distribuições.
- [ ] **`docs/phases/fase-3-conclusao.md`** declarando o trabalho final.
- [ ] **`CLAUDE.md` atualizado** se houver desvio de premissas.

---

## 11. Apêndice: convenções rápidas

### 11.1 Estrutura final esperada de `dbt_project/models/`

```
models/
├── staging/      (Fase 2 — 7 stagings)
├── intermediate/ (Fase 2 — 5 intermediates)
└── marts/        (Fase 3)
    ├── gasto/
    │   ├── mart_br_vs_ocde__gasto_educacao_timeseries.sql
    │   ├── mart_gasto__rankings_recente.sql
    │   └── schema.yml
    ├── alfabetizacao/
    │   ├── mart_alfabetizacao__latam_2020s.sql
    │   └── schema.yml
    ├── cross/
    │   ├── mart_gasto_x_alfabetizacao__correlacao.sql
    │   └── schema.yml
    └── pais/
        ├── mart_br__evolucao_indicadores.sql
        └── schema.yml
```

### 11.2 Macros derivadas em `macros/derived/`

```
macros/
├── harmonize_country.sql   (Fase 2)
├── safe_to_year.sql        (Fase 2)
└── derived/                (Fase 3)
    ├── compute_zscore.sql
    ├── compute_percentile_rank.sql
    ├── compute_gap.sql
    └── compute_trend_slope.sql
```

### 11.3 Convenção `schema.yml` para mart

```yaml
version: 2

models:
  - name: mart_br_vs_ocde__gasto_educacao_timeseries
    description: >
      Gasto publico em educacao (% PIB) por pais e ano para BR + OCDE.
      Pivoteado por fonte (worldbank/unesco/oecd) e enriquecido com
      estatisticas OCDE por ano (mean, p25, p75) e indicadores
      derivados (zscore, gap, trend).
    config:
      tags: ['gold', 'gasto']
    columns:
      - name: country_iso3
        description: ISO-3 do pais (BRA + 38 paises OCDE).
        tests:
          - not_null
      - name: year
        description: Ano da observacao (2010-2023).
        tests:
          - not_null
          - accepted_range:
              arguments:
                min_value: 2010
                max_value: 2030
      - name: value_worldbank
        description: "Valor da fonte World Bank (% PIB)."
        tests:
          - accepted_range:
              arguments:
                min_value: 0
                max_value: 30
      - name: zscore_in_oecd
        description: >
          Z-score do pais dentro do conjunto OCDE no mesmo ano.
          Formula: (value - oecd_mean) / oecd_std. NULL quando
          stddev=0 (so um pais com dado).
        tests:
          - accepted_range:
              arguments:
                min_value: -5
                max_value: 5
                where: "zscore_in_oecd is not null"
```

### 11.4 Comandos do dia-a-dia

```bash
# Construir so a Gold
DBT_PROFILES_DIR=. dbt run --select tag:gold

# Testar so a Gold
DBT_PROFILES_DIR=. dbt test --select tag:gold

# Desenvolver um mart isolado (build apenas suas deps)
DBT_PROFILES_DIR=. dbt build --select +mart_br_vs_ocde__gasto_educacao_timeseries

# Lineage HTML para revisao
DBT_PROFILES_DIR=. dbt docs generate && DBT_PROFILES_DIR=. dbt docs serve --port 8081
```

---

## Conclusão

A Fase 3 é a primeira camada do sistema que **responde perguntas
analíticas diretamente**. O esqueleto Silver da Fase 2 já carrega toda
a complexidade metodológica; aqui só fatiamos, estatística e cruzamos.

O risco maior **não é técnico** (DuckDB + dbt suportam tudo nativamente)
mas **conceitual**: definir bem a unidade analítica de cada mart e
documentar fórmulas com clareza. Marts mal-definidos tornam-se
"tabelas de despejo" que ninguém usa.

Por isso, a maior parte deste documento descreve **pergunta atendida**
e **convenções de metricas derivadas**, não arquivos a escrever.

Com o catálogo (§4) e os indicadores derivados padronizados (§5), o
desenvolvimento real cabe confortavelmente em **1.5 semanas de trabalho
solo**, terminando em uma Gold pronta para alimentar FastAPI (Fase 4)
e os agentes (Fase 5) sem retrabalho.

---

*Próximo documento ao fim do desenvolvimento: `fase-3-conclusao.md` —
seguindo o mesmo template de [`fase-2-conclusao.md`](./fase-2-conclusao.md).*
