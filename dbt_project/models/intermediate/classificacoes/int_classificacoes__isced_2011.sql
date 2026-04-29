{{ config(materialized='table') }}

-- Tabela canonica ISCED 2011 (UNESCO).
-- Snapshot da seed `isced_2011` com mapeamentos para apelidos de fontes
-- especificas (Eurostat usa `ED1`, OCDE usa `ISCED11_1`, etc.).
-- Permite JOIN consistente entre stagings que carregam o nivel ISCED
-- em formatos diferentes.

with seed_isced as (
    select * from {{ ref('isced_2011') }}
)

select
    isced_level,
    descricao_pt,
    descricao_en,
    -- Apelidos canonicos por fonte. Multiplas fontes adicionarao novos
    -- aliases via UNION em revisoes futuras.
    cast('ED' || isced_level as varchar)                  as eurostat_alias,
    cast('ISCED11_' || isced_level as varchar)            as oecd_alias,
    cast('L' || isced_level as varchar)                   as uis_alias
from seed_isced
