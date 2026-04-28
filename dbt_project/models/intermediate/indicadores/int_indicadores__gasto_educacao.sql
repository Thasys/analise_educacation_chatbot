{{ config(materialized='table') }}

-- Primeiro indicador no schema canonico Silver: gasto publico em
-- educacao como % do PIB.
--
-- Fontes que cobrem este indicador:
--   - World Bank (SE.XPD.TOTL.GD.ZS) -- ja em staging
--   - UNESCO UIS, Eurostat, OCDE -- entrarao por UNION quando seus
--     coletores tiverem dataflow IDs validos (debito da Fase 1).
--
-- O schema desta tabela e o "contrato canonico" que sera replicado
-- em todos os int_indicadores__*: country_iso3, year, value, unit,
-- indicator_id, source. Pais filtrado contra a seed via INNER JOIN
-- com int_geografia__paises_harmonizados (drops aggregates como WLD).

with worldbank_raw as (

    select
        country_iso3,
        year,
        value,
        cast('%_GDP' as varchar)        as unit,
        cast('GASTO_EDU_PIB' as varchar) as indicator_id,
        cast('Gasto publico em educacao (% PIB)' as varchar) as indicator_name,
        cast('worldbank' as varchar)    as source,
        cast(indicator_native_id as varchar) as source_indicator_id
    from {{ ref('stg_worldbank__indicators') }}
    where indicator_native_id = 'SE.XPD.TOTL.GD.ZS'
      and value is not null
      and country_iso3 is not null
      and year is not null

),

worldbank as (

    {#
        Dedup defensivo: a Bronze pode conter parquets com periodos
        sobrepostos (ex.: '2010-2023' legado + '2000-2023' atual) e o
        glob de read_parquet acumula todos. A chave natural na fonte
        e (indicator, country, year), entao DISTINCT e suficiente -- nao
        existem duas observacoes legitimas para o mesmo trio.
    #}
    select distinct
        country_iso3,
        year,
        value,
        unit,
        indicator_id,
        indicator_name,
        source,
        source_indicator_id
    from worldbank_raw

)

{#
    UNION ALL com outras fontes quando staging delas existir:
      select ... from ref('stg_unesco__finance') where ...
      select ... from ref('stg_oecd__finance')   where ...
    Comentario em Jinja (nao SQL) para nao gerar deps fantasmas.
#}

select
    wb.country_iso3,
    wb.year,
    wb.value,
    wb.unit,
    wb.indicator_id,
    wb.indicator_name,
    wb.source,
    wb.source_indicator_id
from worldbank as wb
inner join {{ ref('int_geografia__paises_harmonizados') }} as paises
    on wb.country_iso3 = paises.country_iso3
