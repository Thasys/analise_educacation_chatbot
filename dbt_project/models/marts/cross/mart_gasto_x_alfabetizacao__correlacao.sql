{{ config(materialized='table', tags=['gold', 'cross']) }}

-- Mart: Cruzamento entre gasto educacao (% PIB) e alfabetizacao 15+
-- por pais e ano. Detecta paises com investimento alto + resultado
-- baixo (ineficiencia) ou vice-versa.
--
-- Pergunta atendida:
--   "Quanto gasto se converte em alfabetizacao? Que paises sao mais
--    eficientes? O Brasil esta acima ou abaixo da relacao tipica?"
--
-- Estrategia: INNER JOIN entre os dois intermediates por (country, year),
-- consolidando apenas value_canonical (preferindo UIS / WB pela
-- disponibilidade global). Se um pais nao tem ambos os indicadores no
-- mesmo ano, a linha cai fora.
--
-- Cobertura esperada: paises com dados em ambos -- LATAM e alguns
-- outros. OECD majoritariamente nao publica literacy_rate (assume-se
-- ~100%), entao mart fica focado em paises em desenvolvimento.

with gasto_canonical as (

    -- Pega valor canonico WB (que e identico ao UIS por construcao)
    select country_iso3, year, value as gasto_value
    from {{ ref('int_indicadores__gasto_educacao') }}
    where source = 'worldbank'
      and value is not null

),

alfab_canonical as (

    -- Para alfabetizacao priorizamos UNESCO (fonte primaria), WB e
    -- CEPALSTAT como backup. Se um pais so tem IPEA, e BR -- ja vem
    -- coberto pelas internacionais, entao IPEA nao adiciona linhas.
    select
        country_iso3,
        year,
        coalesce(
            max(case when source = 'unesco'    then value end),
            max(case when source = 'worldbank' then value end),
            max(case when source = 'cepalstat' then value end)
        ) as alfab_value
    from {{ ref('int_indicadores__alfabetizacao') }}
    where value is not null
    group by country_iso3, year

),

joined as (

    select
        g.country_iso3,
        g.year,
        g.gasto_value,
        a.alfab_value
    from gasto_canonical g
    inner join alfab_canonical a
        using (country_iso3, year)

),

with_country_info as (

    select
        j.*,
        p.name_pt as country_name,
        p.grouping
    from joined j
    inner join {{ ref('iso_3166_paises') }} p
        on j.country_iso3 = p.iso3

),

with_derived as (

    select
        wci.*,
        -- Razao alfabetizacao / gasto: "pontos de alfabetizacao por
        -- 1pp de gasto/PIB". Indicador grosso de eficiencia, nao
        -- causal -- alfabetizacao tem teto natural ~100, entao paises
        -- ja saturados parecem ineficientes mesmo gastando bem.
        case when gasto_value > 0
            then alfab_value / gasto_value
        end as efficiency_ratio,

        -- Z-score por ano de cada indicador (separados, nao bivariado)
        {{ compute_zscore('gasto_value',  'year') }} as zscore_gasto_year,
        {{ compute_zscore('alfab_value',  'year') }} as zscore_alfab_year,

        -- Diferenca entre os z-scores: positivo => alfabetizacao
        -- relativamente melhor que gasto (eficiencia relativa);
        -- negativo => gasto relativamente alto pra alfabetizacao baixa.
        ({{ compute_zscore('alfab_value', 'year') }})
            - ({{ compute_zscore('gasto_value', 'year') }})
            as zscore_diff_alfab_minus_gasto,

        -- Percentil em cada eixo
        {{ compute_percentile_rank('gasto_value',  'year') }} as percentile_gasto_year,
        {{ compute_percentile_rank('alfab_value',  'year') }} as percentile_alfab_year
    from with_country_info wci

)

select
    country_iso3,
    country_name,
    grouping,
    year,
    round(gasto_value, 4)            as gasto_value,
    round(alfab_value, 4)            as alfab_value,
    round(efficiency_ratio, 4)       as efficiency_ratio,
    round(zscore_gasto_year, 4)      as zscore_gasto_year,
    round(zscore_alfab_year, 4)      as zscore_alfab_year,
    round(zscore_diff_alfab_minus_gasto, 4) as zscore_diff_alfab_minus_gasto,
    round(percentile_gasto_year, 4)  as percentile_gasto_year,
    round(percentile_alfab_year, 4)  as percentile_alfab_year
from with_derived
order by country_iso3, year
