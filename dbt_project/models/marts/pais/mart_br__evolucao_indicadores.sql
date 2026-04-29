{{ config(materialized='table', tags=['gold', 'br']) }}

-- Mart: Evolucao temporal de TODOS os indicadores Silver para Brasil,
-- em formato long (uma linha por indicador-fonte-source_indicator_id-ano).
-- Inclui posicao relativa de BR no contexto OCDE/LATAM no mesmo ano.
--
-- Pergunta atendida:
--   "Mostre toda a trajetoria do Brasil ao longo dos anos: gasto,
--    alfabetizacao, em todas as fontes, com posicao relativa em
--    OCDE e LATAM."
--
-- Util para analises longitudinais e dashboards de "perfil-pais Brasil".
--
-- Cobertura: 2000-2024+ dependendo da fonte. IPEA pode ter 2 series por
-- ano (PNADCA + Atlas DH); ambas aparecem como linhas distintas via
-- source_indicator_id.

with all_indicators as (

    select
        'GASTO_EDU_PIB' as indicator_id,
        'Gasto publico em educacao (% PIB)' as indicator_name,
        country_iso3, year, value, unit, source, source_indicator_id
    from {{ ref('int_indicadores__gasto_educacao') }}
    where value is not null

    union all

    select
        'LITERACY_15M' as indicator_id,
        'Taxa de alfabetizacao 15+ (%)' as indicator_name,
        country_iso3, year, value, unit, source, source_indicator_id
    from {{ ref('int_indicadores__alfabetizacao') }}
    where value is not null

),

-- Apenas BR, todos source_indicator_id preservados (ex.: IPEA pode ter
-- PNADCA e Atlas DH no mesmo ano).
br_only as (
    select * from all_indicators where country_iso3 = 'BRA'
),

-- Para ranking comparativo, agregamos um valor unico por
-- (pais, indicador, fonte, ano) -- usa MAX quando ha multiplas series
-- (caso IPEA com PNADCA + Atlas DH). Sem isso, o country apareceria 2x
-- no partition de rank() e o JOIN explodiria em cartesiano.
deduped_for_rank as (
    select
        indicator_id, source, country_iso3, year,
        max(value) as value
    from all_indicators
    group by 1, 2, 3, 4
),

-- Estatisticas globais por (indicador, fonte, ano)
global_stats as (
    select
        indicator_id, source, year,
        avg(value) as global_mean,
        median(value) as global_median,
        count(distinct country_iso3) as countries_with_data
    from deduped_for_rank
    group by 1, 2, 3
),

-- BR ranking dentro de OCDE
ocde_rank as (
    select
        d.indicator_id, d.source, d.year,
        rank() over (
            partition by d.indicator_id, d.source, d.year
            order by d.value desc
        ) as rank_in_ocde,
        count(*) over (
            partition by d.indicator_id, d.source, d.year
        ) as countries_in_ocde
    from deduped_for_rank d
    inner join {{ ref('iso_3166_paises') }} p
        on d.country_iso3 = p.iso3
    where p.grouping like '%oecd%' or p.iso3 = 'BRA'
    qualify d.country_iso3 = 'BRA'
),

-- BR ranking dentro de LATAM
latam_rank as (
    select
        d.indicator_id, d.source, d.year,
        rank() over (
            partition by d.indicator_id, d.source, d.year
            order by d.value desc
        ) as rank_in_latam,
        count(*) over (
            partition by d.indicator_id, d.source, d.year
        ) as countries_in_latam
    from deduped_for_rank d
    inner join {{ ref('iso_3166_paises') }} p
        on d.country_iso3 = p.iso3
    where p.grouping like '%latam%'
    qualify d.country_iso3 = 'BRA'
)

select
    br.indicator_id,
    br.indicator_name,
    br.source,
    br.source_indicator_id,
    br.year,
    round(br.value, 4)                         as value_br,
    br.unit,
    round(gs.global_mean, 4)                   as global_mean,
    round(gs.global_median, 4)                 as global_median,
    gs.countries_with_data                     as countries_global,
    round(br.value - gs.global_mean, 4)        as gap_to_global_mean,
    ocde.rank_in_ocde,
    ocde.countries_in_ocde,
    latam.rank_in_latam,
    latam.countries_in_latam
from br_only br
left join global_stats gs
    using (indicator_id, source, year)
left join ocde_rank ocde
    on  br.indicator_id = ocde.indicator_id
    and br.source       = ocde.source
    and br.year         = ocde.year
left join latam_rank latam
    on  br.indicator_id = latam.indicator_id
    and br.source       = latam.source
    and br.year         = latam.year
order by br.indicator_id, br.source, br.year, br.source_indicator_id
