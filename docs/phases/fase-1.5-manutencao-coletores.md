# Fase 1.5 — Manutenção dos coletores

> Sprint de manutenção entre Fase 1 (ingestão Bronze) e Fase 2 (Silver+dbt).
> Necessario porque varias APIs publicas mudaram dataflow IDs ou
> arquitetura entre o desenvolvimento da Fase 1 e a Fase 2.
> **Data:** 2026-04-28

---

## 1. Sumario executivo

A primeira execucao real dos 7 coletores REST/API durante o Sprint 2.0
revelou que so 2 fontes (World Bank e IBGE SIDRA) estavam funcionais.
As outras 5 retornavam 404, RemoteProtocolError ou dados vazios — todas
por causa de **drift externo**, nao bugs no codigo.

A Fase 1.5 corrigiu 5 das 6 fontes problematicas e populou a Bronze com
dados reais para o trabalho da Fase 2. CEPALSTAT ficou pendente porque
a nova API REST agora retorna dados em formato dimensional encodado
(IDs internos) que exige refactor maior do parser.

### Fontes apos a Fase 1.5

| Fonte | Status pre-1.5 | Status pos-1.5 | Linhas em Bronze |
|---|---|---|---|
| **World Bank** | OK | OK | ~32k |
| **IBGE SIDRA** | OK | OK | ~3k |
| **IPEADATA** | Series vazias | OK (codigos atualizados) | ~22k |
| **UNESCO UIS** | 404 SDMX endpoint | OK (novo coletor REST) | ~25k |
| **Eurostat** | RemoteProtocolError | OK (transitorio) | ~246k |
| **OCDE SDMX** | 404 dataflow IDs | OK (IDs atualizados + parser estendido) | ~2.9M |
| **CEPALSTAT** | 404 host antigo | Bloqueado (refactor parser) | 0 |

---

## 2. Investigacoes e correcoes

### 2.1 UNESCO UIS — migracao SDMX → REST (2026)

**Sintoma**: `404 Not Found` para `https://api.uis.unesco.org/sdmx/data/...`

**Causa**: A UIS migrou em fevereiro/2026 da arquitetura SDMX para uma
API REST "flat" no host `api.uis.unesco.org/api/public`. O endpoint
SDMX antigo foi descontinuado.

**Correcao** (mudanca substantial):

- Novo coletor: `data_pipeline/src/collectors/unesco/uis_rest_client.py`
- Endpoint: `GET /api/public/data/indicators?indicator=<ID>&geoUnit=<ISO3>&start=YYYY&end=YYYY`
- Schema de resposta: simples `{"records":[{"indicatorId","geoUnit","year","value","magnitude","qualifier"}]}`
- Coletor SDMX antigo (`uis_client.py`) preservado como referencia historica.
- Flow `data_pipeline/src/flows/unesco.py` reescrito para usar REST.
- Testes: 11 novos em `tests/collectors/unesco/test_uis_rest_client.py`.

**Validacao cruzada com World Bank**: BRA gasto educacao % PIB:

| Ano | UNESCO XGDP.FSGOV | World Bank SE.XPD.TOTL.GD.ZS |
|---|---|---|
| 2018 | 6.089 | 6.089 |
| 2019 | 5.963 | 5.963 |
| 2020 | 5.771 | 5.771 |
| 2021 | 5.497 | 5.497 |
| 2022 | 5.619 | 5.619 |

Match perfeito ao centesimo — UIS publica os mesmos dados que WB usa.

### 2.2 OCDE SDMX — IDs deprecados + parser AllDimensions

**Sintoma**: `404 Not Found` para `OECD.EDU.IMEP,DSD_EAG_FIN@DF_FIN_PERSTUDENT,1.0`.
Apos atualizar IDs: HTTP 200 mas `rows=0`.

**Causa #1**: A familia `DSD_EAG_FIN` foi reorganizada em `DSD_EAG_UOE_FIN`
no ciclo Education at a Glance 2024-2025.

**Causa #2 (sutil)**: O coletor pede `dimensionAtObservation=AllDimensions`,
o que faz o servidor retornar `dataSets[0].observations` direto (todas
as dimensoes encodadas no obs_key). O parser em `utils/sdmx_json.py` so
sabia ler o layout `dataSets[0].series[<key>].observations` (default
historico). Apenas 4 linhas de ajuste fazem o parser tentar primeiro
o layout series-aware e cair no `observations` flat se vazio.

**Correcoes**:

- `data_pipeline/src/flows/oecd.py`: novos IDs
  `DSD_EAG_UOE_FIN@DF_UOE_INDIC_FIN_GDP,1.0` e `..._PERSTUD,3.1`.
- `data_pipeline/src/utils/sdmx_json.py`: extensao do parser para
  layout AllDimensions. Backwards-compatible (todos os 38 testes
  existentes ainda passam).
- Resultado: 2.9M linhas reais coletadas.

### 2.3 CEPALSTAT — host migrado, mas resposta agora dimensional

**Sintoma**: `404 Not Found` para `statistics.cepal.org/portal/cepalstat/api/v1`.

**Investigacao**:

- O host migrou para `api-cepalstat.cepal.org/cepalstat/api/v1`.
- O path tambem mudou: agora `/indicator/{id}/data?format=json`
  (id no path), nao `?ids_indicator={id}` (querystring).
- Mais grave: a resposta agora usa **IDs internos de dimensao**
  (ex.: `dim_29117=29170` representa um ano especifico) em vez de
  resolver os labels. O parser atual espera campos como `country_iso3`,
  `year` literais.

**Correcoes parciais aplicadas**:

- `data_pipeline/src/config.py`: novo `cepalstat_api_base`.
- `data_pipeline/src/flows/cepalstat.py`: novos IDs validos
  (2236 alfabetizacao, 53 analfabetismo, 460 gasto, 184 matricula).
  IDs antigos (1471/1407) nao existem mais.

**Pendente (debito 1.5b)**:

- Refactor do parser CEPALSTAT para resolver dim IDs via metadata
  (provavelmente buscar `/indicator/{id}/structure` ou similar e
  fazer um lookup table). Estimativa: ~1 dia.

### 2.4 IPEADATA — series renomeadas/inativas

**Sintoma**: `Metadados('ANALF15M')/Valores` retorna `{"value":[]}` HTTP 200.

**Investigacao**: download do catalogo completo (2839 series) revelou
que `ANALF15M`, `IDEB_BR_SAI/SAF/EM` nao existem mais. As series foram
renomeadas/aposentadas em ciclos recentes do IPEA.

**Correcoes**:

- `data_pipeline/src/flows/ipea.py`: codigos atualizados:
  - `PNADCA_TXA15MUF` (PNAD Continua, BR + UFs, 231 obs)
  - `ADH_T_ANALF15M` (Atlas DH, 22.379 obs decenal)
  - IDEB nao tem mais espelho em IPEA — usar coletor INEP direto.

### 2.5 Eurostat — `RemoteProtocolError` transitorio

**Sintoma**: `peer closed connection without sending complete message body`.

**Investigacao**: o endpoint `educ_uoe_enrt01?format=JSON&geo=BR&time=2020`
funcionou em curl simples — era flutuacao de rede no momento da execucao.

**Correcao**: nenhuma mudanca de codigo. O `@task(retries=3)` ja existente
no flow trata casos similares automaticamente. Apenas re-executar.

Resultado: 3 datasets coletados, 246k linhas em ~30 segundos.

---

## 3. Adicoes/mudancas em codigo

| Mudanca | Arquivo |
|---|---|
| Novo coletor UIS REST | `data_pipeline/src/collectors/unesco/uis_rest_client.py` |
| Re-export | `data_pipeline/src/collectors/unesco/__init__.py` |
| Flow UIS reescrito | `data_pipeline/src/flows/unesco.py` |
| Testes UIS REST (11) | `data_pipeline/tests/collectors/unesco/test_uis_rest_client.py` |
| Testes flow UIS atualizados | `data_pipeline/tests/flows/test_unesco.py` |
| OCDE flow IDs | `data_pipeline/src/flows/oecd.py` |
| CEPAL host | `data_pipeline/src/config.py` |
| CEPAL flow IDs | `data_pipeline/src/flows/cepalstat.py` |
| IPEA flow series | `data_pipeline/src/flows/ipea.py` |
| Parser SDMX layout AllDimensions | `data_pipeline/src/utils/sdmx_json.py` |

### 3.1 Metricas

```
Linhas adicionadas em data_pipeline/src:    ~210
Linhas adicionadas em data_pipeline/tests:  ~135
Testes verdes apos Fase 1.5:                171 / 171
Tempo do build dbt:                         ~6.8s
```

---

## 4. Bronze populada apos Fase 1.5

```
data/bronze/
├── ibge/sidra_7136/
│   ├── 2023/data.parquet        (3 KB)
│   └── 2025/data.parquet        (vazio — ano nao publicado)
├── ipea/
│   ├── serie_pnadca_txa15muf/all/   (231 obs)
│   ├── serie_adh_t_analf15m/all/    (22.379 obs)
│   └── [4 series legadas vazias do Sprint 2.0]
├── eurostat/
│   ├── dataset_educ_uoe_enrt01/2010-2023/   (160.140 obs)
│   ├── dataset_educ_uoe_fine01/2010-2023/   (78.828 obs)
│   └── dataset_edat_lfse_14/2010-2023/      (7.102 obs)
├── oecd/
│   ├── flow_oecd_..._fin_gdp_1_0/           (101.723 obs)
│   └── flow_oecd_..._perstud_3_1/           (2.784.295 obs)
├── unesco/
│   ├── indicator_cr_1/                      (2.074 obs)
│   ├── indicator_cr_2/                      (~)
│   ├── indicator_ner_1/                     (~)
│   ├── indicator_ner_2/                     (~)
│   ├── indicator_xgdp_fsgov/                (3.359 obs - gasto % PIB)
│   ├── indicator_xgovexp_imf/               (~)
│   ├── indicator_fosep_1_gpv/               (~)
│   └── indicator_lr_ag15t99/                (5.601 obs)
└── worldbank/
    └── 6 indicators × 2000-2023             (~32k obs total)
```

**Total Bronze**: ~3.2M observacoes em 7 fontes. CEPALSTAT pendente.

---

## 5. Debito Fase 1.5b (prox sprint de manutencao)

1. **CEPALSTAT parser refactor**: implementar lookup de dim IDs via
   `/indicator/{id}/structure` ou similar. Validar que as 4 dimensoes
   (`dim_208`, `dim_144`, `dim_29117`, `iso3`) sejam resolvidas para
   labels canonicos.

2. **INEP IDEB**: como nao tem espelho em IPEA, validar que o coletor
   INEP IDEB direto (`data_pipeline/src/collectors/inep/ideb.py`)
   funciona com a URL atual da planilha XLSX 2023.

3. **R PISA/TIMSS/PIRLS**: ainda nao executados (R nao instalado nesta
   maquina). Necessarios para `int_indicadores__avaliacoes_estudantes`.

4. **Cobertura mais ampla de coletores Eurostat e OCDE**: hoje so 3+2
   datasets respectivamente. Expandir conforme necessidades dos marts
   da Fase 3.

---

## 6. Como retomar

```bash
# 1. Pull (estado pos-1.5)
git pull origin main

# 2. Reinstalar venvs
cd data_pipeline && uv venv && uv pip install -e ".[dev]" && cd ..
cd dbt_project && python -m venv .venv && source .venv/Scripts/activate && pip install dbt-core dbt-duckdb && cd ..

# 3. Rodar testes (171 esperados)
cd data_pipeline && source .venv/Scripts/activate && python -m pytest tests/ -q

# 4. Popular Bronze
DATA_ROOT="$PWD/../data" python -m src.flows.worldbank
DATA_ROOT="$PWD/../data" python -m src.flows.unesco
DATA_ROOT="$PWD/../data" python -m src.flows.oecd
DATA_ROOT="$PWD/../data" python -m src.flows.eurostat
DATA_ROOT="$PWD/../data" python -m src.flows.ipea
DATA_ROOT="$PWD/../data" python -m src.flows.ibge_sidra

# 5. Rodar dbt (77 testes verdes esperados)
cd ../dbt_project && DBT_PROFILES_DIR=. dbt build
```

---

*Continuacao logica: Sprint 1.5b (parser CEPALSTAT) ou Sprint 2.2
(staging das demais fontes em dbt). Recomendado 2.2 primeiro pois
unlock vem-com-dados é maior que CEPALSTAT.*
