{#
    compute_trend_slope — slope de uma regressao linear simples
    (value ~ year) computada como window function.

    Usa a funcao SQL standard `regr_slope(y, x)` (suportada em DuckDB).
    Slope > 0 = tendencia de crescimento; < 0 = decrescimo.

    Convenção: o slope e calculado dentro da particao (ex.: por pais),
    sobre a janela temporal completa disponivel naquela particao.

    Args:
      value_col: nome da coluna com valor (Y).
      year_col: nome da coluna com ano (X). Default 'year'.
      partition_by: particao (geralmente 'country_iso3').

    Exemplo (slope da serie do pais ao longo de todos os anos):
      select
        country_iso3, year, value,
        {{ compute_trend_slope('value', 'year', 'country_iso3') }} as trend_slope_full
      from t
#}

{% macro compute_trend_slope(value_col, year_col='year', partition_by='country_iso3') %}
    regr_slope({{ value_col }}, {{ year_col }})
        over (partition by {{ partition_by }})
{% endmacro %}


{% macro compute_trend_r2(value_col, year_col='year', partition_by='country_iso3') %}
{#
    R^2 da mesma regressao -- mede o quao linear e a tendencia.
    R^2 alto + slope nao-trivial = tendencia confiavel.
    R^2 baixo = serie ruidosa, slope nao deve ser interpretado.
#}
    regr_r2({{ value_col }}, {{ year_col }})
        over (partition by {{ partition_by }})
{% endmacro %}
