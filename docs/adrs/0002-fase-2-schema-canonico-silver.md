# ADR 0002 — Schema canônico Silver e padrão de UNION cross-source

- **Status:** aceito
- **Data:** 2026-04-29
- **Fase:** 2 (Silver Layer + dbt)

## Contexto

A Fase 2 transforma a Bronze multi-fonte (9 fontes na Fase 1, 7 com dados
reais após manutenção da Fase 1.5) em uma camada Silver harmonizada que
permite responder perguntas comparativas entre Brasil e o resto do mundo.

A maior fonte de bugs metodológicos em pesquisa comparada vive na
harmonização: cada fonte usa codificação diferente para o mesmo conceito
(país, ano, nível educacional, indicador), e nenhuma resposta sobre
"educação no Brasil em comparação com a OCDE" resolve em apenas uma fonte.

## Decisões

### 1. Schema canônico Silver para `int_indicadores__*`

Toda tabela `int_indicadores__*` da Silver expõe o mesmo conjunto de colunas:

| Coluna | Tipo | Significado |
|---|---|---|
| `country_iso3` | `VARCHAR(3)` | ISO-3166 alpha-3. Único modo de identificar país. |
| `year` | `INTEGER` | Ano de referência. |
| `value` | `DOUBLE` | Valor numérico. |
| `unit` | `VARCHAR` | Unidade canônica (ex.: `%_GDP`, `%`, `count`). |
| `indicator_id` | `VARCHAR` | ID canônico do projeto (ex.: `GASTO_EDU_PIB`, `LITERACY_15M`). |
| `indicator_name` | `VARCHAR` | Rótulo legível em PT-BR. |
| `source` | `VARCHAR` | Fonte original (`worldbank`, `unesco`, `oecd`, `eurostat`, `ipea`, `cepalstat`, ...). |
| `source_indicator_id` | `VARCHAR` | ID nativo da fonte (`SE.XPD.TOTL.GD.ZS`, `XGDP.FSGOV`, ...). |

Tabelas Silver podem adicionar colunas opcionais (`std_error`, `obs_status`,
`isced_level`, `territory_code`, `sex`, ...) sempre como **opcional**:
quando a fonte não tem o campo, fica `NULL`.

### 2. UNION ALL como padrão multi-fonte (não JOIN, não AVG)

Quando múltiplas fontes publicam o **mesmo indicador** (ex.: gasto em
educação % PIB aparece em World Bank + UNESCO + OCDE), o intermediate:

- **NÃO** faz JOIN entre as fontes.
- **NÃO** calcula média/mediana entre fontes.
- **FAZ** `UNION ALL` — cada fonte vira uma linha separada com `source`
  distinto, preservando integralmente a metodologia original.

Razão: cada fonte usa sistema de contas nacionais distinto (UOE da OCDE
vs GFS-IMF do Banco Mundial vs Atlas DH do IPEA, etc.). Diferenças de
0.5–1.5pp para o mesmo país/ano são **legítimas**, não bugs. Agregar
mascararia decisões metodológicas que o pesquisador precisa ver.

Regra de ouro: **se você não distingue a fonte na tabela final, não pode
distinguir as conclusões na análise.**

### 3. Dedup defensivo via `SELECT DISTINCT` antes do UNION

Uma fonte pode duplicar a chave natural por dois motivos:
- Bronze tem parquets com períodos sobrepostos (ex.: `2010-2023/` legado +
  `2000-2023/` atual após re-execução do coletor).
- A fonte tem dimensões adicionais que não são filtradas (ex.: OCDE GDP
  com `EXP_DESTINATION` distinguindo `INST_EDU` vs `INST_EDU_PUB`).

Cada CTE de fonte termina com `SELECT DISTINCT` na chave natural
`(country, year, source_indicator_id)`. Não é hack — é proteção contra
mudanças silenciosas na Bronze.

### 4. Filtragem rigorosa contra a seed `iso_3166_paises`

`int_indicadores__*` faz `INNER JOIN` com `int_geografia__paises_harmonizados`.
Isso garante que agregados regionais (`AFE`, `EAS`, `WLD` do World Bank;
agregados `EU27_2020` da Eurostat; etc.) sejam excluídos automaticamente.

A seed também serve como **lista canônica** para `accepted_values` testes
em todos os intermediates futuros, eliminando a necessidade de checagens
manuais por fonte.

### 5. Conversão pré-UNION quando definições conceituais diferem

Quando uma fonte publica o **conceito complementar** (ex.: IPEA publica
"taxa de analfabetismo" = `100 - literacy_rate`), a CTE da fonte
**converte antes do UNION**, com nota explícita:

```sql
ipea_raw as (
    select
        ...
        100.0 - value                        as value,  -- inverted
        cast(series_code || ' (inverted)' as varchar) as source_indicator_id
    from {{ ref('stg_ipea__series') }}
    where series_code in ('PNADCA_TXA15MUF', 'ADH_T_ANALF15M')
)
```

O sufixo `(inverted)` no `source_indicator_id` registra a transformação
para auditoria.

### 6. Granularidade `country_iso3` como nível canônico Silver

Tabelas `int_indicadores__*` operam **somente em nível país**. Dados
subnacionais (UFs/municípios brasileiros do IPEA/SIDRA, regiões NUTS-2
do Eurostat, estados americanos da OCDE) são dimensão ortogonal e
ganham seu próprio intermediate (`int_indicadores__*__subnacional`)
em sprint posterior. Razão: misturar grãos no mesmo modelo torna o
schema canônico incoerente e quebra `JOIN` com seed de países.

### 7. Materialização: `view` para staging, `table` para intermediate

- **Staging**: `view`. Volumes pequenos por staging (cada Parquet < 50MB),
  view evita duplicação de espaço em DuckDB.
- **Intermediate**: `table`. Joins e cross-source UNIONs, vale persistir
  resultado para que consultas downstream e dbt tests sejam rápidos.
- **Marts** (Fase 3): será revisado, provavelmente `external` Parquet
  para que o FastAPI possa ler diretamente.

### 8. Path da Bronze via `var('bronze_root')`

Stagings usam `read_parquet('{{ var("bronze_root") }}/<source>/...')`.
A var é parametrizável via env `DBT_BRONZE_ROOT`, default `../data/bronze`.
Em CI/Docker basta exportar a env. Modelos não conhecem caminhos absolutos.

## Alternativas consideradas

### Snowflake schema (uma fact + várias dim) por indicador

Descartado para a Silver. A Silver é a camada de "dados harmonizados
ainda fiéis à fonte"; estruturar como fact/dim é trabalho de Gold.

### Star schema único `fact_observations` desde a Silver

Descartado por dois motivos:
1. **Schema explosivo de dimensões opcionais** — `std_error` só existe
   para PISA/TIMSS, `isced_level` só para datasets que classificam por
   nível, `sex` só para fontes desagregadas. Forçar tudo em uma star
   schema na Silver dispersa NULLs e destrói legibilidade.
2. **Cada `int_indicadores__*` é uma "fact virtual"** — vários intermediates
   com schema canônico idêntico permitem `UNION ALL` para construir um
   star schema unificado em Gold quando útil. A Silver mantém a
   granularidade conceitual (um intermediate = um indicador).

### Fazer `int_indicadores__gasto_educacao` agregar com `AVG()` entre fontes

Descartado. Discutido na Decisão #2 — agregar mascara metodologia.

### Não filtrar agregados regionais (deixar passar `WLD`, `EAS`)

Descartado. Misturaria países e agregados na mesma coluna `country_iso3`,
quebrando todas as análises comparadas. INNER JOIN com seed é trivial e
caro de não fazer.

## Consequências

### Positivas

- **Comparabilidade transparente**: ao olhar `WHERE country_iso3='BRA'`
  vê-se imediatamente "tem 3 fontes, divergem em ~1pp; fonte tal usa
  base GFS-IMF, fonte tal usa UOE". Isto é, **a tabela documenta a
  controvérsia metodológica**.
- **Reuso massivo**: novos intermediates (`int_indicadores__avaliacoes_estudantes`,
  `int_indicadores__matriculas_isced`, etc.) são copy-paste do template
  do `gasto_educacao` com o filtro de fonte adaptado.
- **Testes declarativos uniformes**: cada `int_indicadores__*` recebe
  os mesmos 6-7 testes (`not_null`, `accepted_values` em `unit` e
  `indicator_id` e `source`, `relationships` para `country_iso3`).

### Negativas / aceitas

- **Tabelas mais altas que largas**: BRA com 5 fontes para gasto em
  educação resulta em 5 linhas/ano em vez de 1. É exatamente a
  intenção, mas significa que `SELECT * WHERE country='BRA'` retorna
  mais linhas do que um pesquisador iniciante esperaria. Documentado
  no schema.yml de cada modelo.
- **Granularidade subnacional separada**: tabelas BR-subnacional
  (com IPEA UFs/municípios) ficam em modelo separado. Pesquisas que
  combinam BR-subnacional com BR-país precisam de join explícito —
  custo aceitável pela limpeza do schema.

### Riscos

- **Drift do schema canônico** se algum intermediate futuro adicionar
  coluna ad-hoc no nome errado. Mitigação: dbt tests `accepted_values`
  + revisão de schema.yml em PRs.
- **Confusão entre `indicator_id` (canônico do projeto) e
  `source_indicator_id` (ID nativo da fonte)**. Mitigação: nomes
  distintos e descrições explícitas no schema.yml.

## Validações já realizadas

- **Match perfeito ao centésimo** entre UNESCO `XGDP.FSGOV`, World Bank
  `SE.XPD.TOTL.GD.ZS` e CEPAL `2236` (literacy) — UIS é fonte primária
  e WB/CEPAL ressindicam. Esperado e desejável.
- **Diferenças metodológicas reveladas**: OCDE EAG mostra ~1pp menor
  para BRA gasto educação que WB/UIS, consistente com base UOE vs
  GFS-IMF. Sem schema canônico cross-source isso ficaria invisível.
- **IPEA PNADCA difere ~1pp do conjunto WB/UIS/CEPAL** em alfabetização
  para BRA, refletindo metodologia autodeclaratória da PNAD Contínua.
  Diferença legítima.

## Referências

- [`docs/phases/fase-2-analise.md`](../phases/fase-2-analise.md) — análise
  prévia que motivou estas decisões.
- [`docs/phases/fase-2-conclusao.md`](../phases/fase-2-conclusao.md) —
  fechamento da Fase 2 (a próxima entrega).
- [`dbt_project/models/intermediate/indicadores/int_indicadores__gasto_educacao.sql`](../../dbt_project/models/intermediate/indicadores/int_indicadores__gasto_educacao.sql) —
  primeira aplicação completa do padrão (3 fontes UNION ALL).
- [`dbt_project/models/intermediate/indicadores/int_indicadores__alfabetizacao.sql`](../../dbt_project/models/intermediate/indicadores/int_indicadores__alfabetizacao.sql) —
  segunda aplicação (4 fontes UNION ALL com conversão IPEA pré-UNION).
