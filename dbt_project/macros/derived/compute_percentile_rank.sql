{#
    compute_percentile_rank — percentil dentro de uma particao.

    Retorno em [0, 1]:
      0.0 = pior valor da particao
      1.0 = melhor valor da particao
      0.5 = mediana

    Args:
      value_col: nome da coluna com valor.
      partition_by: lista de colunas que delimitam o grupo.
      ascending: se True (default), maior valor = percentil mais alto.
                 Para "indicador onde menos e melhor" (ex.: taxa de
                 evasao), passar ascending=False para inverter.

    Exemplo:
      select
        country_iso3, year, value,
        {{ compute_percentile_rank('value', 'year') }} as percentile_global_year
      from t
#}

{% macro compute_percentile_rank(value_col, partition_by, ascending=true) %}
    {%- if ascending -%}
    percent_rank() over (partition by {{ partition_by }} order by {{ value_col }} asc)
    {%- else -%}
    percent_rank() over (partition by {{ partition_by }} order by {{ value_col }} desc)
    {%- endif -%}
{% endmacro %}
