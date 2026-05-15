# Fase 2 — Análise de Desenvolvimento

> **Análise Educacional Comparada Brasil × Internacional**
> Documento analítico sobre o desenvolvimento da **Fase 2 — Silver Layer + dbt**.
> Complementa o roadmap geral em [`CLAUDE.md`](../../CLAUDE.md#fase-2--silver-layer-e-dbt-semanas-57)
> e parte das conclusões da [`Fase 1`](./fase-1-conclusao.md).
> **Data:** 2026-04-27

---

## Sumário

1. [Contexto e ponto de partida](#1-contexto-e-ponto-de-partida)
2. [Objetivos da Fase 2](#2-objetivos-da-fase-2)
3. [Decisões arquiteturais propostas](#3-decisões-arquiteturais-propostas)
4. [Modelagem dbt — três camadas, três responsabilidades](#4-modelagem-dbt--três-camadas-três-responsabilidades)
5. [Harmonização de códigos (o coração da Silver)](#5-harmonização-de-códigos-o-coração-da-silver)
6. [Mapeamento Bronze → Silver por fonte](#6-mapeamento-bronze--silver-por-fonte)
7. [Estratégia de testes](#7-estratégia-de-testes)
8. [Sequência de implementação proposta](#8-sequência-de-implementação-proposta)
9. [Riscos e mitigações](#9-riscos-e-mitigações)
10. [Critérios de aceitação](#10-critérios-de-aceitação)
11. [Débitos da Fase 1 que afetam a Fase 2](#11-débitos-da-fase-1-que-afetam-a-fase-2)
12. [Apêndice: convenções rápidas](#12-apêndice-convenções-rápidas)

---

## 1. Contexto e ponto de partida

A Fase 1 entregou **9 fontes de dados** em camada Bronze — preservando a
fidelidade dos formatos originais (PNAD em colunas portuguesas, SDMX em
matriz dimensional, JSON-stat em cubo, microdados INEP em CSV latin-1, …).
Esse hiperpluralismo é uma virtude: garante reprodutibilidade e auditoria.
Mas é também o **maior obstáculo** para qualquer pergunta analítica do
projeto: nenhuma resposta sobre "o Brasil em comparação com a OCDE"
resolve em apenas uma fonte.

A Fase 2 transforma essa diversidade em uma camada Silver onde:

- **Tipos** estão consistentes (anos como `INT`, valores como `DOUBLE`,
  identificadores como `VARCHAR` em padrões internacionais).
- **Códigos** estão harmonizados (BRA = `BRA`, não `BR`, `BRA`, `Brasil`,
  `76` ao mesmo tempo).
- **Granularidades** estão explícitas (Brasil-país, Estado-UF, Município-IBGE,
  Indivíduo-anonimizado).
- **Linhagem** é rastreável até o `_metadata.json` da Bronze.

Sem essa camada, a Gold (Fase 3) e os agentes (Fase 5) não conseguem
construir comparações estatisticamente válidas — toda lógica de "casar
BRA com `BR` da Eurostat" acabaria proliferando dentro de cada agente
ou cada gráfico, fragmentando regras de negócio e tornando bugs metodo-
lógicos invisíveis.

### Ponto de partida quantitativo

```
9 fontes em Bronze · 160 testes Python verdes · 0 modelos dbt · 0 testes dbt
DuckDB instalado mas não consultado · profiles.yml apontando para
data/duckdb/education.duckdb (vazio até a primeira execução real)
```

---

## 2. Objetivos da Fase 2

### 2.1 Objetivos primários

1. **`dbt build` com 100% verde** sobre dataset Bronze realista (não vazio).
2. **Schema canônico Silver** publicado e estável — colunas como
   `country_iso3`, `territory_code`, `isced_level`, `year`, `value`
   aparecem com o mesmo nome em **todos** os modelos `int_*`.
3. **Documentação navegável** via `dbt docs serve` mostrando lineage
   das ~16 staging models até as ~5 intermediate models.
4. **Cobertura de testes**: 100% das tabelas com pelo menos um
   `not_null` ou `unique` em chaves; ranges plausíveis em métricas
   (PISA score ∈ [200, 800], % ∈ [0, 100], ano ∈ [1990, ano-corrente]).

### 2.2 Objetivos secundários

5. **Seeds de referência** versionadas no Git (ISO-3166, IBGE-UF,
   ISCED 2011, mapas de país por fonte).
6. **Macros utilitárias** para reuso transversal (`harmonize_country()`,
   `safe_to_year()`, `null_if_empty()`).
7. **Suíte mínima Great Expectations** para validações que dbt não
   expressa naturalmente (distribuições, correlações esperadas).

### 2.3 Não-objetivos (escopo da Fase 3)

- Datasets analíticos finais (`mart_*`).
- Indicadores derivados pré-calculados (gap em pontos padronizados, etc.).
- OpenMetadata como UI de catálogo.
- Otimizações de performance (ordenação, particionamento DuckDB).

A clareza sobre o que **não** entra é tão importante quanto o que entra:
a Fase 2 é construção do "tijolo padrão", não da "torre".

---

## 3. Decisões arquiteturais propostas

### 3.1 dbt-duckdb como motor único

**Por quê**: o data lake é um conjunto de Parquets em `data/bronze/`.
DuckDB lê Parquet diretamente via `read_parquet()` sem ETL adicional,
o adapter `dbt-duckdb` é maduro e suporta `external_location` para
materializações que escrevem de volta como Parquet. Sem subir Postgres,
sem mover dados.

**Implicação**: nenhuma dependência runtime de container — Fase 2 roda
inteira local com `uv` + `dbt-core` + `dbt-duckdb`. Isso casa com a
decisão da Fase 1 (Docker Desktop offline).

### 3.2 Materializações por camada

| Camada | Materialização | Justificativa |
|---|---|---|
| `staging/` | `view` | Volumes pequenos por staging (cada Parquet < 10 GB); view evita duplicação de espaço |
| `intermediate/` | `table` | Joins e harmonizações; vale persistir resultado |
| `marts/` (Fase 3) | `table` ou `external` | Será revisado em Fase 3 |

Tabela materializada em DuckDB é arquivo binário interno do `.duckdb`.
Onde o consumo cruza o processo (FastAPI lendo, agentes consultando),
considerar `external_location` para escrever como Parquet em
`data/silver/<dominio>/`.

### 3.3 Convenção de nomenclatura

Padrão estrito (CLAUDE.md já anuncia, Fase 2 formaliza):

```
stg_<source>__<dataset>            # 1:1 com Bronze
int_<dominio>__<descricao>         # cross-source (joins, harmonização)
mart_<dominio>__<analise>          # Fase 3
```

Exemplos:
- `stg_inep__censo_escolar`
- `stg_unesco__flow_unesco_edu_non_finance_1_0`
- `int_geografia__paises_harmonizados`
- `int_indicadores__alfabetizacao_15m`

Dois `_` separando o agrupador da descrição é convenção dbt
"data team" (Fishtown Analytics).

### 3.4 Schema canônico Silver

Toda tabela `int_indicadores__*` deve poder ser empilhada com
`UNION ALL` em uma "fact table virtual" futura. Para isso, padronizo:

| Coluna | Tipo | Descrição |
|---|---|---|
| `country_iso3` | VARCHAR(3) | ISO-3166 alpha3 (`BRA`, `FIN`, `USA`) |
| `territory_code` | VARCHAR | Vazio para país; código IBGE-UF (2) ou IBGE-mun (7) |
| `territory_level` | VARCHAR | `country` \| `state` \| `municipality` \| `region` |
| `indicator_id` | VARCHAR | ID estável da métrica (`PISA_MATH_MEAN`, `WB_SE_XPD_TOTL_GD_ZS`) |
| `indicator_name` | VARCHAR | Rótulo legível |
| `isced_level` | VARCHAR | ISCED 2011 ou `NA` |
| `year` | INT | Ano de referência |
| `period` | VARCHAR | Período fino se aplicável (`2022-Q1`) |
| `value` | DOUBLE | Valor numérico |
| `unit` | VARCHAR | `%`, `score`, `BRL`, `USD_PPP`, `count` |
| `std_error` | DOUBLE \| NULL | Erro-padrão quando exigido (PISA, TIMSS, PIRLS) |
| `obs_status` | VARCHAR \| NULL | Flag SDMX (`A`, `E`, `M`) |
| `source` | VARCHAR | `inep`, `oecd`, `unesco`, … |
| `source_url` | VARCHAR | URL canônica original |

Nem toda fonte preenche todos os campos — `std_error` só faz sentido
para PISA/TIMSS/PIRLS, `isced_level` só para datasets que classificam
por nível, e assim por diante. O contrato é "se a fonte tem, a Silver
expõe naquele nome; se não tem, fica `NULL`".

---

## 4. Modelagem dbt — três camadas, três responsabilidades

### 4.1 Staging (`models/staging/`) — fidelidade tipada

Função: ler Parquet da Bronze e impor tipos, sem alterar semântica.

```sql
-- models/staging/inep/stg_inep__ideb.sql
{{ config(materialized='view') }}

select
    cast(uf as varchar)             as uf_code,
    cast(ideb_2021 as double)       as ideb_2021,
    cast(ideb_2023 as double)       as ideb_2023
from read_parquet('{{ var("bronze_root") }}/inep/ideb/2023/data.parquet')
```

Cada `stg_*` deve ter `schema.yml` com:
- `description:` (o que esse staging representa).
- `columns:` com `description` e `tests:` mínimos (`not_null` em PKs).
- `meta:` com `source_url` apontando para o sidecar `_metadata.json` da Bronze.

### 4.2 Intermediate (`models/intermediate/`) — harmonização e enriquecimento

Função: aplicar **regras de negócio horizontais** (harmonização de
códigos, joins com seeds, derivação de `indicator_id`). É aqui que se
materializa o schema canônico.

Domínios propostos para a Fase 2:

```
int_geografia__paises_harmonizados        -- BRA/FIN/USA + nomes oficiais
int_geografia__ufs_brasil                 -- código IBGE 2-dig + nome + região
int_geografia__municipios_brasil          -- código IBGE 7-dig + UF
int_classificacoes__isced_2011            -- níveis 0-8 + descrição PT/EN
int_indicadores__alfabetizacao            -- empilha SIDRA + IPEADATA + WB + UIS + CEPALSTAT
int_indicadores__gasto_educacao           -- empilha WB + UIS + Eurostat + OCDE
int_indicadores__avaliacoes_estudantes    -- PISA + TIMSS + PIRLS + SAEB + IDEB
```

Cada `int_indicadores__*` deve produzir **o schema canônico inteiro**.
Isso permite, na Fase 3, criar marts via `UNION ALL` ou via vistas
abstratas. É essa decisão que torna a comparação BR × OCDE viável em
SQL puro, sem reaprender as APIs em cada análise.

### 4.3 Marts (Fase 3) — analítico final

Não é objetivo da Fase 2. Mas vale ancorar: marts vão consumir
exclusivamente intermediate. **Staging nunca vira insumo de mart**
diretamente — a regra previne que decisões de harmonização acabem
"locais a um mart" e portanto escondidas.

---

## 5. Harmonização de códigos (o coração da Silver)

A maior fonte de bugs metodológicos em pesquisa comparada vive aqui.

### 5.1 Países

Cada fonte usa um código diferente para "Brasil":

| Fonte | Código bruto |
|---|---|
| World Bank | `BRA` (já ISO-3) |
| IPEADATA | `Brasil` (NIVNOME) ou TERCODIGO IBGE-2 quando UF |
| UNESCO UIS / OCDE | `BRA` (REF_AREA) |
| Eurostat | `BR` (geo, ISO-2) |
| CEPALSTAT | `76` (country_id ONU) ou `BRA` (country_iso3) |
| INEP | sem código de país (sempre Brasil implícito) |
| IEA (PISA/TIMSS/PIRLS) | `BRA` (CNT) |

**Solução**: seed `seeds/iso_3166_paises.csv` com colunas
`(iso2, iso3, name_pt, name_en, un_m49)`. Macro `harmonize_country()`
que recebe o código bruto + a fonte e devolve `iso3` canônico (com
fallback para `'UNK'` quando irreconhecível).

### 5.2 Estados / UFs do Brasil

INEP, IPEADATA e SIDRA usam **código IBGE de 2 dígitos** (11–53).
Outras fontes simplesmente não existem nesse nível. Seed
`seeds/ibge_ufs.csv` com `(uf_code, sigla, nome, regiao_codigo, regiao_nome)`.

### 5.3 Municípios

Códigos IBGE de 7 dígitos. Atenção: existe a versão legada de 6
dígitos que **não deve ser usada** — Censo 2010+ e IDEB pós-2017 usam 7.
Seed `seeds/ibge_municipios.csv` com `(mun_code7, uf_code, nome, populacao_2022)`.

### 5.4 Níveis ISCED 2011

| Código | Descrição PT | Descrição EN |
|---|---|---|
| 0 | Educação infantil | Early childhood education |
| 1 | Anos iniciais do EF | Primary education |
| 2 | Anos finais do EF | Lower secondary |
| 3 | Ensino médio | Upper secondary |
| 4 | Pós-secundário não-superior | Post-secondary non-tertiary |
| 5 | Educação terciária curta | Short-cycle tertiary |
| 6 | Bacharelado | Bachelor's |
| 7 | Mestrado | Master's |
| 8 | Doutorado | Doctoral |

Seed `seeds/isced_2011.csv`. Macro `harmonize_isced()` para fontes
que usam apelidos próprios (UIS usa `L1`, `L2`; UOE/Eurostat usa `ED1`,
`ED2`; INEP usa "Anos Iniciais EF" em texto livre).

### 5.5 Indicador

`indicator_id` é o eixo final da harmonização. Convenção proposta:

```
<DOMINIO>_<METRICA>           # ex.: ALFAB_15M, IDEB_AI, ESL_EU
<FONTE>_<CODIGO_NATIVO>       # ex.: WB_SE_XPD_TOTL_GD_ZS, UNESCO_GER1_M
```

Para os intermediate `int_indicadores__*`, sempre usar a primeira
forma (canônica). Para staging, manter o código nativo é OK (é fiel
à fonte).

---

## 6. Mapeamento Bronze → Silver por fonte

Resumo das regras-chave para cada coletor da Fase 1. Este é o
*input* concreto para escrever os 16 staging models e 7 intermediate
models.

### 6.1 IBGE SIDRA (`stg_ibge__sidra_<tabela>`)

- Colunas brutas em português ("Valor", "Brasil", "Ano").
- Renomear para snake_case ASCII no staging.
- `Valor` → `value::DOUBLE` (atenção: SIDRA serve textos com `..`,
  `-` ou `...` para missing — converter para NULL).
- `D3C` (código de ano) → `year::INT`.
- `D1C` ou similar → `territory_code` (IBGE 2 ou 7 dígitos
  dependendo do nível).

### 6.2 World Bank (`stg_worldbank__indicator_*`)

- Já vem com `country_iso3`, `date`, `value`. Quase pronto.
- `date` é string ("2023") → `year::INT`.
- `country_id` é ISO-2; ignorar (preferir `country_iso3`).
- Filtrar agregados regionais ("World", "EAS") deixando só países
  reais — usar JOIN com seed ISO-3166.

### 6.3 IPEADATA (`stg_ipea__serie_*`)

- `VALDATA` é timestamp UTC (já tipado pelo coletor) → `year`,
  `period`.
- `NIVNOME` em texto livre — mapear para `territory_level`:
  - `'Brasil'` → `country`
  - `'Estados'` → `state`
  - `'Municípios'` → `municipality`
- `TERCODIGO` é vazio quando `Brasil`, IBGE-2 quando UF, IBGE-7
  quando município.

### 6.4 UNESCO UIS / OCDE (`stg_unesco__*`, `stg_oecd__*`)

- Schema dinâmico: cada dataflow tem dimensões diferentes.
- Padrão **comum**: `REF_AREA`, `TIME_PERIOD`, `OBS_VALUE`, `OBS_STATUS`.
- Demais dimensões (sex, age, isced, measure, …) preservadas no
  staging com nome original; uso decidido nos `int_indicadores__*`.

### 6.5 Eurostat (`stg_eurostat__dataset_*`)

- `geo` (ISO-2) → harmonizar para `country_iso3` na intermediate.
- `time` é string mas formato varia (`2022`, `2022-Q1`, `2022M03`).
  Manter como string no staging; staging só faz `cast(value as double)`.
- Outras dimensões (`age`, `sex`, `isced11`) preservadas.

### 6.6 CEPALSTAT (`stg_cepalstat__indicator_*`)

- Já tem `country_iso3`, `year`, `value`. Mais simples.
- `country_id` (ONU M49) → ignorar (redundante com iso3).

### 6.7 INEP

- `stg_inep__censo_escolar` — coluna por coluna do CSV; PK
  candidata: `(NU_ANO_CENSO, CO_ENTIDADE)`.
- `stg_inep__saeb` — mesmo padrão; PK `(NU_ANO_PROVA, ID_ALUNO)`.
- `stg_inep__enem` — `(NU_ANO, NU_INSCRICAO)`.
- `stg_inep__ideb` — wide format por ciclo; **considerar pivot
  para long no intermediate** (`year`, `value`, `level`).

### 6.8 IEA (`stg_iea__pisa`, `stg_iea__timss`, `stg_iea__pirls`)

- Schema já canônico: `study, REF_AREA, TIME_PERIOD, [grade,] domain,
  OBS_VALUE, SE, N`. Staging é quase identidade.
- Preservar `SE` (erro-padrão) — é o item mais valioso para
  intervalos de confiança nos marts da Fase 3.

---

## 7. Estratégia de testes

### 7.1 Pirâmide de testes na Fase 2

```
       /\
      /GE\        Validações estatísticas/distribuição (poucas, alvo)
     /----\
    /dbt   \     Testes declarativos por modelo (muitos, baratos)
   /generic \
  /----------\
 /  Python    \  Já cobertos na Fase 1 (coletores, parsers)
/--------------\
```

### 7.2 Testes dbt obrigatórios

Para **toda staging table**:
- `not_null` em PKs candidatas.
- `unique` em PKs verdadeiras (quando exatamente identificáveis).

Para **toda intermediate table**:
- `not_null` em `country_iso3`, `year`, `value`.
- `accepted_values` em `country_iso3` referenciando seed ISO-3166.
- `accepted_values` em `territory_level` (`country`, `state`,
  `municipality`, `region`).
- `accepted_range` (custom test) em `year` (1990 ≤ y ≤ ano-corrente).
- `accepted_range` em `value` por indicator_id (PISA: 200–800; %: 0–100).

### 7.3 Great Expectations

Casos onde GE é mais natural que dbt:
- **Distribuição**: % de NULLs em colunas críticas < 5%.
- **Correlação**: PISA math vs PISA read deve correlacionar > 0.7
  por país.
- **Cobertura temporal**: para indicadores anuais, gap máximo entre
  anos consecutivos ≤ 3.

GE roda em pre-publish: bloqueia a próxima Fase se algo desviar do
esperado. Não bloqueia builds incrementais (seria dor sem ganho).

### 7.4 Critério de "verde"

```bash
dbt deps && dbt seed && dbt run && dbt test
```

Sai com 0 e mostra `PASS` em todos os testes. Lineage HTML gerado por
`dbt docs generate && dbt docs serve`.

---

## 8. Sequência de implementação proposta

Fluxo otimizado para destravar o trabalho cedo (testes funcionando
em paralelo com modelagem).

| Sprint | Duração | Entregáveis |
|---|---|---|
| **2.0 — Setup** | 1 dia | `dbt deps` ok, `profiles.yml` validado, seed inicial ISO-3166 carregada, `dbt debug` verde. Macro `harmonize_country` esqueleto. |
| **2.1 — Geografia & Classificações** | 2 dias | Seeds ISO-3166, IBGE-UF, IBGE-municípios, ISCED-2011 + intermediate models de geografia/classificações. Testes unique nas seeds. |
| **2.2 — Staging das 9 fontes** | 4 dias | 16 staging models (1 ou 2 por fonte) com `schema.yml` e `not_null` em PKs. Cobertura imediatamente verificada com `dbt test --select staging`. |
| **2.3 — Intermediate de indicadores cross-source** | 4 dias | 3 dos 4 `int_indicadores__*` (alfabetização, gasto, avaliações). Aplicação rigorosa do schema canônico. |
| **2.4 — Testes ampliados + GE** | 2 dias | Custom dbt tests (`accepted_range`), suíte GE para correlações e distribuições. |
| **2.5 — Documentação** | 1 dia | `dbt docs generate`, atualização do CLAUDE.md, ADR de decisões da Fase 2. |
| **Total** | **~14 dias úteis** | (≈ 2.5–3 semanas) |

Tempo proposto encaixa na janela "semanas 5–7" do CLAUDE.md.

### 8.1 Ordem de ataque dentro da staging

Fontes mais simples primeiro — feedback loop curto:

1. World Bank (já tem `country_iso3`)
2. CEPALSTAT (idem)
3. IEA (PISA/TIMSS/PIRLS — schema já canônico)
4. IPEADATA (mapeamento territorial limpo)
5. UNESCO + OCDE (SDMX — mais complexo, mas fortemente padronizado)
6. Eurostat (JSON-stat — colunas variam mais por dataset)
7. SIDRA (PT-BR + missing markers `..`/`...`)
8. INEP (CSV largos: dezenas a centenas de colunas)

---

## 9. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| **Bronze vazia** na primeira execução de `dbt build` | Alta | Alto | Cada staging model tem fixture mínima em `seeds/_fixtures_*.csv` para `dbt run` rodar sem ter executado coletores reais. Os testes diferenciam "sample" de "produção" via tag `@sample`. |
| **Drift de schema do INEP** entre ciclos | Média | Médio | Staging usa `select * from read_parquet(...)`-style com casts explícitos; mudanças de coluna geram NULLs detectáveis pelos `not_null` tests, em vez de quebrar o build. |
| **Códigos de país em UTF-8 com acentuação** (CEPALSTAT, SIDRA) | Média | Médio | Harmonização sempre passa por seed ISO-3166. Se um nome bruto não bate, fica `country_iso3 = NULL`, que reprova `not_null` — falha visível, não silenciosa. |
| **Ano em formato não-numérico** (Eurostat `2022-Q1`) | Baixa | Baixo | Macro `safe_to_year()` extrai os 4 primeiros dígitos; preserva `period` original separadamente. |
| **DuckDB OOM em INEP grande** | Média | Alto | Materializar `stg_inep__*` como `external` Parquet; usar `read_parquet(..., union_by_name=True)` com colunas explícitas. Limitar `memory_limit` no profile. |
| **Plausible values mal-tratados** | Baixa (R já fez certo) | Crítico (invalida pesquisa) | A Silver consome só agregados (`OBS_VALUE`, `SE`) — nunca volta aos PVs brutos. Documentar em `int_indicadores__avaliacoes_estudantes` que SE vem direto de R com BRR/Jackknife. |
| **Tempos de build crescendo** | Baixa | Baixo | Materializar intermediate como `table`; staging continua `view`. Testar `dbt run --select state:modified+` para builds incrementais. |
| **Conflito com a futura camada Gold** (re-trabalho) | Média | Baixo | Schema canônico Silver é justamente o contrato com a Gold. Se mudar, Gold tem que se adequar — e isso é normal. ADR documenta a versão "v1" do schema. |

---

## 10. Critérios de aceitação

A Fase 2 está concluída quando **todos** os itens abaixo são verdade:

- [ ] `dbt deps && dbt seed && dbt run && dbt test` retorna exit 0
      sobre dataset de produção (não fixtures).
- [ ] Pelo menos **16 staging models** publicados (1 por dataset
      Bronze + variantes INEP).
- [ ] **Pelo menos 7 intermediate models** publicados:
      `int_geografia__paises_harmonizados`,
      `int_geografia__ufs_brasil`,
      `int_geografia__municipios_brasil`,
      `int_classificacoes__isced_2011`,
      `int_indicadores__alfabetizacao`,
      `int_indicadores__gasto_educacao`,
      `int_indicadores__avaliacoes_estudantes`.
- [ ] **100% das tabelas** com `description` no `schema.yml`.
- [ ] **100% das tabelas** com pelo menos 1 teste em alguma coluna.
- [ ] `dbt docs generate` produz HTML com lineage navegável.
- [ ] **Suíte Great Expectations** com pelo menos 5 expectativas
      ativas, executando via `pytest -m ge`.
- [ ] `docs/phases/fase-2-conclusao.md` declarando o trabalho final
      (similar ao da Fase 1).
- [ ] Atualização do `CLAUDE.md` se algo divergir das premissas.

---

## 11. Débitos da Fase 1 que afetam a Fase 2

Ressalvas registradas em [`fase-1-conclusao.md`](./fase-1-conclusao.md#6-débitos-técnicos-registrados)
e como vão impactar o trabalho:

1. **URLs INEP a validar** — Antes de qualquer `dbt run` real sobre
   INEP, executar uma vez cada coletor com ano corrente para confirmar
   que os ZIPs existem onde esperado. Sem isso, staging só roda em
   fixtures.
2. **R não executado** — Idem para PISA/TIMSS/PIRLS. Os intermediate
   `int_indicadores__avaliacoes_estudantes` precisam de Parquet real
   gerado pelos scripts R; até lá, usar fixtures sintéticas.
3. **Docker Desktop offline** — Não bloqueia a Fase 2 (DuckDB é
   embedded), mas a auditoria via `IngestionLogger` continua em modo
   no-op. Aceitável.
4. **`pre-commit` ausente** — Antes de fazer múltiplos commits dbt,
   instalar para garantir `prettier` em YAMLs e `markdownlint` em
   `schema.yml`s.
5. **Sem cobertura mínima imposta** — Adicionar `--cov-fail-under=85`
   no `pyproject.toml` da `data_pipeline` quando rodar a próxima
   suite, para não regredir.

---

## 12. Apêndice: convenções rápidas

### 12.1 Estrutura final esperada de `dbt_project/models/`

```
models/
├── staging/
│   ├── ibge/         stg_ibge__sidra_7136.sql + .yml
│   ├── worldbank/    stg_worldbank__indicator_se_xpd_totl_gd_zs.sql + .yml
│   ├── ipea/         stg_ipea__serie_analf15m.sql + ...
│   ├── unesco/       stg_unesco__flow_unesco_edu_non_finance_1_0.sql + ...
│   ├── eurostat/     stg_eurostat__dataset_educ_uoe_enrt01.sql + ...
│   ├── oecd/         stg_oecd__flow_oecd_edu_imep_dsd_eag_fin.sql + ...
│   ├── cepalstat/    stg_cepalstat__indicator_1471.sql + ...
│   ├── inep/         stg_inep__censo_escolar.sql, ..._saeb, ..._enem, ..._ideb
│   └── iea/          stg_iea__pisa.sql, stg_iea__timss.sql, stg_iea__pirls.sql
│
├── intermediate/
│   ├── geografia/
│   │   ├── int_geografia__paises_harmonizados.sql + .yml
│   │   ├── int_geografia__ufs_brasil.sql
│   │   └── int_geografia__municipios_brasil.sql
│   ├── classificacoes/
│   │   └── int_classificacoes__isced_2011.sql
│   └── indicadores/
│       ├── int_indicadores__alfabetizacao.sql
│       ├── int_indicadores__gasto_educacao.sql
│       └── int_indicadores__avaliacoes_estudantes.sql
│
└── marts/   (Fase 3)
```

### 12.2 Convenção de `schema.yml`

```yaml
version: 2

models:
  - name: stg_inep__ideb
    description: >
      IDEB por UF. Origem: planilha XLSX oficial do INEP.
    meta:
      source_url: "https://download.inep.gov.br/.../ideb_2023.xlsx"
      ingested_via: "data_pipeline.collectors.inep.IdebCollector"
    columns:
      - name: uf_code
        description: Código IBGE de 2 dígitos (11–53).
        tests:
          - not_null
          - relationships:
              to: ref('int_geografia__ufs_brasil')
              field: uf_code
      - name: ideb_2023
        description: Score IDEB 2023.
        tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 10
```

### 12.3 Macros básicas a criar

```sql
-- macros/harmonize_country.sql
{% macro harmonize_country(raw_code, source) %}
  coalesce(
    (select iso3 from {{ ref('iso_3166_paises') }} where iso2 = {{ raw_code }}),
    (select iso3 from {{ ref('iso_3166_paises') }} where iso3 = {{ raw_code }}),
    null
  )
{% endmacro %}

-- macros/safe_to_year.sql
{% macro safe_to_year(col) %}
  try_cast(regexp_extract(cast({{ col }} as varchar), '^([0-9]{4})', 1) as int)
{% endmacro %}
```

### 12.4 Comandos do dia-a-dia

```bash
# Setup inicial
cd dbt_project && uv run dbt deps && uv run dbt debug

# Build incremental durante desenvolvimento
uv run dbt run --select state:modified+ --defer --state target/

# Verificar 1 modelo isolado
uv run dbt run --select stg_inep__ideb && uv run dbt test --select stg_inep__ideb

# Documentação local
uv run dbt docs generate && uv run dbt docs serve --port 8081
```

---

## Conclusão

A Fase 2 é menos sobre "código novo" e mais sobre **disciplina contratual**:
publicar um schema canônico Silver (seção 3.4) e harmonizar tudo o que
veio da Fase 1 contra ele. O risco maior não é técnico (dbt + DuckDB são
tecnologias maduras) — é **drift de regras de negócio metodológicas**.
Por isso a maior parte deste documento descreve *convenções e testes*,
não *arquivos a escrever*.

Com a estrutura, sequência e critérios deste documento, o desenvolvimento
da Fase 2 deveria caber confortavelmente em **2.5–3 semanas de trabalho
solo**, terminando em um dataset analítico Silver pronto para alimentar
a Gold (Fase 3) e os agentes (Fase 5) sem retrabalho.

---

*Próximo documento ao fim do desenvolvimento: `fase-2-conclusao.md` —
seguindo o mesmo template usado em [`fase-1-conclusao.md`](./fase-1-conclusao.md).*
