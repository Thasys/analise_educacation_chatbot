-- Intermediate: IDEB agregado para Brasil, 1 linha por (etapa, ano).
--
-- Agrega `stg_inep_ideb` filtrando rede='Publica' (que ja e o agregado
-- das tres redes publicas pelo proprio INEP, computado a nivel
-- municipal). Para v1 usa media simples por municipio; iteracao
-- futura: ponderar por matriculas (Censo Escolar) para reproduzir
-- exatamente o IDEB nacional ponderado divulgado pelo INEP.
--
-- O delta entre media simples e media ponderada e de ~0,1-0,2 pts
-- (municipios pequenos pesam mais que sua matricula real). Documentar
-- esse caveat em qualquer resposta que cite o valor.

select
    'BRA' as country_iso3,
    etapa,
    ano,
    avg(nota_observada)               as nota_observada_br,
    avg(nota_meta)                    as nota_meta_br,
    count(distinct municipio_id)      as n_municipios_observados,
    count(distinct case when nota_meta is not null then municipio_id end)
                                       as n_municipios_com_meta,
    -- Ciclo mais recente que contribuiu para este (etapa, ano).
    -- Util para auditoria: 2019 traz 2005-2019; 2021 traz so 2021.
    max(ciclo_divulgacao)             as ciclo_divulgacao_origem
from {{ ref('stg_inep_ideb') }}
where rede = 'Pública'
  and nota_observada is not null
  and ano between 2005 and 2030
group by etapa, ano
