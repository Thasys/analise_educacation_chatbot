{#
    Conversao defensiva de strings/timestamps em ano (INT).
    Cobre os formatos heterogeneos que aparecem nas fontes:
      "2023"          -> 2023        (World Bank, IPEA, CEPALSTAT)
      "2022-Q1"       -> 2022        (Eurostat tempo trimestral)
      "2022M03"       -> 2022        (Eurostat tempo mensal)
      "2024-09-01..." -> 2024        (IPEA VALDATA timestamp)

    Estrategia: extrair os 4 primeiros digitos consecutivos da
    representacao string e converter para int. Se nao houver 4
    digitos no inicio, retorna NULL (sera capturado por not_null
    nos testes da intermediate).
#}


{% macro safe_to_year(col) %}
    try_cast(regexp_extract(cast({{ col }} as varchar), '^([0-9]{4})', 1) as integer)
{% endmacro %}


{% macro safe_to_double(col) %}
{#
    Conversao defensiva de string em DOUBLE.
    Cobre marcadores de missing comuns:
      ".." / "..." / "-" -> NULL  (SIDRA)
      ""                  -> NULL  (CSV vazio)
    Numeros validos sao convertidos com try_cast.
#}
    try_cast(
      nullif(
        nullif(
          nullif(nullif(cast({{ col }} as varchar), '..'), '...'),
          '-'
        ),
        ''
      )
      as double
    )
{% endmacro %}
