{{
    config(
        tags=['gold', 'avaliacoes'],
        meta={
            "indicator_namespace": "IDEB_*",
            "source_url": "https://download.inep.gov.br/educacao_basica/portal_ideb/"
        }
    )
}}

-- Mart Gold: IDEB Brasil, serie historica por etapa.
--
-- Consumido pelos agentes via `EduGatewayClient` nos endpoints
-- `/api/data/timeseries` e `/api/data/compare` quando `indicator`
-- e um dos:
--     IDEB_AI   -- anos iniciais do ensino fundamental
--     IDEB_AF   -- anos finais do ensino fundamental
--     IDEB_EM   -- ensino medio
--
-- Cobertura:
--   - IDEB_AI/IDEB_AF: 2005-2021 (9 anos, bienal)
--   - IDEB_EM:          2017-2021 (3 anos)
--
-- Granularidade: Brasil agregado, rede publica. Granularidade UF/
-- municipio fica para mart futuro (`mart_ideb__municipios_recentes`).

select
    country_iso3,
    case etapa
        when 'anos_iniciais_fund' then 'IDEB_AI'
        when 'anos_finais_fund'   then 'IDEB_AF'
        when 'ensino_medio'        then 'IDEB_EM'
    end as indicator,
    ano                  as year,
    nota_observada_br    as value,
    nota_meta_br         as meta_projetada,
    n_municipios_observados,
    'inep'               as source,
    ciclo_divulgacao_origem
from {{ ref('int_ideb__br_serie_historica') }}
order by indicator, year
