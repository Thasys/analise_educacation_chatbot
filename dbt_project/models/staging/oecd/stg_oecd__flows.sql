{{
    config(
        materialized='view',
        meta={
            "source_url": "https://sdmx.oecd.org/public/rest/data/<FLOW_REF>",
            "ingested_via": "data_pipeline.collectors.oecd.sdmx_client.OecdSdmxCollector"
        }
    )
}}

-- Staging unificado dos dataflows OCDE (SDMX-JSON 2.0). Cada dataflow
-- tem dimensoes especificas alem do nucleo SDMX. O nucleo:
--   REF_AREA (ISO-3), TIME_PERIOD, OBS_VALUE, OBS_STATUS,
--   MEASURE, EDUCATION_LEV, UNIT_MEASURE
-- Especificas (variam): EXP_SOURCE, EXP_DESTINATION, EXPENDITURE_TYPE,
-- PRICE_BASE, Q_SHEET, BASE_PER, etc.
--
-- O `flow_code` e extraido do path para preservar proveniencia.

with raw as (

    select *
    from read_parquet(
        '{{ var("bronze_root") }}/oecd/flow_*/*/data.parquet',
        union_by_name = true,
        filename      = true
    )

)

select
    -- 'C:\...\bronze\oecd\flow_oecd_edu_imep_dsd_eag_uoe_fin_df_uoe_indic_fin_gdp_1_0\2010-2023\data.parquet'
    -- -> 'flow_oecd_edu_imep_dsd_eag_uoe_fin_df_uoe_indic_fin_gdp_1_0'
    regexp_extract(
        replace(cast(filename as varchar), '\', '/'),
        'oecd/(flow_[^/]+)/',
        1
    )                                                       as flow_code,
    cast(REF_AREA       as varchar)                         as country_iso3,
    cast(TIME_PERIOD    as varchar)                         as period_raw,
    {{ safe_to_year('TIME_PERIOD') }}                       as year,
    cast(OBS_VALUE      as double)                          as value,
    cast(OBS_STATUS     as varchar)                         as obs_status,
    cast(MEASURE        as varchar)                         as measure,
    cast(EDUCATION_LEV  as varchar)                         as education_level_alias,
    cast(UNIT_MEASURE   as varchar)                         as unit_measure,
    cast(UNIT_MULT      as varchar)                         as unit_multiplier,
    cast(PRICE_BASE     as varchar)                         as price_base,
    -- Dimensoes opcionais (NULL quando o dataflow nao as tem):
    cast(EXP_SOURCE     as varchar)                         as exp_source,
    cast(EXP_DESTINATION as varchar)                        as exp_destination,
    cast(EXPENDITURE_TYPE as varchar)                       as expenditure_type
from raw
