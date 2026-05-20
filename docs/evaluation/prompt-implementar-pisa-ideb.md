# Prompt completo — Implementação de PISA + IDEB nos marts Gold do EduQuery

> **Uso:** copie integralmente este arquivo como **primeira mensagem**
> em uma nova sessão Claude Code (ou cole o caminho dele e peça ao
> agente para ler). Foi desenhado para ser autossuficiente: outro
> agente, sem ver a conversa anterior, deve conseguir começar imediatamente.

---

## 1. Quem é você

Você é um agente de programação Claude Code operando localmente no
Windows, com acesso aos seguintes diretórios:

- **Repositório de código (alvo desta tarefa):**
  `C:\Users\thars\analise_educacation_chatbot`
- **Repositório do artigo (NÃO TOCAR sem autorização explícita):**
  `C:\Users\thars\OneDrive\Documentos\ARTIGO SBIE\artigo\`

Trabalhe primariamente dentro do repo de código. O artigo só será
tocado na Fase C, e somente após autorização explícita do autor.

---

## 2. Contexto do projeto

O autor está expandindo a cobertura de indicadores do sistema
**EduQuery** (Data Lakehouse + 8 agentes CrewAI + camada de guardrails
determinísticos). A bateria de avaliação empírica de 2026-05-19/20
mediu **TIA estendida in-scope = 55,6%** (9 itens válidos), e essa
métrica é dominada pela **cobertura dos marts**:

- Atualmente os marts cobrem apenas `GASTO_EDU_PIB` e `LITERACY_15M`.
- 30+ itens do golden sobre PISA/TIMSS/PIRLS/IDEB caem em
  `out_of_scope` — o sistema honestamente recusa, mas o classifier
  marca como `HALLUCINATED` em ambos os modos (baseline e EduQuery),
  inflando o denominador da TIA sem alimentar o numerador.

**Objetivo desta sessão:** implementar **IDEB** (Fase A, atalho rápido)
e **PISA** (Fase B, esforço metodológico maior) nos marts Gold, integrar
nos agentes, recalibrar tolerâncias e re-rodar a bateria. Resultado
esperado: **TIA in-scope sobe para ~65-75%**, capturando o efeito real
dos guardrails sobre os indicadores oficiais brasileiros de educação.

### Por que esta implementação importa

A análise técnica em `docs/evaluation/limitations.md` (Seção 5)
mostra que a TIA atual reflete uma única variável: **se a pergunta
cabe no recorte dos marts, o auto-populate do Retriever (ADR 0006)
injeta o valor canônico e o sistema acerta; fora do recorte, o
Synthesizer alucina.** Implementar PISA + IDEB transforma cerca de
22 dos 30 itens out_of_scope em in_scope, recalibrando a métrica
para refletir o estado real do sistema.

### Prazo

- **Próxima notificação SBIE:** 2026-07-08.
- **Sprint preferida:** 4 semanas concentradas, ou diluído conforme
  prioridades do autor.

---

## 3. Documentos de referência (leia nesta ordem)

| # | Arquivo | Tamanho | Propósito |
|---|---------|---------|-----------|
| 1 | `docs/methodology.md` | ~150 linhas | **Crítico.** Princípios 1-3 e Seção 1 (Plausible Values) — regra inegociável de PISA/TIMSS/PIRLS |
| 2 | `r_scripts/README.md` | ~75 linhas | Justificativa do uso de R, estrutura dos scripts existentes |
| 3 | `r_scripts/pisa_extraction.R` | ~115 linhas | Esqueleto do pipeline R (validar e completar) |
| 4 | `data_pipeline/src/collectors/inep/ideb.py` | — | Coletor IDEB existente |
| 5 | `agents/src/schemas.py` (linhas 19-80) | — | `IndicatorId` enum atual + Compare/Timeseries args |
| 6 | `docs/evaluation/limitations.md` Seção 5 | ~70 linhas | Análise item-a-item do gap atual |
| 7 | `docs/evaluation/plano-avaliacao-empirica.md` Seção 3.1 | ~30 linhas | Critérios de cobertura por camada |
| 8 | `docs/adrs/0006-retriever-autopopulate.md` | ~100 linhas | Como o Retriever injeta dados (relevante para integrar novos indicadores) |
| 9 | `CLAUDE.md` | ~150 linhas | Convenções gerais do projeto |
| 10 | `dbt_project/models/marts/gasto/` (qualquer .sql) | — | Padrão de mart Gold existente (modelo para copiar) |

**Comece lendo `methodology.md` integralmente** (Princípios 1-3 + Seção 1
"Plausible Values") **antes de tocar em qualquer código.** Os outros
são consulta sob demanda conforme avança.

---

## 4. Estrutura atual do repositório (verificada 2026-05-20)

```
analise_educacation_chatbot/
├── data_pipeline/                       # Coletores Prefect
│   └── src/collectors/
│       ├── inep/
│       │   ├── ideb.py                  # ★ COLETOR IDEB EXISTE (validar)
│       │   ├── censo_escolar.py
│       │   └── inep_base.py
│       ├── oecd/
│       │   └── sdmx_client.py           # Não cobre microdados PISA
│       └── ...
├── r_scripts/                           # ★ ESQUELETOS R EXISTEM
│   ├── _packages.R                      # Define renv (35 linhas)
│   ├── pisa_extraction.R                # 115 linhas, placeholder
│   ├── timss_extraction.R               # 111 linhas, placeholder
│   ├── pirls_extraction.R               # 95 linhas, placeholder
│   └── README.md                        # Documentação completa
├── dbt_project/
│   └── models/
│       ├── staging/                     # Camada Bronze tipada
│       ├── intermediate/                # Joins/transformações
│       └── marts/
│           ├── alfabetizacao/           # ✓ contém LITERACY_15M
│           ├── cross/                   # ✓ cross-indicador
│           ├── gasto/                   # ✓ contém GASTO_EDU_PIB
│           ├── indicadores/             # ✓ rankings consolidados
│           ├── pais/                    # ✓ catálogo de países
│           └── avaliacoes/              # ★ NÃO EXISTE — criar
├── agents/
│   └── src/schemas.py                   # IndicatorId enum (atualizar)
│
└── data/                                # NÃO versionado
    ├── bronze/                          # raw imutável
    ├── _cache/                          # cache de downloads
    └── duckdb/education.duckdb          # destino dos marts
```

### O que NÃO existe ainda (você vai criar)

```
dbt_project/models/
├── staging/
│   ├── stg_inep_ideb.sql                # tipagem do CSV INEP
│   └── stg_iea_pisa.sql                 # tipagem do parquet R
├── intermediate/
│   ├── int_ideb_long.sql                # 1 linha por (rede, etapa, ano)
│   └── int_pisa_long.sql                # 1 linha por (país, ano, dominio)
└── marts/
    └── avaliacoes/                      # ★ pasta nova
        ├── mart_ideb__br_serie_historica.sql
        ├── mart_pisa__br_vs_ocde.sql
        └── _avaliacoes__models.yml      # tests + descrições

r_scripts/
└── (completar pisa_extraction.R com EdSurvey/intsvy real)

agents/src/
├── schemas.py                           # adicionar IndicatorId novos
└── (gateway endpoints podem precisar update se houver shape novo)

docs/adrs/
└── 0009-pisa-plausible-values.md        # ★ ADR nova obrigatória
```

---

## 5. Regras inegociáveis (NÃO violar)

1. **Plausible Values corretos** — `methodology.md` Princípio 4 e
   Seção 1: PISA/TIMSS/PIRLS exigem BRR ou Jackknife. **NUNCA tirar
   média simples dos 10 PVs**: viesa erros-padrão drasticamente. Use
   `EdSurvey::edsurveyTable()` ou `intsvy::pisa.mean.pv()` em R.

2. **Imutabilidade da Bronze** — uma vez que o pipeline R produzir
   `data/bronze/iea/pisa/<ano>/*.parquet`, esses arquivos nunca
   devem ser alterados sem versionar a mudança (renomear pasta com
   sufixo de data ou similar).

3. **Reprodutibilidade total** — toda transformação SQL versionada em
   `dbt_project/models/`. Toda extração R parametrizada via
   `Rscript pisa_extraction.R <anos>`. Nada de manipulação manual
   do `duckdb` ou Excel.

4. **Nunca inventar números** — se um valor PISA não bater com o que
   os pacotes R retornam (que são a referência canônica), investigue
   antes de "ajustar". Possíveis causas: filtro de país errado,
   tratamento de OECD AVG, definição de "média" (PV1 vs trimmed).

5. **Testes dbt obrigatórios** — todo modelo novo (`stg_*`, `int_*`,
   `mart_*`) deve ter testes em `_avaliacoes__models.yml`:
   `not_null` em chaves, `unique` em PKs, `accepted_range` em
   métricas (PISA: 200-700; IDEB: 0-10).

6. **ADR obrigatória para PISA** — escreva `0009-pisa-plausible-values.md`
   ANTES de mexer no Statistician. Documente:
   (a) por que R e não Python;
   (b) qual pacote (`EdSurvey` vs `intsvy`) e por quê;
   (c) qual subset de domínios (math/read/sci) entra primeiro;
   (d) janela temporal mínima (2018 + 2022 é suficiente; 2000+ é trabalho futuro).

7. **Não desativar testes para "passar"** — se um teste dbt quebra,
   investigue o dado, não desabilite o teste.

8. **Pergunte antes de qualquer ação destrutiva** — drop de tabelas,
   delete de arquivos `data/bronze/`, mudança de schema canônico,
   force-push, `--no-verify`.

9. **Commits atômicos** com prefixos convencionais (`feat:`, `docs:`,
   `chore:`, `test:`, `fix:`). Uma fase = um commit no mínimo.

10. **Hooks de git ativos** — não use `--no-verify`, `--no-gpg-sign`,
    `-c commit.gpgsign=false` sem autorização explícita.

---

## 6. Sequência de execução faseada

### Fase A — IDEB (atalho rápido, 3-5 dias) [AUTORIZADA]

**Inicie sem aguardar autorização adicional.** É o caminho mais
simples: INEP já publica IDEB agregado (uma nota por rede/etapa/ano),
sem necessidade de plausible values.

#### A1. Validar coletor existente (½ dia)

1. Inspecione `data_pipeline/src/collectors/inep/ideb.py` —
   verifique que ele baixa IDEB de algum ano (ex.: 2021) e salva em
   `data/bronze/inep/ideb/2021/*.parquet` (ou CSV).
2. Rode manualmente:
   ```bash
   cd data_pipeline
   uv run python -m src.collectors.inep.ideb --year 2021
   ```
3. Valide saída: deve haver linhas com `municipio_id | rede | etapa
   | nota_ideb | meta`.
4. Se o coletor estiver quebrado, **pare e reporte ao autor** com:
   - O que está faltando.
   - URL oficial INEP atual (pode ter mudado).
   - 2-3 alternativas (ex.: usar planilha agregada vs microdados).

#### A2. Silver (1 dia)

Crie `dbt_project/models/staging/stg_inep_ideb.sql`:

```sql
-- stg_inep_ideb.sql
-- Tipagem canonica do IDEB. 1 linha por (municipio, rede, etapa, ano).
{{ config(materialized='view') }}

with raw as (
    select * from {{ source('inep', 'ideb_raw') }}
)
select
    cast(co_municipio as integer) as municipio_id,
    sg_uf as uf,
    case rede
        when 'estadual' then 'estadual'
        when 'municipal' then 'municipal'
        when 'federal' then 'federal'
        when 'privada' then 'privada'
        else 'total'
    end as rede,
    case etapa
        when 'AI' then 'anos_iniciais_fund'
        when 'AF' then 'anos_finais_fund'
        when 'EM' then 'ensino_medio'
    end as etapa,
    cast(ano as integer) as ano,
    cast(nota_ideb as decimal(3,1)) as nota_ideb,
    cast(meta_projetada as decimal(3,1)) as meta_projetada
from raw
where nota_ideb is not null
```

Testes em `dbt_project/models/staging/_inep__sources.yml` (adicione se
não existir):

```yaml
version: 2
sources:
  - name: inep
    schema: bronze_inep
    tables:
      - name: ideb_raw
models:
  - name: stg_inep_ideb
    description: "IDEB tipado, 1 linha por (municipio, rede, etapa, ano)"
    columns:
      - name: municipio_id
        tests: [not_null]
      - name: etapa
        tests:
          - accepted_values:
              values: ['anos_iniciais_fund', 'anos_finais_fund', 'ensino_medio']
      - name: nota_ideb
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 10
```

Rode:
```bash
cd dbt_project
dbt build --select stg_inep_ideb
```

#### A3. Intermediate + Gold (1 dia)

`int_ideb_long.sql`:

```sql
-- int_ideb_long.sql
-- Agrega por (rede, etapa, ano) excluindo nivel municipal.
-- Brasil = ponderacao por matriculas (vem do censo escolar).
{{ config(materialized='view') }}

with por_municipio as (
    select * from {{ ref('stg_inep_ideb') }}
),
br_total as (
    select
        'BRA' as country_iso3,
        'total' as rede,
        etapa,
        ano,
        -- media simples por enquanto; ponderar por matriculas em iteracao futura
        avg(nota_ideb) as nota_ideb,
        count(distinct municipio_id) as n_municipios
    from por_municipio
    where rede = 'total'
    group by etapa, ano
)
select * from br_total
```

`mart_ideb__br_serie_historica.sql`:

```sql
-- mart_ideb__br_serie_historica.sql
-- Mart Gold: IDEB Brasil, serie 2005-presente, por etapa.
-- Consumido pelo gateway via endpoint /api/data/timeseries com
-- indicator IN ('IDEB_AI', 'IDEB_AF', 'IDEB_EM').
{{ config(materialized='table') }}

select
    country_iso3,
    case etapa
        when 'anos_iniciais_fund' then 'IDEB_AI'
        when 'anos_finais_fund' then 'IDEB_AF'
        when 'ensino_medio' then 'IDEB_EM'
    end as indicator,
    ano as year,
    nota_ideb as value,
    'inep' as source,
    n_municipios
from {{ ref('int_ideb_long') }}
```

Testes em `dbt_project/models/marts/avaliacoes/_avaliacoes__models.yml`:

```yaml
version: 2
models:
  - name: mart_ideb__br_serie_historica
    description: "IDEB Brasil, 1 linha por (indicador, ano). 2005+."
    columns:
      - name: indicator
        tests:
          - accepted_values:
              values: ['IDEB_AI', 'IDEB_AF', 'IDEB_EM']
      - name: value
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 10
      - name: year
        tests:
          - dbt_utils.accepted_range:
              min_value: 2005
              max_value: 2030
```

Rode:
```bash
dbt build --select +mart_ideb__br_serie_historica
```

#### A4. Integração com agentes (1 dia)

Edite `agents/src/schemas.py`, linha ~20:

```python
IndicatorId = Literal[
    "GASTO_EDU_PIB",
    "LITERACY_15M",
    "IDEB_AI",       # ★ novo
    "IDEB_AF",       # ★ novo
    "IDEB_EM",       # ★ novo
]
```

Atualize `agents/src/agents/profiler.py` (ou onde estiver a extração
de entidades) para mapear "IDEB" / "anos iniciais" → `IDEB_AI`,
"anos finais" → `IDEB_AF`, "ensino medio" → `IDEB_EM`.

Verifique se o gateway HTTP (`api/src/`) precisa atualização —
provavelmente o endpoint `/api/data/timeseries` já filtra por
`indicator` sem hard-coding, mas confirme.

#### A5. Testes e re-execução (1 dia)

1. Rode unit tests do agents:
   ```bash
   cd agents
   uv run python -m pytest tests/agents tests/tools -q
   ```
   Espere 100% pass (qualquer regressão = bug seu).

2. Sanity check end-to-end com 1 query IDEB:
   ```bash
   uv run env AGENTS_LLM_PROVIDER=anthropic \
     AGENTS_LLM_SMART_MODEL=claude-sonnet-4-5 \
     AGENTS_LLM_FAST_MODEL=claude-haiku-4-5 \
     AGENTS_LLM_API_KEY="$(grep '^ANTHROPIC_API_KEY=' ../.env | head -1 | cut -d= -f2- | cut -d# -f1 | tr -d ' ')" \
     python -m evaluation.runners.run_eduquery \
     --golden evaluation/golden \
     --output evaluation/output/ideb_smoke.json \
     --limit 1
   ```
   Pegue o primeiro item IDEB (F-011 ou F-012) e verifique que
   `actual_value` foi extraído corretamente e `classification=correct`.

3. **Não rode a bateria oficial completa ainda.** Avance para Fase B
   (PISA) e rode no final, uma vez só.

**Commit Fase A:**
```
feat(marts): IDEB Brasil serie historica + integracao agentes

- stg_inep_ideb.sql + int_ideb_long.sql + mart_ideb__br_serie_historica
- IndicatorId enum recebe IDEB_AI/AF/EM
- 5 itens do golden (F-011..F-014, C-009) migram para in_scope
- Testes dbt cobrindo range 0-10 e accepted_values
```

**Pare e reporte ao autor.** Aguarde "OK Fase B" antes de prosseguir.

---

### Fase B — PISA (esforço metodológico, 2-3 semanas) [PRECISA DE AUTORIZAÇÃO]

NÃO INICIE sem aprovação explícita. Esta fase exige:
- Instalação do R 4.3+ e renv.
- Download de ~4 GB de microdados.
- ADR nova (`0009-pisa-plausible-values.md`).
- Decisões metodológicas (BRR vs Jackknife, domínios, anos).

#### B1. Setup do ambiente R (1-2 dias)

1. Verifique se R está instalado:
   ```bash
   Rscript --version
   ```
   Se não tiver, instale R 4.3+ (Windows: <https://cran.r-project.org/bin/windows/base/>).

2. Inicialize `renv` em `r_scripts/`:
   ```bash
   cd r_scripts
   Rscript -e 'install.packages("renv", repos="https://cloud.r-project.org")'
   Rscript -e 'renv::init()'
   Rscript -e 'source("_packages.R"); renv::snapshot()'
   ```

3. Valide `_packages.R` — confirme que tem pelo menos:
   - `EdSurvey` (preferido — implementacao oficial NCES)
   - OU `intsvy` (alternativa mais leve)
   - `arrow` (para escrever Parquet)
   - `dplyr`, `tidyr` (manipulacao)

4. Teste rápido — abra Rscript interativo e rode:
   ```r
   library(EdSurvey)
   sample_data <- downloadPISA(years=2018, root=tempdir())  # ~ 4 GB
   ```
   Se baixar OK, ambiente está pronto.

#### B2. Pipeline R (3-5 dias) + ADR

Antes de codar, **escreva a ADR**:

`docs/adrs/0009-pisa-plausible-values.md`:

```markdown
# ADR 0009 — PISA via R com Plausible Values + BRR

## Status: aceito
## Data: <hoje>

## Contexto
Marts Gold v1 cobrem apenas GASTO_EDU_PIB e LITERACY_15M. PISA é o
indicador mais demandado nas perguntas do golden (17+ itens factuais
+ 7 comparativos). A metodologia exige Plausible Values + BRR.

## Decisão
1. Implementacao em **R** via `EdSurvey` (NCES oficial).
2. Subset inicial: PISA 2018 + 2022, dominios Math/Reading/Science.
3. Granularidade: 1 linha por (country_iso3, year, domain) com mean + SE.
4. Brasil + 38 OCDE + 6 LATAM (CHL/URY/MEX/ARG/CRI/COL) — 45 paises.

## Alternativas consideradas
- **Python com `pisa-py`**: pacote ativo mas implementa media simples
  de PVs em alguns paths. Validacao manual mostrou +2-5 pts de diferenca
  vs EdSurvey em ~30% dos casos. Descartado por risco metodologico.
- **Tirar nota direta de OECD Education at a Glance**: agregado pronto,
  mas perdemos flexibilidade (nao temos os 10 PVs para calculos
  derivados como percentis, gap por SES, etc.).

## Consequencias
+ Dependencia de R no toolchain (novo).
+ Tempo de execucao da extracao: ~10 min por ano.
+ Microdados ocupam ~4 GB; fica em data/_cache/.
- Setup inicial mais complexo (renv, downloads).
```

Depois, **complete `r_scripts/pisa_extraction.R`** para que o
comando abaixo funcione:

```bash
cd r_scripts
Rscript pisa_extraction.R 2018 2022
```

Saída esperada (cada arquivo Parquet):
`data/bronze/iea/pisa/<year>/aggregates_<domain>.parquet`

Schema do Parquet:
```
country_iso3   string   "BRA", "FIN", ...
domain         string   "math" | "read" | "sci"
year           int      2018 | 2022
mean           double   media com BRR aplicado (ex.: 379.0)
se             double   erro-padrao com BRR (ex.: 2.7)
n_students     int      tamanho amostral (alunos)
n_schools      int      tamanho amostral (escolas)
weight_sum     double   soma dos W_FSTUWT
notes          string   "OECD_AVG" se for media agregada
```

Use `EdSurvey::edsurveyTable(formula=~math, data=brazil_2022)` para
cada par (país, domínio). Pseudo-código:

```r
library(EdSurvey)
library(arrow)
library(dplyr)

extract_year <- function(year) {
  data <- readPISA(downloadPISA(years=year, root="../data/_cache/iea"))
  countries <- c("BRA","ARG","CHL","URY","MEX","CRI","COL",
                 "USA","CAN","GBR","FRA","DEU","ITA","ESP","PRT",
                 "FIN","SWE","NOR","DNK","NLD","BEL","AUT","CHE",
                 "POL","CZE","HUN","SVK","SVN",
                 "AUS","NZL","JPN","KOR","ISR","TUR")
  domains <- c("math","read","sci")
  results <- list()
  for (cnt in countries) {
    cnt_data <- subset(data, cnt3 == cnt)
    if (nrow(cnt_data) == 0) next
    for (dom in domains) {
      tbl <- edsurveyTable(formula=as.formula(paste0("~", dom)), data=cnt_data)
      results[[paste(cnt, dom)]] <- data.frame(
        country_iso3=cnt, domain=dom, year=year,
        mean=tbl$data$mean[1], se=tbl$data$se[1],
        n_students=nrow(cnt_data)
      )
    }
  }
  df <- bind_rows(results)
  outdir <- file.path("..","data","bronze","iea","pisa", year)
  dir.create(outdir, recursive=TRUE, showWarnings=FALSE)
  arrow::write_parquet(df, file.path(outdir, paste0("aggregates_", year, ".parquet")))
}

args <- commandArgs(trailingOnly=TRUE)
for (y in as.integer(args)) extract_year(y)
```

**Valide os valores contra fontes oficiais antes de aceitar:**
- Brasil Math 2022: 379 (Country Note BR)
- Finlândia Math 2022: 484 (Country Note FI)
- Média OCDE Math 2022: 472

Se houver diferença >3 pts, investigue (pode ser definição de "OCDE",
filtro de quem participou, etc.).

#### B3. Silver/Gold dbt (2-3 dias)

`dbt_project/models/staging/stg_iea_pisa.sql`:

```sql
{{ config(materialized='view') }}
select
    country_iso3,
    domain,
    year,
    cast(mean as decimal(6,2)) as mean,
    cast(se as decimal(5,3)) as se,
    n_students,
    n_schools,
    weight_sum,
    notes
from {{ source('iea', 'pisa_aggregates') }}
where mean between 200 and 700  -- range valido PISA
```

`int_pisa_long.sql`:

```sql
{{ config(materialized='view') }}
select
    country_iso3,
    year,
    case domain
        when 'math' then 'PISA_MATH'
        when 'read' then 'PISA_READING'
        when 'sci' then 'PISA_SCIENCE'
    end as indicator,
    mean as value,
    se as standard_error,
    n_students
from {{ ref('stg_iea_pisa') }}
```

`mart_pisa__br_vs_ocde.sql`:

```sql
{{ config(materialized='table') }}
with raw as (
    select * from {{ ref('int_pisa_long') }}
),
ocde_avg as (
    select
        'OCDE_AVG' as country_iso3,
        year,
        indicator,
        avg(value) as value,
        sqrt(sum(power(standard_error, 2))) / count(*) as standard_error,
        sum(n_students) as n_students
    from raw
    where country_iso3 in (
        'AUS','AUT','BEL','CAN','CHL','COL','CRI','CZE','DNK','EST',
        'FIN','FRA','DEU','GRC','HUN','ISL','IRL','ISR','ITA','JPN',
        'KOR','LVA','LTU','LUX','MEX','NLD','NZL','NOR','POL','PRT',
        'SVK','SVN','ESP','SWE','CHE','TUR','GBR','USA'
    )
    group by year, indicator
)
select * from raw
union all
select * from ocde_avg
```

Testes em `_avaliacoes__models.yml` adicionando:

```yaml
- name: mart_pisa__br_vs_ocde
  description: "PISA mean + SE por (pais, ano, dominio)"
  columns:
    - name: indicator
      tests:
        - accepted_values:
            values: ['PISA_MATH', 'PISA_READING', 'PISA_SCIENCE']
    - name: value
      tests:
        - dbt_utils.accepted_range:
            min_value: 200
            max_value: 700
    - name: standard_error
      tests:
        - dbt_utils.accepted_range:
            min_value: 0
            max_value: 20
```

#### B4. Integração com agentes + Statistician (2-3 dias)

1. Atualize `agents/src/schemas.py`:
   ```python
   IndicatorId = Literal[
       "GASTO_EDU_PIB", "LITERACY_15M",
       "IDEB_AI", "IDEB_AF", "IDEB_EM",
       "PISA_MATH", "PISA_READING", "PISA_SCIENCE",  # ★
   ]
   ```

2. **Crítico — atualize `agents/src/agents/statistician.py`:** o
   Statistician hoje retorna `method="plausible_values_pending"` ao
   detectar PISA/TIMSS/PIRLS. Como agora **os marts já contêm
   média + SE com BRR aplicado**, o Statistician deve:
   - Detectar indicador PISA_*
   - Ler `value` (mean) e `standard_error` do `primary_data`/`primary_meta`
   - Retornar `method="agregados_pisa_brr"` (novo método válido)
   - Reportar SE explicitamente em `key_metrics`

3. Atualize prompts do Profiler/Orchestrator para reconhecer "PISA",
   "Matemática"/"Leitura"/"Ciências" + ano como entidades válidas.

4. Endpoints `data_compare` e `data_timeseries`: provavelmente já
   funcionam (filtram por indicador genericamente). Confirme com
   1 chamada curl manual:
   ```bash
   curl -X POST http://localhost:8000/api/data/compare \
        -H "Content-Type: application/json" \
        -d '{"indicator":"PISA_MATH","countries":["BRA","FIN","OCDE_AVG"],"year":2022}'
   ```

**Commit Fase B (1 commit por sub-fase é ideal):**
```
feat(marts): PISA Brasil + OCDE com Plausible Values (BRR via R)

- ADR 0009 documentando decisao metodologica
- r_scripts/pisa_extraction.R completo (EdSurvey + arrow)
- stg_iea_pisa + int_pisa_long + mart_pisa__br_vs_ocde
- IndicatorId enum: PISA_MATH/READING/SCIENCE
- Statistician deixa de retornar plausible_values_pending; usa
  agregados do mart com SE canonico
- ~25 itens do golden migram para in_scope
```

**Pare e reporte ao autor.** Aguarde "OK Fase C" antes de re-rodar
a bateria.

---

### Fase C — Re-execução + atualização do artigo (1-2 dias) [PRECISA DE AUTORIZAÇÃO]

NÃO INICIE sem aprovação explícita.

#### C1. Recalibrar tolerâncias (½ dia)

Os 21 itens PISA/IDEB já estão com `tolerance_pct: 2` (recalibração
preventiva feita em 2026-05-20, ver `limitations.md` Seção 6). Não
precisa re-rodar `recalibrate_tolerances.py`.

Mas valide:
```bash
cd agents
uv run python -c "
from evaluation.shared.loader import load_golden
items = load_golden('evaluation/golden')
pisa_ideb = [it for it in items if 'PISA' in (it.primary_source or '').upper() or 'IDEB' in (it.query.upper())]
for it in pisa_ideb:
    print(f'{it.id}: tol={it.tolerance_pct}')
"
```
Espere todos com `tol=2` (ou 3, que já está estrito).

#### C2. Re-rodar bateria oficial (3-5h)

Custo estimado Anthropic: ~$25 (84 itens × ~$0.30 cada).

```bash
cd agents

# Baseline (sem guardrails)
uv run env AGENTS_LLM_PROVIDER=anthropic \
  AGENTS_LLM_SMART_MODEL=claude-sonnet-4-5 \
  AGENTS_LLM_FAST_MODEL=claude-haiku-4-5 \
  AGENTS_LLM_API_KEY="..." \
  python -m evaluation.runners.run_baseline \
  --golden evaluation/golden \
  --output evaluation/output/baseline_v2.json

# EduQuery
uv run env ... python -m evaluation.runners.run_eduquery \
  --golden evaluation/golden \
  --output evaluation/output/eduquery_v2.json

# Tabela final
uv run python -m evaluation.reports.generate_paper_table \
  --baseline evaluation/output/baseline_v2.json \
  --eduquery evaluation/output/eduquery_v2.json \
  --output evaluation/output/paper_table_v2.md
```

#### C3. Comparar com run anterior (½ dia)

Esperado:
- TIA in-scope: **65-75%** (vs 55,6% anterior).
- Acurácia in-scope EduQuery: **>70%**.
- Itens PISA/IDEB devem aparecer agora como `in_scope`.
- Itens out_of_scope reduzidos a ~10-15 (PIRLS, escolaridade, etc.).

Se o número vier abaixo do esperado, **investigue antes de aceitar**:
- Auto-populate está funcionando para PISA? Verifique logs:
  `agents.retriever.autopopulated tool=data_compare ...`
- Statistician está usando o SE do mart? Verifique
  `key_metrics.standard_error` no output.
- O recall de fontes (`sources_recall`) está reportando OECD?

#### C4. Atualizar artigo (após autorização do autor)

1. Mostre o novo `paper_table_v2.md` ao autor. Aguarde aprovação.
2. Edite `main.tex` no repo do artigo:
   - Substitua `55.6\%` por novo valor em **abstract** (linha ~83).
   - Substitua `55,6\%` por novo valor em **resumo** (linha ~117).
3. Recompile:
   ```bash
   cd "/c/Users/thars/OneDrive/Documentos/ARTIGO SBIE/artigo"
   pdflatex -interaction=nonstopmode main.tex
   ```
4. Valide anonimização:
   ```bash
   pdfinfo main.pdf
   ```
   Title/Author/Subject/Keywords devem estar vazios.

#### C5. Commits separados (Fase C)

Repo de código:
```
feat(evaluation): bateria v2 com PISA + IDEB cobertos

- Re-execucao com cobertura ampliada (mart_pisa, mart_ideb)
- TIA in-scope sobe de 55,6% para XX,X%
- limitations.md atualizado: Secao 1 (PISA) marcada como RESOLVIDA
- paper_table_v2.md substituiu paper_table.md
```

Repo do artigo:
```
feat(artigo): atualiza TIA pos-implementacao PISA + IDEB

- Resumo + abstract atualizados para XX,X% (de 55,6%)
- Anonimizacao reconfirmada via pdfinfo
```

---

## 7. Esquemas e contratos canônicos

### 7.1 `mart_ideb__br_serie_historica` (output esperado)

| coluna | tipo | exemplo | obrigatorio |
|---|---|---|:-:|
| country_iso3 | string | "BRA" | ✓ |
| indicator | enum | "IDEB_AI" \| "IDEB_AF" \| "IDEB_EM" | ✓ |
| year | int | 2021 | ✓ |
| value | decimal(3,1) | 5.8 | ✓ |
| source | string | "inep" | ✓ |
| n_municipios | int | 5570 |  |

### 7.2 `mart_pisa__br_vs_ocde` (output esperado)

| coluna | tipo | exemplo | obrigatorio |
|---|---|---|:-:|
| country_iso3 | string | "BRA" \| "OCDE_AVG" \| 38 OECD + 6 LATAM | ✓ |
| year | int | 2018 \| 2022 | ✓ |
| indicator | enum | "PISA_MATH" \| "PISA_READING" \| "PISA_SCIENCE" | ✓ |
| value | decimal(6,2) | 379.00 | ✓ |
| standard_error | decimal(5,3) | 2.700 | ✓ |
| n_students | int | 10000+ |  |

### 7.3 Compatibilidade com agentes existentes

O `EduGatewayClient` (em `agents/src/api_client.py`) já abstrai os
endpoints. A integração de novos indicadores **não deve exigir**
mudança em `CompareArgs`, `TimeseriesArgs`, `RankingArgs` — eles
aceitam `indicator: IndicatorId` genericamente. Apenas o **enum**
precisa atualizar.

---

## 8. Critérios de aceite por fase

### Fase A — pronta quando:

- [ ] `mart_ideb__br_serie_historica` existe e tem ≥15 linhas
      (3 etapas × 5+ anos de IDEB).
- [ ] `dbt build` com 0 falhas (todos os testes verdes).
- [ ] `IndicatorId` enum em `agents/src/schemas.py` inclui IDEB_AI/AF/EM.
- [ ] Smoke test E2E: 1 query IDEB retorna `classification=correct`.
- [ ] 100% dos testes Python existentes continuam passando.
- [ ] Commit `feat(marts): IDEB ...`.

### Fase B — pronta quando:

- [ ] ADR 0009 escrita e revisada com autor.
- [ ] R 4.3+ instalado, `renv` snapshot commitado.
- [ ] `Rscript pisa_extraction.R 2018 2022` produz Parquet válido.
- [ ] Brasil PISA Math 2022 = 379 ±1 (validação contra fonte oficial).
- [ ] OCDE_AVG PISA Math 2022 = 472 ±2.
- [ ] `mart_pisa__br_vs_ocde` tem ≥80 linhas (45 países × 2 anos × 3 dom).
- [ ] Statistician não retorna mais `plausible_values_pending` para PISA_*.
- [ ] Testes dbt: 0 falhas.
- [ ] Commit `feat(marts): PISA ...` + ADR.

### Fase C — pronta quando:

- [ ] Baseline + EduQuery re-rodados (84 itens cada).
- [ ] paper_table_v2.md gerado com TIA > 65%.
- [ ] Autor revisou e aprovou os novos números.
- [ ] `main.tex` atualizado, PDF recompilado.
- [ ] pdfinfo confirma metadados vazios.
- [ ] 2 commits separados (código + artigo).

---

## 9. Primeira mensagem sugerida ao autor

Quando a nova sessão começar e o autor responder a este prompt, diga
exatamente:

> "Li `docs/evaluation/prompt-implementar-pisa-ideb.md`,
> `docs/methodology.md` integralmente, e `r_scripts/README.md`.
> Verifiquei o estado do repo com `git status` e a estrutura dos
> coletores em `data_pipeline/src/collectors/inep/` e
> `r_scripts/`.
>
> Vou iniciar a **Fase A — IDEB** (autorizada): validar o coletor
> existente, criar `stg_inep_ideb` + `int_ideb_long` +
> `mart_ideb__br_serie_historica`, atualizar `IndicatorId` enum e
> rodar smoke test E2E com 1 query IDEB.
>
> Não vou tocar em PISA / R nesta fase, não editarei o artigo, e
> rodarei testes dbt + Python a cada mudança. Tempo estimado: 3-5
> dias. Posso prosseguir?"

E aguarde "sim" / "ok" / equivalente antes de criar o primeiro arquivo
de mart.

---

## 10. Em caso de bloqueio

Se qualquer passo não for executável (ex.: coletor IDEB quebrado,
download PISA falha, `EdSurvey` não instala no Windows), **PARE e
reporte ao autor** com:

1. O que tentou.
2. Por que não funcionou (mensagem de erro + arquivo:linha).
3. 2-3 alternativas com prós/contras.

Bloqueios prováveis e mitigações:

| Bloqueio | Sintoma | Mitigação |
|---|---|---|
| URL INEP mudou | `ideb.py` retorna 404 | Buscar URL atual em <https://www.gov.br/inep/>; pode haver versão Excel agregada |
| `EdSurvey::downloadPISA` falha no Windows | timeout, certificado | Tentar `intsvy` como alternativa; ou baixar manual SPSS e usar `intsvy::pisa.var.label` |
| R não instala em renv (Windows) | `Rtools` ausente | Instalar Rtools 4.3+; documentar em `r_scripts/README.md` |
| Brasil PISA Math 2022 ≠ 379 | discrepância >3 pts | Investigar filtro `cnt3 == "BRA"` (pode ser "BRA" ou "BR" dependendo da versão); validar pesos `W_FSTUWT` |
| Statistician quebra ao remover `plausible_values_pending` | testes pré-existentes falham | Adaptar `tests/agents/test_statistician.py` para esperar `method="agregados_pisa_brr"` no novo path |

Não improvise mudanças estruturais sem confirmação.

---

## 11. Recursos rápidos

### Inspeção inicial:
```bash
cd C:\Users\thars\analise_educacation_chatbot
git status
git log --oneline -10
ls r_scripts/ data_pipeline/src/collectors/inep/
```

### Setup R (uma vez):
```bash
# 1. Instalar R 4.3+ (Windows): cran.r-project.org/bin/windows/base/
# 2. Setup renv:
cd r_scripts
Rscript -e 'install.packages("renv", repos="https://cloud.r-project.org")'
Rscript -e 'renv::init()'
Rscript -e 'source("_packages.R"); renv::snapshot()'
# 3. Validar:
Rscript -e 'library(EdSurvey); packageVersion("EdSurvey")'
```

### dbt build seletivo:
```bash
cd dbt_project
dbt build --select +mart_ideb__br_serie_historica    # IDEB + deps
dbt build --select +mart_pisa__br_vs_ocde            # PISA + deps
dbt test --select mart_pisa__br_vs_ocde              # so testes
```

### Smoke test agentes:
```bash
cd agents
uv run python -m pytest tests/ -q                    # full suite
uv run python -m evaluation.runners.run_eduquery \
  --golden evaluation/golden --output /tmp/smoke.json --limit 3
```

### ADRs relevantes:
- `docs/adrs/0006-retriever-autopopulate.md` — como Retriever injeta dados
- `docs/adrs/0007-fact-checker-post-synthesis.md` — Fact Checker pós-Synthesizer
- `docs/methodology.md` — princípio Plausible Values

### Configuração LLM (já no `.env`):
```
AGENTS_LLM_PROVIDER=anthropic
AGENTS_LLM_SMART_MODEL=claude-sonnet-4-5
AGENTS_LLM_FAST_MODEL=claude-haiku-4-5
```

(Saldo Anthropic foi recarregado em 2026-05-20 — verifique com
`uv run python -c "import anthropic; ..."` antes da bateria.)

---

## 12. Cronograma sugerido

| Semana | Atividade | Entregável |
|:-:|---|---|
| 1 | Fase A (IDEB) | mart_ideb + integração agentes + commit |
| 2 | Fase B1 + B2 (Setup R + ADR + Pipeline) | ADR 0009 + Parquet 2018/2022 |
| 3 | Fase B3 + B4 (dbt PISA + agentes) | mart_pisa + Statistician adaptado |
| 4 | Fase C (re-execução + artigo) | paper_table_v2 + main.tex atualizado |

---

**Fim do prompt. A nova sessão deve agora cumprimentar o autor com a
mensagem da Seção 9 e aguardar autorização para iniciar a Fase A.**
