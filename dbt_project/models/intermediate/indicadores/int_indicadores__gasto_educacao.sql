{{ config(materialized='table') }}

-- Indicador no schema canonico Silver: gasto publico em educacao como
-- % do PIB.
--
-- Fontes empilhadas via UNION ALL:
--   - World Bank  (SE.XPD.TOTL.GD.ZS)
--   - UNESCO UIS  (XGOVEXP.IMF)
-- Eurostat/OCDE adicionam dimensoes (ISCED, fonte de gasto, etc.) que
-- exigem filtragem rigorosa antes de empilhar -- ficam para Sprint 2.3.
--
-- Schema canonico Silver (replicado em todos int_indicadores__*):
-- country_iso3, year, value, unit, indicator_id, indicator_name, source,
-- source_indicator_id. INNER JOIN com paises harmonizados filtra
-- agregados regionais (AFE, EAS, WLD).

with worldbank_raw as (

    select
        country_iso3,
        year,
        value,
        cast('%_GDP' as varchar)             as unit,
        cast('GASTO_EDU_PIB' as varchar)     as indicator_id,
        cast('Gasto publico em educacao (% PIB)' as varchar) as indicator_name,
        cast('worldbank' as varchar)         as source,
        cast(indicator_native_id as varchar) as source_indicator_id
    from {{ ref('stg_worldbank__indicators') }}
    where indicator_native_id = 'SE.XPD.TOTL.GD.ZS'
      and value is not null
      and country_iso3 is not null
      and year is not null

),

unesco_raw as (

    {#
        Atencao: a UIS expoe DUAS metricas parecidas com nomes confusos:
          - XGDP.FSGOV   = Gasto educacao como % do PIB     <-- correto aqui
          - XGOVEXP.IMF  = Gasto educacao como % gasto govt total  (NAO comparavel)
        Validacao 2026-04-28: BRA 2020 XGDP.FSGOV=5.77 = WB 5.77 (match perfeito);
        XGOVEXP.IMF=12.5 e ~2x maior porque tem outro denominador.
    #}
    select
        country_iso3,
        year,
        value,
        cast('%_GDP' as varchar)             as unit,
        cast('GASTO_EDU_PIB' as varchar)     as indicator_id,
        cast('Gasto publico em educacao (% PIB)' as varchar) as indicator_name,
        cast('unesco' as varchar)            as source,
        cast(indicator_native_id as varchar) as source_indicator_id
    from {{ ref('stg_unesco__indicators') }}
    where indicator_native_id = 'XGDP.FSGOV'
      and value is not null
      and country_iso3 is not null
      and year is not null

),

unioned_raw as (
    select * from worldbank_raw
    union all
    select * from unesco_raw
),

deduped as (

    {#
        Dedup defensivo na chave natural (indicator_id, source, country, year).
        Atende a:
          - Bronze com periodos sobrepostos (ex.: glob captura '2010-2023'
            legado + '2000-2023' atual e duplica linhas).
          - Multiplas observacoes legitimas mesma chave nao existem.
        Nao agrega valores entre `source`s diferentes -- isso e proposito
        da union: cada fonte vira uma linha separada, permitindo
        comparar metodologias.
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
    from unioned_raw

)

select
    d.country_iso3,
    d.year,
    d.value,
    d.unit,
    d.indicator_id,
    d.indicator_name,
    d.source,
    d.source_indicator_id
from deduped as d
inner join {{ ref('int_geografia__paises_harmonizados') }} as paises
    on d.country_iso3 = paises.country_iso3
