{{
    config(
        materialized='view',
        meta={
            "source_url": "https://api.uis.unesco.org/api/public/data/indicators",
            "ingested_via": "data_pipeline.collectors.unesco.uis_rest_client.UisRestCollector"
        }
    )
}}

-- Staging do UNESCO UIS Data API publica (REST, 2026+).
-- Glob sobre `bronze/unesco/indicator_*/<periodo>/data.parquet` -- todos
-- compartilham o schema simples retornado pelo /data/indicators:
--   indicatorId, geoUnit, year, value, magnitude, qualifier

with raw as (

    select *
    from read_parquet(
        '{{ var("bronze_root") }}/unesco/indicator_*/*/data.parquet',
        union_by_name = true
    )

)

select
    cast("indicatorId" as varchar)        as indicator_native_id,
    cast("geoUnit"     as varchar)        as country_iso3,
    cast("year"        as integer)        as year,
    cast("value"       as double)         as value,
    cast("magnitude"   as varchar)        as magnitude,
    cast("qualifier"   as varchar)        as qualifier
from raw
