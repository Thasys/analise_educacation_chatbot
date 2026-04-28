{#
    Macros de harmonizacao de codigos de pais.
    O sistema padroniza tudo para ISO-3166 alpha-3 (BRA, FIN, USA, ...),
    eliminando as inconsistencias entre fontes (Eurostat usa ISO-2,
    CEPALSTAT usa M49, IPEA usa nome PT, etc.).
#}


{% macro harmonize_country_iso3(raw_code) %}
{#
    Resolve um codigo ISO-3 contra a seed iso_3166_paises.
    Uso quando a fonte JA usa ISO-3 (World Bank, UNESCO UIS, OCDE,
    CEPALSTAT iso3, IEA): apenas valida que o codigo existe na seed.
    Retorna NULL para agregados regionais (AFE, EAS, WLD) e codigos
    desconhecidos -- esses caem nos testes not_null da intermediate.

    Exemplo:
        select {{ harmonize_country_iso3("country_iso3") }} as country_iso3
        from {{ ref('stg_worldbank__indicators') }}
#}
    coalesce(
      (select iso3 from {{ ref('iso_3166_paises') }} where iso3 = {{ raw_code }}),
      null
    )
{% endmacro %}


{% macro harmonize_country_iso2(raw_code) %}
{#
    Converte ISO-2 em ISO-3 via seed.
    Uso para Eurostat (geo column) e outras fontes que usam alpha-2.
#}
    coalesce(
      (select iso3 from {{ ref('iso_3166_paises') }} where iso2 = {{ raw_code }}),
      null
    )
{% endmacro %}


{% macro harmonize_country_m49(raw_code) %}
{#
    Converte codigo numerico M49 (ONU) em ISO-3.
    Uso para CEPALSTAT (country_id), UN data e outras fontes M49.
    Aceita string ou int -- normaliza via try_cast.
#}
    coalesce(
      (select iso3 from {{ ref('iso_3166_paises') }} where un_m49 = try_cast({{ raw_code }} as integer)),
      null
    )
{% endmacro %}


{% macro harmonize_country_name_pt(raw_name) %}
{#
    Converte nome PT-BR em ISO-3 via seed.
    Uso para IPEADATA (NIVNOME = 'Brasil') e outras fontes que usam
    o nome do pais em portugues. Match case-insensitive sobre name_pt
    da seed.
#}
    coalesce(
      (select iso3 from {{ ref('iso_3166_paises') }} where lower(name_pt) = lower({{ raw_name }})),
      null
    )
{% endmacro %}
