{{ config(materialized='table') }}

-- Indicador no schema canonico Silver: gasto publico em educacao como
-- % do PIB.
--
-- Fontes empilhadas via UNION ALL:
--   - World Bank  (SE.XPD.TOTL.GD.ZS)
--   - UNESCO UIS  (XGDP.FSGOV)
--   - OCDE EAG    (DSD_EAG_UOE_FIN@DF_UOE_INDIC_FIN_GDP)
--
-- OCDE precisa de filtros rigorosos -- o dataflow GDP traz ~100k linhas
-- com varias combinacoes de (ISCED nivel, fonte de financiamento, tipo
-- de gasto, base de preco). A combinacao canonica para "gasto governo
-- geral em educacao % PIB":
--    education_level_alias = 'ISCED11_1T8'  (todos os niveis)
--    unit_measure          = 'PT_B1GQ'      (% PIB nominal)
--    exp_source            = 'S13'          (governo geral)
--    expenditure_type      = 'DIR_EXP'      (gasto direto)
--    exp_destination       = 'INST_EDU'     (todas as instituicoes
--                                            educacionais; INST_EDU_PUB
--                                            seria so publicas, viesado).
--
-- Eurostat: dataset `educ_uoe_fine01` traz so absolutos (MIO_EUR/PPS/NAC),
-- nao % PIB. Para incluir Eurostat seria preciso adicionar coletor de
-- `t2020_42` ou similar -- adiada para Sprint 2.4.
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

oecd_raw as (

    {#
        Filtro canonico no flow GDP da EAG. NOTA metodologica: a OCDE usa
        UOE (UNESCO-OECD-Eurostat) coleta com definicoes propias de
        contas nacionais, parcialmente diferente do GFS do FMI usado pelo
        WB e UIS. Esperar diferencas de 0.5-1.5pp entre fontes para o
        mesmo pais/ano e legitimo metodologicamente.
        Validacao BRA 2010: WB=5.96, UIS=5.96, OCDE=4.88 -- divergencia de
        ~1pp consistente com base diferente.
    #}
    select
        country_iso3,
        year,
        value,
        cast('%_GDP' as varchar)             as unit,
        cast('GASTO_EDU_PIB' as varchar)     as indicator_id,
        cast('Gasto publico em educacao (% PIB)' as varchar) as indicator_name,
        cast('oecd' as varchar)              as source,
        cast(measure || '|' || education_level_alias as varchar) as source_indicator_id
    from {{ ref('stg_oecd__flows') }}
    where flow_code like 'flow_oecd_edu_imep_dsd_eag_uoe_fin_df_uoe_indic_fin_gdp%'
      and education_level_alias = 'ISCED11_1T8'
      and unit_measure = 'PT_B1GQ'
      and exp_source = 'S13'
      and expenditure_type = 'DIR_EXP'
      and exp_destination = 'INST_EDU'
      and value is not null
      and country_iso3 is not null
      and year is not null

),

unioned_raw as (
    select * from worldbank_raw
    union all
    select * from unesco_raw
    union all
    select * from oecd_raw
),

deduped as (

    {#
        Dedup defensivo na chave natural (indicator_id, source, country, year).
        Atende a:
          - Bronze com periodos sobrepostos (ex.: glob captura '2010-2023'
            legado + '2000-2023' atual e duplica linhas).
          - OCDE pode ter linhas redundantes em outras dimensoes nao
            filtradas (ex.: EXP_DESTINATION) -- DISTINCT consolida.
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
