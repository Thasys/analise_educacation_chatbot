{{
    config(
        meta={
            "source_url": "https://download.inep.gov.br/educacao_basica/portal_ideb/planilhas_para_download/<ciclo>/divulgacao_<etapa>_municipios_<ciclo>.xlsx",
            "ingested_via": "data_pipeline.src.scripts.collect_ideb"
        }
    )
}}

-- Staging do IDEB municipal (INEP), formato longo.
--
-- Le 6 parquets bronze (3 etapas x 2 ciclos: 2019 e 2021) e converte o
-- formato wide do INEP -- onde cada ano observado/projetado e uma
-- coluna separada (VL_OBSERVADO_2005, ..., VL_OBSERVADO_2021,
-- VL_PROJECAO_2007, ..., VL_PROJECAO_2021) -- em formato longo: 1 linha
-- por (etapa, municipio, rede, ano), com nota observada e meta
-- projetada lado a lado quando ambos existem.
--
-- Cobertura:
--   - AI/AF: 2005-2021 observado, 2007-2021 metas
--   - EM:    2017-2021 observado, 2019-2021 metas
--     (EM municipal so passou a ser divulgado a partir de 2017)
--
-- Bronze preserva os XLSX integrais como strings (marcadores '-' do
-- INEP); a conversao para double usa `safe_to_double`, que trata
-- '-', '..', '' como NULL. O union_by_name=true acomoda diferencas
-- de schema entre ciclos (planilha 2021 tem 14-16 colunas; 2019 tem
-- 28-100 colunas, todas as historicas).
--
-- Granularidade: municipio x rede. Para Brasil/UF agregados, ver
-- `int_ideb__br_serie_historica`.

with raw_combined as (
    select *
    from read_parquet(
        '{{ var("bronze_root") }}/inep/ideb_*/*/data.parquet',
        union_by_name = true
    )
),

observado_long as (
    unpivot raw_combined
    on columns('^VL_OBSERVADO_\d{4}$')
    into
        name col_observado
        value valor_observado
),

projecao_long as (
    unpivot raw_combined
    on columns('^VL_PROJECAO_\d{4}$')
    into
        name col_projecao
        value valor_projecao
),

obs_norm as (
    select
        ETAPA as etapa_codigo,
        try_cast(CICLO_DIVULGACAO as integer) as ciclo_divulgacao,
        SG_UF as uf,
        try_cast(CO_MUNICIPIO as integer) as municipio_id,
        NO_MUNICIPIO as municipio_nome,
        REDE as rede,
        try_cast(regexp_extract(col_observado, '(\d{4})', 1) as integer) as ano,
        {{ safe_to_double('valor_observado') }} as nota_observada
    from observado_long
    where {{ safe_to_double('valor_observado') }} is not null
),

proj_norm as (
    select
        ETAPA as etapa_codigo,
        try_cast(CO_MUNICIPIO as integer) as municipio_id,
        REDE as rede,
        try_cast(regexp_extract(col_projecao, '(\d{4})', 1) as integer) as ano,
        {{ safe_to_double('valor_projecao') }} as nota_meta
    from projecao_long
    where {{ safe_to_double('valor_projecao') }} is not null
)

select
    obs.etapa_codigo,
    case obs.etapa_codigo
        when 'AI' then 'anos_iniciais_fund'
        when 'AF' then 'anos_finais_fund'
        when 'EM' then 'ensino_medio'
    end as etapa,
    obs.uf,
    obs.municipio_id,
    obs.municipio_nome,
    obs.rede,
    obs.ano,
    obs.nota_observada,
    p.nota_meta,
    obs.ciclo_divulgacao
from obs_norm obs
left join proj_norm p
    on obs.etapa_codigo = p.etapa_codigo
   and obs.municipio_id = p.municipio_id
   and obs.rede        = p.rede
   and obs.ano         = p.ano
