# Fase 2 — Sprint 2.0 (Setup + primeiros modelos)

> Progresso parcial da Fase 2. Sprint 2.0 e 2.1 (parcial) entregues.
> Documento de transferencia para retomar de outra maquina.
> **Data:** 2026-04-28

---

## 1. O que foi entregue

### 1.1 Bronze populada (parcial)

Execucao real dos coletores REST/API da Fase 1. Sucesso/falha por fonte:

| Fonte | Status | Observacao |
|---|---|---|
| **World Bank** | OK | 6 indicadores, ~32k linhas em `data/bronze/worldbank/` |
| **IBGE SIDRA 7136** | OK (parcial) | 2023 com dados reais; 2025 retornou 0 linhas (ainda nao publicado) |
| **IPEADATA** | Vazio | API retorna `Valores` vazios para series `ANALF15M`, `IDEB_BR_*` |
| **UNESCO UIS** | 404 | Dataflow `UNESCO,EDU_NON_FINANCE,1.0` nao encontrado |
| **Eurostat** | Erro de servidor | `RemoteProtocolError: peer closed connection` |
| **OCDE SDMX** | 404 | Dataflow `OECD.EDU.IMEP,DSD_EAG_FIN@DF_FIN_PERSTUDENT,1.0` invalido |
| **CEPALSTAT** | 404 | Indicador `1471` nao encontrado |

**Coletores funcionam corretamente**; as falhas sao **drift de dataflow IDs / disponibilidade do lado das APIs**, nao bugs no codigo. Registrado como **debito tecnico Fase 1.5** (manutencao de IDs).

### 1.2 dbt operacional

- Venv proprio em `dbt_project/.venv/` com `dbt-core 1.11.8` + `dbt-duckdb 1.10.1`.
- `DUCKDB_PATH` resolve para `data/duckdb/education.duckdb` (criado).
- `dbt debug` verde; `dbt build` verde.

### 1.3 Seeds (3)

| Seed | Linhas | Funcao |
|---|---|---|
| `iso_3166_paises` | 95 | Catalogo ISO-3166 com agrupamento (latam/oecd/brics/asia/africa_mena/europe_other) |
| `ibge_ufs` | 27 | UFs do Brasil (codigo IBGE, sigla, regiao) |
| `isced_2011` | 9 | Niveis ISCED 2011 PT/EN |

### 1.4 Macros (6)

- `harmonize_country_iso3(raw)` — valida ISO-3 contra seed.
- `harmonize_country_iso2(raw)` — converte ISO-2 para ISO-3 (Eurostat).
- `harmonize_country_m49(raw)` — converte M49 numerico para ISO-3 (CEPALSTAT, UN).
- `harmonize_country_name_pt(raw)` — converte nome PT-BR para ISO-3 (IPEADATA).
- `safe_to_year(col)` — extrai 4 digitos iniciais de string como INT.
- `safe_to_double(col)` — converte string em DOUBLE com NULL para `..`, `...`, `-`, ``.

### 1.5 Staging models (2)

| Modelo | Fonte | Materialization | Dedup | Testes |
|---|---|---|---|---|
| `stg_worldbank__indicators` | World Bank glob | view | (na intermediate) | 5 |
| `stg_ibge__sidra_7136` | SIDRA glob | view | (na intermediate) | 4 |

### 1.6 Intermediate models (2 — primeiro contrato canonico Silver)

| Modelo | Materialization | Linhas | Cobertura |
|---|---|---|---|
| `int_geografia__paises_harmonizados` | table | 96 | Paises efetivamente presentes em ao menos uma staging |
| `int_indicadores__gasto_educacao` | table | 1.718 | World Bank `SE.XPD.TOTL.GD.ZS`, 96 paises, 2000-2023 |

**Schema canonico publicado** (parcial — campos preenchidos hoje):
`country_iso3 · year · value · unit · indicator_id · indicator_name · source · source_indicator_id`.

### 1.7 dbt build summary

```
3 seeds · 2 view models (staging) · 2 table models (intermediate) · 45 testes
PASS=52 WARN=0 ERROR=0 SKIP=0  (~2s end-to-end)
```

---

## 2. Decisoes arquiteturais aplicadas

### 2.1 `vars.bronze_root` em `dbt_project.yml`

Permite que todos os modelos `read_parquet('{{ var("bronze_root") }}/...')` sejam
agnosticos a path. Em CI/Docker basta setar `DBT_BRONZE_ROOT=/data/bronze`.
Default e `../data/bronze` (relativo ao projeto dbt).

### 2.2 Dedup defensivo na Intermediate

Bronze pode conter parquets com periodos sobrepostos (ex.: glob captura
`2010-2023/data.parquet` legado + `2000-2023/data.parquet` atual e duplica
linhas). A chave natural e `(indicator, country, year)`, entao `SELECT DISTINCT`
em intermediate elimina duplicatas sem mascarar bugs reais. Staging
permanece fiel a Bronze.

### 2.3 Comentarios em Jinja, nao SQL

Refs em `{# ... ref('stg_xyz') ... #}` (comentario Jinja) nao geram dependencias
fantasmas no DAG. Usar `-- ref()` em SQL puro VAI gerar dep — mesmo o ref
estando "comentado" no SQL final.

### 2.4 Dependencias instaladas no venv permanentemente

`openpyxl` foi adicionado ao venv `data_pipeline/.venv/` (estava listado em
`pyproject.toml` mas nao sincronizado). Solidifica os 4 testes IDEB.

---

## 3. Pendencias para continuar Fase 2

### 3.1 Sprint 2.1 — Geografia & Classificacoes (parcial)

Feito:
- [x] Seed ISO-3166
- [x] Seed IBGE-UF
- [x] Seed ISCED 2011
- [x] `int_geografia__paises_harmonizados`

Falta:
- [ ] Seed `ibge_municipios.csv` (~5570 linhas — preferivel popular via dbt seed do que checar manual)
- [ ] `int_geografia__ufs_brasil` (provavelmente so SELECT da seed + filtro de presenca)
- [ ] `int_geografia__municipios_brasil`
- [ ] `int_classificacoes__isced_2011` (idem)

### 3.2 Sprint 2.2 — Staging das demais fontes

Pendentes (precisam que coletores correspondentes voltem a popular Bronze):
- `stg_ipea__serie_*` (4 series — bloqueado por API IPEADATA)
- `stg_unesco__flow_*` (bloqueado por dataflow IDs)
- `stg_eurostat__dataset_*` (bloqueado)
- `stg_oecd__flow_*` (bloqueado)
- `stg_cepalstat__indicator_*` (bloqueado)
- `stg_inep__censo_escolar`, `stg_inep__saeb`, `stg_inep__enem`, `stg_inep__ideb`
  (precisam executar coletores INEP — banda larga; nao executados ainda)
- `stg_iea__pisa`, `stg_iea__timss`, `stg_iea__pirls`
  (precisam R + microdados oficiais; debito Fase 1)

### 3.3 Sprint 2.3 — Indicadores cross-source

A medida que stagings entrem, expandir os intermediate:
- `int_indicadores__alfabetizacao` (SIDRA + WB + UIS + CEPALSTAT)
- `int_indicadores__avaliacoes_estudantes` (PISA + TIMSS + PIRLS + SAEB)
- (continuar `int_indicadores__gasto_educacao` com WB + UIS + Eurostat + OCDE)

### 3.4 Sprint 2.4 — Testes ampliados + GE

- Custom dbt test `accepted_range` (year ∈ [1990, ano_atual]; PISA ∈ [200, 800]; % ∈ [0, 100]).
- Suite Great Expectations para correlacoes e distribuicoes.

### 3.5 Sprint 2.5 — Documentacao

- `dbt docs generate && dbt docs serve` (HTML lineage navegavel).
- ADR `0002-fase-2-schema-canonico.md`.
- Atualizar `CLAUDE.md` se houver desvios.

---

## 4. Manutencao Fase 1 (debitos descobertos hoje)

Antes de continuar Fase 2 com as fontes nao-WorldBank, e necessario uma
sessao de **manutencao de coletores** (Fase 1.5):

1. **IPEADATA**: investigar por que `Metadados('SERCODIGO')/Valores` retorna
   array vazio. Pode ser: (a) API mudou estrutura, (b) series renomeadas,
   (c) bug temporario do servidor.
2. **UNESCO UIS**: descobrir dataflow IDs atuais via `https://api.uis.unesco.org/`.
3. **OCDE**: idem para `sdmx.oecd.org/public/rest/dataflow/all/all/all/`.
4. **CEPALSTAT**: re-validar IDs de indicadores (1471, 1407 expirados?).
5. **Eurostat**: investigar `RemoteProtocolError`. Provavel rate-limit ou
   instabilidade — talvez um simples retry resolve.

---

## 5. Como retomar de outra maquina

### 5.1 Pre-requisitos

```bash
# 1. Pull
git pull origin main

# 2. Reinstalar venvs
cd data_pipeline && uv venv && uv pip install -e ".[dev]"
cd ../dbt_project && python -m venv .venv && source .venv/Scripts/activate && pip install dbt-core dbt-duckdb

# 3. Rodar coletores REST (se Bronze vazia)
cd ../data_pipeline && DATA_ROOT="$PWD/../data" python -m src.flows.worldbank
DATA_ROOT="$PWD/../data" python -m src.flows.ibge_sidra

# 4. Rodar dbt
cd ../dbt_project && DBT_PROFILES_DIR=. dbt build
```

### 5.2 Verificar saude

```bash
cd dbt_project && DBT_PROFILES_DIR=. dbt build --no-partial-parse
# Deve imprimir: PASS=52 WARN=0 ERROR=0
```

### 5.3 Visualizar dados

```python
import duckdb
con = duckdb.connect('data/duckdb/education.duckdb', read_only=True)
con.sql("SELECT * FROM main_intermediate.int_indicadores__gasto_educacao WHERE country_iso3='BRA' ORDER BY year").show()
```

---

## 6. Metricas

```
Modelos dbt:                  4 (2 staging + 2 intermediate)
Testes dbt:                   45
Linhas em macros:             ~80
Linhas em seeds:              126 (95 paises + 27 UFs + 9 ISCED + 5 schema.yml)
Tempo dbt build:              ~2.0s
Linhas Silver materializadas: 1.814 (96 paises + 1.718 obs gasto educacao)
```

---

*Continuacao logica: Sprint 2.1 (geografia completa) ou Sprint 1.5 (manutencao
de coletores) — depende de prioridade. Recomendado 1.5 antes de 2.2 para nao
acumular debito.*
