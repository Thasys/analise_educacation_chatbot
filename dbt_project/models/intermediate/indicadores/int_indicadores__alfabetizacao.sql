{{ config(materialized='table') }}

-- Indicador no schema canonico Silver: taxa de alfabetizacao da
-- populacao com 15 anos ou mais.
--
-- Fontes empilhadas (todas como literacy rate %, 0-100):
--   - World Bank (SE.ADT.LITR.ZS)  -- na pratica e a serie UIS LR.AG15T99
--                                     ressindicada (valores identicos).
--   - UNESCO UIS (LR.AG15T99)      -- fonte primaria UNESCO.
--   - IPEADATA   (PNADCA_TXA15MUF e ADH_T_ANALF15M) -- BR/UFs/municipios
--                                     em ANALFABETISMO; convertido para
--                                     alfabetizacao via (100 - value).
--
-- ATENCAO METODOLOGICA: as 3 fontes usam definicoes parecidas mas nao
-- identicas:
--   - UIS/WB: "people aged 15+ who can both read and write a short
--     simple statement on their everyday life" (definicao classica).
--   - IPEA PNADCA: derivado da PNAD Continua, autodeclaracao de
--     analfabetismo na pesquisa domiciliar.
--   - IPEA Atlas DH: derivado do Censo Demografico, autodeclaracao.
-- Diferencas de 0.5-1.5pp entre fontes para o mesmo BR/ano sao
-- esperadas e legitimas. NAO somar/mediar entre fontes -- cada uma e
-- uma linha separada com sua propria source.
--
-- Conversao IPEA: PNADCA_TXA15MUF e ADH_T_ANALF15M sao TAXAS DE
-- ANALFABETISMO. Para alinhar ao schema canonico (literacy rate),
-- convertemos via `100 - value`. Documentado em source_indicator_id
-- com sufixo `(inverted)`.
--
-- Schema canonico: country_iso3, year, value, unit, indicator_id,
-- indicator_name, source, source_indicator_id.
-- IPEA carrega Brasil + UFs/municipios; demais so country-level.
-- Por enquanto restringimos ao nivel pais (territory_level_name='Brasil')
-- para respeitar o schema country_iso3 da Silver. Subnacional e dimensao
-- ortogonal e ganhara seu proprio intermediate em Sprint 2.4+.

with worldbank_raw as (

    select
        country_iso3,
        year,
        value,
        cast('%' as varchar)                 as unit,
        cast('LITERACY_15M' as varchar)      as indicator_id,
        cast('Taxa de alfabetizacao 15+ (%)' as varchar) as indicator_name,
        cast('worldbank' as varchar)         as source,
        cast(indicator_native_id as varchar) as source_indicator_id
    from {{ ref('stg_worldbank__indicators') }}
    where indicator_native_id = 'SE.ADT.LITR.ZS'
      and value is not null
      and country_iso3 is not null
      and year is not null

),

unesco_raw as (

    select
        country_iso3,
        year,
        value,
        cast('%' as varchar)                 as unit,
        cast('LITERACY_15M' as varchar)      as indicator_id,
        cast('Taxa de alfabetizacao 15+ (%)' as varchar) as indicator_name,
        cast('unesco' as varchar)            as source,
        cast(indicator_native_id as varchar) as source_indicator_id
    from {{ ref('stg_unesco__indicators') }}
    where indicator_native_id = 'LR.AG15T99'
      and value is not null
      and country_iso3 is not null
      and year is not null

),

ipea_raw as (

    {#
        IPEA fornece TAXA DE ANALFABETISMO. Convertemos para alfabetizacao.
        Filtra apenas observacoes nivel Brasil (NIVNOME='Brasil') -- UFs
        e municipios entrarao em intermediate subnacional na Sprint 2.4.
    #}
    select
        cast('BRA' as varchar)               as country_iso3,
        year,
        100.0 - value                        as value,
        cast('%' as varchar)                 as unit,
        cast('LITERACY_15M' as varchar)      as indicator_id,
        cast('Taxa de alfabetizacao 15+ (%)' as varchar) as indicator_name,
        cast('ipea' as varchar)              as source,
        cast(series_code || ' (inverted)' as varchar) as source_indicator_id
    from {{ ref('stg_ipea__series') }}
    where series_code in ('PNADCA_TXA15MUF', 'ADH_T_ANALF15M')
      and territory_level_name = 'Brasil'
      and value is not null
      and year is not null

),

unioned_raw as (
    select * from worldbank_raw
    union all
    select * from unesco_raw
    union all
    select * from ipea_raw
),

deduped as (

    {#
        Dedup defensivo na chave natural (country, year, source, source_indicator_id).
        IPEA pode ter PNADCA + Atlas DH no mesmo ano (raros) -- ambos sao
        observacoes legitimas separadas porque tem source_indicator_id
        distinto.
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
