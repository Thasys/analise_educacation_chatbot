{#
    compute_gap — diferenca entre valor de uma observacao e uma referencia
    calculada via window function (mean, median, percentile, etc.).

    Variantes:
      compute_gap_to_mean    : value - avg over (partition)
      compute_gap_to_median  : value - median over (partition)
      compute_gap_pct_to_mean: (value - avg) / avg * 100

    Args:
      value_col: nome da coluna com valor.
      partition_by: particao para calcular a referencia.

    Exemplo:
      select
        country_iso3, year, value,
        {{ compute_gap_to_mean('value', 'year') }}     as gap_to_year_mean,
        {{ compute_gap_pct_to_mean('value', 'year') }} as gap_pct_to_year_mean
      from t
#}

{% macro compute_gap_to_mean(value_col, partition_by) %}
    ({{ value_col }} - avg({{ value_col }}) over (partition by {{ partition_by }}))
{% endmacro %}


{% macro compute_gap_to_median(value_col, partition_by) %}
    ({{ value_col }} - median({{ value_col }}) over (partition by {{ partition_by }}))
{% endmacro %}


{% macro compute_gap_pct_to_mean(value_col, partition_by) %}
    case
      when avg({{ value_col }}) over (partition by {{ partition_by }}) > 0 then
        ({{ value_col }} - avg({{ value_col }}) over (partition by {{ partition_by }}))
        / avg({{ value_col }}) over (partition by {{ partition_by }}) * 100.0
      else null
    end
{% endmacro %}
