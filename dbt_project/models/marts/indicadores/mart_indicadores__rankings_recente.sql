{{ config(materialized='table', tags=['gold', 'rankings']) }}

-- Mart: Rankings cross-indicador no ano mais recente disponivel por
-- (indicador, fonte). Une todos os int_indicadores__* via UNION ALL,
-- pega so o ano mais recente, e calcula rankings global e por
-- agrupamento (oecd/latam/etc.).
--
-- Pergunta atendida:
--   "No ano mais recente, qual e o ranking dos paises em cada
--    indicador? Onde o Brasil esta ranqueado?"
--
-- Estrutura: long format (uma linha por indicador-pais-fonte). Util
-- para tabelas comparativas como:
--   "BRA: gasto educacao = 14º entre OCDE; alfabetizacao = 8º entre LATAM"

with all_indicators as (
    select 'GASTO_EDU_PIB' as indicator_id, * from {{ ref('int_indicadores__gasto_educacao') }}
    union all
    select 'LITERACY_15M' as indicator_id, * from {{ ref('int_indicadores__alfabetizacao') }}
),

-- Anos mais recentes por (indicador, source)
latest_year_per_indicator_source as (
    select indicator_id, source, max(year) as latest_year
    from all_indicators
    where value is not null
    group by 1, 2
),

-- Filtra apenas observacoes do ano mais recente para cada (indicador, source)
recent as (
    select a.country_iso3, a.year, a.value, a.unit, a.indicator_id,
           a.indicator_name, a.source
    from all_indicators a
    inner join latest_year_per_indicator_source l
        using (indicator_id, source)
    where a.year = l.latest_year
      and a.value is not null
),

-- Junta info do pais (grouping)
with_grouping as (
    select r.*,
        p.name_pt as country_name,
        p.grouping
    from recent r
    inner join {{ ref('iso_3166_paises') }} p
        on r.country_iso3 = p.iso3
),

-- Rankings global e por grouping
ranked as (
    select
        wg.*,
        rank() over (
            partition by indicator_id, year, source
            order by value desc
        ) as rank_global,
        count(*) over (
            partition by indicator_id, year, source
        ) as countries_global,
        rank() over (
            partition by indicator_id, year, source, grouping
            order by value desc
        ) as rank_in_grouping,
        count(*) over (
            partition by indicator_id, year, source, grouping
        ) as countries_in_grouping,
        {{ compute_percentile_rank('value', 'indicator_id, year, source', ascending=false) }} as percentile_rank_global
    from with_grouping wg
)

select
    indicator_id,
    indicator_name,
    source,
    country_iso3,
    country_name,
    grouping,
    year,
    round(value, 4) as value,
    unit,
    rank_global,
    countries_global,
    rank_in_grouping,
    countries_in_grouping,
    round(percentile_rank_global, 3) as percentile_rank_global
from ranked
order by indicator_id, source, rank_global
