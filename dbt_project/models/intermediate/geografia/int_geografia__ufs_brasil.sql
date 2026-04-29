{{ config(materialized='table') }}

-- Tabela canonica de UFs do Brasil (27 estados + DF).
-- Snapshot da seed `ibge_ufs` enriquecida com flags de presenca em
-- alguma fonte da Bronze (atualmente: SIDRA + IPEA por presenca de
-- territory_code de 2 digitos).

with seed_ufs as (
    select * from {{ ref('ibge_ufs') }}
),

-- UFs efetivamente presentes em IPEADATA (NIVNOME='Estados').
ipea_ufs as (
    select distinct territory_code as uf_code
    from {{ ref('stg_ipea__series') }}
    where territory_level_name = 'Estados'
      and territory_code is not null
      and length(territory_code) = 2
)

select
    seed_ufs.uf_code,
    seed_ufs.sigla,
    seed_ufs.nome,
    seed_ufs.regiao_codigo,
    seed_ufs.regiao_nome,
    cast('BRA' as varchar)                                    as country_iso3,
    case when ipea_ufs.uf_code is not null then true else false end as observed_in_ipea
from seed_ufs
left join ipea_ufs on seed_ufs.uf_code = ipea_ufs.uf_code
