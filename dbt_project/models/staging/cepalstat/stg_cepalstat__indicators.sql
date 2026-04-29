{{
    config(
        materialized='view',
        meta={
            "source_url": "https://api-cepalstat.cepal.org/cepalstat/api/v1/indicator/<ID>/data",
            "ingested_via": "data_pipeline.collectors.cepalstat.api_client.CepalstatCollector"
        }
    )
}}

-- Staging dos indicadores CEPALSTAT (CEPAL/ECLAC) via API REST v1.
-- O coletor ja resolveu os dim_* IDs em colunas canonicas
-- (year, sex, country_iso3, country_name) usando o endpoint /dimensions.
-- Aqui apenas tipamos e selecionamos a forma final.

with raw as (

    select *
    from read_parquet(
        '{{ var("bronze_root") }}/cepalstat/indicator_*/*/data.parquet',
        union_by_name = true
    )

)

select
    cast(indicator_id   as varchar)          as indicator_native_id,
    cast(indicator_name as varchar)          as indicator_name,
    cast(country_iso3   as varchar)          as country_iso3,
    cast(country_name   as varchar)          as country_name,
    cast(year           as integer)          as year,
    cast(value          as double)           as value,
    cast(sex            as varchar)          as sex,
    cast(source_id      as varchar)          as source_id,
    cast(notes_ids      as varchar)          as notes_ids
from raw
where year is not null
  and country_iso3 is not null
