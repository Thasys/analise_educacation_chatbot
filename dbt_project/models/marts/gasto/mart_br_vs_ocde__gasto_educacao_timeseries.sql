{{ config(materialized='table', tags=['gold', 'gasto']) }}

-- Mart: Gasto publico em educacao (% PIB) -- Brasil + OCDE em serie
-- temporal, com indicadores derivados (z-score, percentil, gap, trend).
--
-- Pergunta atendida:
--   "Como o gasto BR em educacao se compara com OCDE ao longo do tempo?
--    BR esta convergindo ou divergindo da media OCDE?
--    Em que percentil OCDE o BR fica em cada ano?"
--
-- Recorte: Brasil + 38 paises OCDE (incluindo OCDE-G7 e LATAM-OCDE),
-- 2010-2023. Filtragem por grouping LIKE '%oecd%' captura os 3
-- subconjuntos analiticos (`oecd`, `oecd_g7`, `latam_oecd`).
--
-- Pivoteamento por fonte: cada (country, year) tem 3 valores possiveis
-- (worldbank, unesco, oecd). value_canonical = coalesce do WB com UIS
-- (sao identicos por construcao -- WB ressindica UIS).
--
-- Cobertura temporal: 2010-2023. WB/UIS cobrem todo o periodo; OECD
-- so a partir de 2010 e tipicamente atrasa ~1 ano em relacao aos
-- outros (2022-2023 podem estar NULL).

with gasto as (
    select
        country_iso3,
        year,
        source,
        value
    from {{ ref('int_indicadores__gasto_educacao') }}
    where year >= 2010
),

-- Pivot por fonte
by_source as (
    select
        country_iso3,
        year,
        max(case when source = 'worldbank' then value end) as value_worldbank,
        max(case when source = 'unesco'    then value end) as value_unesco,
        max(case when source = 'oecd'      then value end) as value_oecd
    from gasto
    group by 1, 2
),

-- Filtro analítico: BR + OCDE
target_countries as (
    select
        bs.*,
        coalesce(bs.value_worldbank, bs.value_unesco) as value_canonical,
        p.name_pt as country_name,
        p.grouping
    from by_source bs
    inner join {{ ref('int_geografia__paises_harmonizados') }} pais
        on bs.country_iso3 = pais.country_iso3
    inner join {{ ref('iso_3166_paises') }} p
        on pais.country_iso3 = p.iso3
    where p.grouping like '%oecd%'
       or pais.country_iso3 = 'BRA'
),

-- Estatisticas OCDE por ano (excluindo BR para nao viesar)
oecd_stats_by_year as (
    select
        year,
        avg(value_canonical) filter (where country_iso3 != 'BRA') as oecd_mean,
        median(value_canonical) filter (where country_iso3 != 'BRA') as oecd_median,
        quantile_cont(value_canonical, 0.25) filter (where country_iso3 != 'BRA') as oecd_p25,
        quantile_cont(value_canonical, 0.75) filter (where country_iso3 != 'BRA') as oecd_p75,
        count(distinct country_iso3) filter (where country_iso3 != 'BRA' and value_canonical is not null) as oecd_countries_with_data
    from target_countries
    group by year
),

-- Junta estatisticas de volta
with_stats as (
    select
        tc.*,
        os.oecd_mean,
        os.oecd_median,
        os.oecd_p25,
        os.oecd_p75,
        os.oecd_countries_with_data
    from target_countries tc
    left join oecd_stats_by_year os using (year)
),

-- Indicadores derivados (window functions)
with_derived as (
    select
        ws.*,
        {{ compute_zscore('value_canonical', 'year') }} as zscore_in_oecd_year,
        {{ compute_percentile_rank('value_canonical', 'year') }} as percentile_in_oecd_year,
        case
            when oecd_mean is not null then value_canonical - oecd_mean
        end as gap_to_oecd_mean,
        case
            when oecd_mean is not null and oecd_mean > 0
                then (value_canonical - oecd_mean) / oecd_mean * 100.0
        end as gap_pct_to_oecd_mean,
        {{ compute_trend_slope('value_canonical', 'year', 'country_iso3') }} as trend_slope_full_period,
        {{ compute_trend_r2('value_canonical', 'year', 'country_iso3') }} as trend_r2_full_period
    from with_stats ws
)

select
    country_iso3,
    country_name,
    grouping,
    year,
    value_worldbank,
    value_unesco,
    value_oecd,
    value_canonical,
    oecd_mean,
    oecd_median,
    oecd_p25,
    oecd_p75,
    oecd_countries_with_data,
    zscore_in_oecd_year,
    percentile_in_oecd_year,
    gap_to_oecd_mean,
    gap_pct_to_oecd_mean,
    trend_slope_full_period,
    trend_r2_full_period
from with_derived
order by country_iso3, year
