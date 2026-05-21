-- Indicador no schema canonico Silver: IDEB Brasil, por etapa.
--
-- Reusa a agregacao Brasil pronta em `int_ideb__br_serie_historica`
-- (em `intermediate/avaliacoes/`) e mapeia para o schema canonico
-- adotado pelas demais intermediates de indicadores
-- (country_iso3, year, value, unit, indicator_id, indicator_name,
-- source, source_indicator_id).
--
-- Indicadores canonicos publicados:
--   - IDEB_AI: anos iniciais do ensino fundamental
--   - IDEB_AF: anos finais do ensino fundamental
--   - IDEB_EM: ensino medio
--
-- Cobertura: AI/AF 2005-2021 (bienal); EM 2017-2021.
-- Fonte: INEP, planilhas de divulgacao do IDEB municipal (ciclos
-- 2019 e 2021). Granularidade: pais (BRA). UF e municipio ficam em
-- mart proprio (futuro).
--
-- Unidade: 'pontos' na escala 0-10 do IDEB.

select
    country_iso3,
    ano                                                              as year,
    nota_observada_br                                                as value,
    cast('pontos' as varchar)                                        as unit,
    case etapa
        when 'anos_iniciais_fund' then 'IDEB_AI'
        when 'anos_finais_fund'   then 'IDEB_AF'
        when 'ensino_medio'        then 'IDEB_EM'
    end                                                              as indicator_id,
    case etapa
        when 'anos_iniciais_fund' then 'IDEB - Anos Iniciais do Ensino Fundamental'
        when 'anos_finais_fund'   then 'IDEB - Anos Finais do Ensino Fundamental'
        when 'ensino_medio'        then 'IDEB - Ensino Medio'
    end                                                              as indicator_name,
    cast('inep' as varchar)                                          as source,
    'VL_OBSERVADO_' || cast(ano as varchar)                          as source_indicator_id
from {{ ref('int_ideb__br_serie_historica') }}
