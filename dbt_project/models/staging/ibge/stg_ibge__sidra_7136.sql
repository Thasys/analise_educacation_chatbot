{{
    config(
        materialized='view',
        meta={
            "source_url": "https://apisidra.ibge.gov.br/values/t/7136",
            "ingested_via": "data_pipeline.collectors.ibge.sidra_client.SidraCollector"
        }
    )
}}

-- Staging do IBGE SIDRA tabela 7136 (PNAD Continua Educacao).
-- Coluna `Valor` vem como string com marcadores '..', '...', '-' para
-- missing. Usa safe_to_double() para conversao defensiva.
-- Demais colunas sao categoricas (codigo + label IBGE) -- preservadas
-- como strings, com renomeacao para snake_case ASCII.
--
-- Fonte: API publica REST do SIDRA (apisidra.ibge.gov.br), JSON posicional.

with raw as (

    select *
    from read_parquet(
        '{{ var("bronze_root") }}/ibge/sidra_7136/*/data.parquet',
        union_by_name = true
    )

)

select
    cast("Nível Territorial (Código)" as varchar)  as territory_level_code,
    cast("Nível Territorial"           as varchar) as territory_level_name,
    cast("Brasil (Código)"             as varchar) as territory_code,
    cast("Brasil"                      as varchar) as territory_name,
    cast("Unidade de Medida (Código)"  as varchar) as unit_code,
    cast("Unidade de Medida"           as varchar) as unit_name,
    {{ safe_to_double('"Valor"') }}                as value,
    cast("Variável (Código)"           as varchar) as variable_code,
    cast("Variável"                    as varchar) as variable_name,
    {{ safe_to_year('"Ano (Código)"') }}           as year,
    cast("Sexo (Código)"               as varchar) as sex_code,
    cast("Sexo"                        as varchar) as sex_name,
    cast("Grupo de idade (Código)"     as varchar) as age_group_code,
    cast("Grupo de idade"              as varchar) as age_group_name
from raw
