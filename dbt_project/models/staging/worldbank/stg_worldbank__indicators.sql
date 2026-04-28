{{
    config(
        materialized='view',
        meta={
            "source_url": "https://api.worldbank.org/v2/country/all/indicator/<INDICATOR>",
            "ingested_via": "data_pipeline.collectors.worldbank.api_client.WorldBankCollector"
        }
    )
}}

-- Staging do World Bank Indicators API.
-- Le todos os parquets sob bronze/worldbank/indicator_*/<periodo>/data.parquet
-- via glob e empilha (todos compartilham schema homogeneo do coletor).
-- Campo `value` ja vem como float64 do coletor; demais como string.
-- Aqui aplicamos casts conservadores e extraimos `year` da coluna `date`.
--
-- Fonte: API REST publica do World Bank (v2). Sem autenticacao.

with raw as (

    select *
    from read_parquet(
        '{{ var("bronze_root") }}/worldbank/indicator_*/*/data.parquet',
        union_by_name = true
    )

)

select
    cast(indicator_id   as varchar) as indicator_native_id,
    cast(indicator_name as varchar) as indicator_name,
    cast(country_id     as varchar) as country_iso2_raw,
    cast(country_iso3   as varchar) as country_iso3,
    cast(country_name   as varchar) as country_name_raw,
    {{ safe_to_year('date') }}      as year,
    cast(value          as double)  as value,
    cast(unit           as varchar) as unit,
    cast(obs_status     as varchar) as obs_status,
    cast(decimal        as integer) as decimal_precision
from raw
