{{ config(materialized='table') }}

-- Subset da seed iso_3166_paises restrito aos paises efetivamente
-- presentes em alguma fonte da Bronze. Funciona como tabela de
-- referencia "viva" para joins downstream e como filtro de agregados
-- (AFE, EAS, WLD do World Bank, por exemplo, ficam de fora).
--
-- Atualmente cobre apenas World Bank; sera expandido (UNION) conforme
-- novas fontes entrem em staging.

with worldbank_countries as (

    select distinct country_iso3
    from {{ ref('stg_worldbank__indicators') }}
    where country_iso3 is not null

),

unesco_countries as (

    select distinct country_iso3
    from {{ ref('stg_unesco__indicators') }}
    where country_iso3 is not null

),

union_observed as (

    select country_iso3 from worldbank_countries
    union
    select country_iso3 from unesco_countries

)

select
    seed.iso2,
    seed.iso3                              as country_iso3,
    seed.name_pt,
    seed.name_en,
    seed.un_m49,
    seed.grouping
from {{ ref('iso_3166_paises') }} as seed
inner join (
    select distinct country_iso3 from union_observed
) as obs
    on seed.iso3 = obs.country_iso3
