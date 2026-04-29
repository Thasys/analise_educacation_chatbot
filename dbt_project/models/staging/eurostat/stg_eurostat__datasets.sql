{{
    config(
        materialized='view',
        meta={
            "source_url": "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<DATASET>",
            "ingested_via": "data_pipeline.collectors.eurostat.jsonstat_client.EurostatCollector"
        }
    )
}}

-- Staging unificado dos datasets Eurostat (JSON-stat 2.0). Cada dataset
-- tem dimensoes especificas (educ_uoe_enrt01 inclui sex/worktime/sector;
-- educ_uoe_fine01 inclui sector/unit; edat_lfse_14 inclui age/wstatus).
-- O `union_by_name=true` empilha os parquets adicionando NULLs onde a
-- dimensao nao existe no dataset de origem; `dataset_code` e extraido
-- do filename para preservar a proveniencia.
--
-- Schema nucleo presente em TODOS:
--   freq, geo (ISO-2), time (string -- ano ou periodo trimestral/mensal),
--   OBS_VALUE, OBS_STATUS

with raw as (

    select *
    from read_parquet(
        '{{ var("bronze_root") }}/eurostat/dataset_*/*/data.parquet',
        union_by_name = true,
        filename      = true
    )

)

select
    -- 'C:\...\data\bronze\eurostat\dataset_educ_uoe_enrt01\2010-2023\data.parquet'
    -- -> 'educ_uoe_enrt01'
    regexp_extract(
        replace(cast(filename as varchar), '\', '/'),
        'eurostat/dataset_([^/]+)/',
        1
    )                                                  as dataset_code,
    cast(freq    as varchar)                           as freq,
    cast(geo     as varchar)                           as country_iso2_raw,
    cast(time    as varchar)                           as period_raw,
    {{ safe_to_year('time') }}                         as year,
    cast(OBS_VALUE as double)                          as value,
    cast(OBS_STATUS as varchar)                        as obs_status,
    -- Dimensoes opcionais (NULL quando o dataset nao as tem):
    cast(unit    as varchar)                           as unit,
    cast(sex     as varchar)                           as sex,
    cast(age     as varchar)                           as age_group,
    cast(isced11 as varchar)                           as isced_alias,
    cast(sector  as varchar)                           as sector,
    cast(worktime as varchar)                          as worktime,
    cast(wstatus as varchar)                           as wstatus
from raw
