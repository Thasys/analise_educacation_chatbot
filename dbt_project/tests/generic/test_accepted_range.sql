{#
    Custom dbt test: valida que valores em uma coluna estao dentro de
    um intervalo numerico esperado. Util para detectar bugs de unidade
    (ex.: % chegando como fracao 0-1 ou como pp 0-100), valores fora
    de escala ou metricas derivadas escapando do range plausivel.

    Args:
        model:       (auto) tabela/modelo a testar.
        column_name: (auto) coluna a testar.
        min_value:   limite inferior inclusivo (None = sem limite).
        max_value:   limite superior inclusivo (None = sem limite).
        where:       expressao SQL para restringir o conjunto testado
                     (ex.: "year >= 2020"). Util para nao reprovar por
                     valores legitimos em sub-conjuntos minoritarios.

    Comportamento:
        - NULL e ignorado (compatibilidade com not_null que cuida disso).
        - Sucesso: 0 linhas violando o range.
        - Falha: cada linha violando vira uma linha do resultado, dbt
          reporta count de violacoes.

    Exemplo de uso em schema.yml:

        columns:
          - name: gasto_pct_pib
            tests:
              - accepted_range:
                  arguments:
                    min_value: 0
                    max_value: 30
                    where: "year >= 2010"
#}

{% test accepted_range(model, column_name, min_value=none, max_value=none, where=none) %}

select {{ column_name }}
from {{ model }}
where {{ column_name }} is not null
{% if where %}
  and ({{ where }})
{% endif %}
{% if min_value is not none %}
  and {{ column_name }} < {{ min_value }}
{% endif %}
{% if max_value is not none %}
  and {{ column_name }} > {{ max_value }}
{% endif %}

{# Quando min e max sao ambos None, o teste degenera para "sem violacoes". #}

{% endtest %}
