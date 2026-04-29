{{ config(materialized='table', tags=['gold', 'alfabetizacao']) }}

-- Mart: Taxa de alfabetizacao 15+ -- Brasil + LATAM, anos 2020+.
--
-- Pergunta atendida:
--   "Onde esta o BR no contexto LATAM em alfabetizacao recente?
--    Que paises LATAM lideram? Como BR esta evoluindo vs vizinhos?"
--
-- Recorte: BRA + 20 paises LATAM (grouping LIKE '%latam%'), anos
-- 2020-2024. Pivoteado por fonte (worldbank/unesco/cepalstat/ipea)
-- com value_canonical priorizando fontes internacionais (UIS) sobre
-- nacionais (IPEA), porque a comparabilidade entre paises e o foco.
--
-- IPEA cobre apenas BRA e ja foi convertido de analfabetismo na Silver.

with alfab as (
    select
        country_iso3,
        year,
        source,
        value
    from {{ ref('int_indicadores__alfabetizacao') }}
    where year >= 2020
),

-- Pivot por fonte
by_source as (
    select
        country_iso3,
        year,
        max(case when source = 'worldbank' then value end) as value_worldbank,
        max(case when source = 'unesco'    then value end) as value_unesco,
        max(case when source = 'cepalstat' then value end) as value_cepalstat,
        max(case when source = 'ipea'      then value end) as value_ipea
    from alfab
    group by 1, 2
),

-- Filtro analítico: BR + LATAM
target_countries as (
    select
        bs.*,
        coalesce(bs.value_unesco, bs.value_worldbank, bs.value_cepalstat) as value_canonical,
        p.name_pt as country_name,
        p.grouping
    from by_source bs
    inner join {{ ref('int_geografia__paises_harmonizados') }} pais
        on bs.country_iso3 = pais.country_iso3
    inner join {{ ref('iso_3166_paises') }} p
        on pais.country_iso3 = p.iso3
    where p.grouping like '%latam%'
),

-- Estatisticas LATAM por ano (incluindo BR; sao todos peers)
latam_stats_by_year as (
    select
        year,
        avg(value_canonical)               as latam_mean,
        median(value_canonical)            as latam_median,
        quantile_cont(value_canonical, 0.25) as latam_p25,
        quantile_cont(value_canonical, 0.75) as latam_p75,
        min(value_canonical)               as latam_min,
        max(value_canonical)               as latam_max,
        count(distinct country_iso3) filter (where value_canonical is not null) as latam_countries_with_data
    from target_countries
    group by year
),

-- Junta estatisticas
with_stats as (
    select tc.*, ls.* exclude (year)
    from target_countries tc
    left join latam_stats_by_year ls using (year)
),

-- Indicadores derivados
with_derived as (
    select
        ws.*,
        {{ compute_zscore('value_canonical', 'year') }} as zscore_in_latam_year,
        {{ compute_percentile_rank('value_canonical', 'year') }} as percentile_in_latam_year,
        case when latam_mean is not null
            then value_canonical - latam_mean
        end as gap_to_latam_mean,
        {{ compute_trend_slope('value_canonical', 'year', 'country_iso3') }} as trend_slope_2020s,
        -- Diferenca BR explicita (util para storytelling)
        case when country_iso3 != 'BRA' then
            value_canonical - max(case when country_iso3='BRA' then value_canonical end)
                              over (partition by year)
        end as gap_to_bra
    from with_stats ws
)

select
    country_iso3,
    country_name,
    grouping,
    year,
    value_worldbank,
    value_unesco,
    value_cepalstat,
    value_ipea,
    value_canonical,
    latam_mean,
    latam_median,
    latam_p25,
    latam_p75,
    latam_min,
    latam_max,
    latam_countries_with_data,
    zscore_in_latam_year,
    percentile_in_latam_year,
    gap_to_latam_mean,
    gap_to_bra,
    trend_slope_2020s
from with_derived
order by country_iso3, year
