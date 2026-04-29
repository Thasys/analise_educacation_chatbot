{{
    config(
        materialized='view',
        meta={
            "source_url": "http://www.ipeadata.gov.br/api/odata4/Metadados('<SERIE>')/Valores",
            "ingested_via": "data_pipeline.collectors.ipea.odata_client.IpeaDataCollector"
        }
    )
}}

-- Staging do IPEADATA OData v4. Empilha todas as series coletadas via
-- glob `bronze/ipea/serie_*/all/data.parquet`. Schema homogeneo:
--   SERCODIGO, VALDATA (timestamp tz), VALVALOR, NIVNOME, TERCODIGO

with raw as (

    select *
    from read_parquet(
        '{{ var("bronze_root") }}/ipea/serie_*/*/data.parquet',
        union_by_name = true
    )

)

select
    cast("SERCODIGO" as varchar)             as series_code,
    cast("VALDATA"   as timestamp)           as value_timestamp,
    extract(year from cast("VALDATA" as timestamp))::integer as year,
    cast("VALVALOR" as double)               as value,
    cast("NIVNOME"   as varchar)             as territory_level_name,
    cast("TERCODIGO" as varchar)             as territory_code
from raw
