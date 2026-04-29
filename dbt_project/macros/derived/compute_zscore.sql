{#
    compute_zscore — z-score dentro de uma particao.

    Formula: (value - mean) / stddev_samp
    Particionamento usual: por (year, group) -- nunca compare valores
    de anos diferentes na mesma normalizacao.

    Uso de `nullif(stddev, 0)` evita divisao por zero quando ha so um
    pais com valor naquela particao (resulta em NULL).

    Args:
      value_col: nome da coluna com valor (ex.: 'value_worldbank').
      partition_by: lista de colunas que delimitam o grupo (ex.: 'year, grouping').

    Exemplo:
      select
        country_iso3, year, value,
        {{ compute_zscore('value', 'year') }} as zscore_global_year
      from t
#}

{% macro compute_zscore(value_col, partition_by) %}
    case
      when stddev_samp({{ value_col }}) over (partition by {{ partition_by }}) > 0 then
        ({{ value_col }} - avg({{ value_col }}) over (partition by {{ partition_by }}))
        / stddev_samp({{ value_col }}) over (partition by {{ partition_by }})
      else null
    end
{% endmacro %}
