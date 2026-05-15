# Fase 2 — Conclusão e Estado do Sistema

> **Análise Educacional Comparada Brasil × Internacional**
> Documento de fechamento da Fase 2 (Silver Layer + dbt + Cross-source).
> **Data de fechamento:** 2026-04-29
> **Status:** ✅ Concluída — pronta para iniciar Fase 3 (Gold Layer / marts).

---

## 1. Sumário executivo

A Fase 2 transforma a Bronze multi-fonte em uma camada Silver harmonizada
e testada, com 7 stagings, 5 intermediates seguindo schema canônico, e
**3,2 milhões de observações queriáveis em SQL puro via DuckDB**.

A concretização do schema canônico Silver foi exercitada em dois
indicadores cross-source — gasto em educação (3 fontes) e taxa de
alfabetização (4 fontes) — provando que a abordagem **UNION ALL com
`source` distinto** preserva metodologia original e revela divergências
metodológicas legítimas que estariam mascaradas em uma média agregada.

### Em uma frase

> Saímos de "Bronze multi-fonte com 9 conectores" (Fase 1) para "Silver
> com schema canônico, 6 fontes empilhadas e 100 testes dbt verdes,
> capaz de responder em SQL puro perguntas como 'compare gasto em
> educação BR × OCDE × LATAM nos últimos 10 anos'".

---

## 2. Atualizações implementadas

### 2.1 Sprints da Fase 2

| Sprint | Entregáveis | Linhas SQL | Testes |
|---|---|---|---|
| **2.0 — Setup** | dbt-duckdb, 3 seeds, 6 macros, 2 stagings, 2 intermediates | ~600 | 52 |
| **1.5 — Manutenção coletores** | UIS REST collector, parser SDMX `AllDimensions`, IDs OECD/IPEA/CEPAL atualizados | ~450 | +11 (171) |
| **2.1 — Geografia & classificações** | `int_geografia__ufs_brasil`, `int_classificacoes__isced_2011`, stagings UIS/IPEA | ~250 | 77 |
| **2.2 — Stagings restantes** | `stg_eurostat__datasets`, `stg_oecd__flows`, gasto_educacao com OECD | ~200 | 84 |
| **2.3 — Cross-source #1** | `int_indicadores__alfabetizacao` (3 fontes) | ~150 | 95 |
| **1.5b — Refactor parser CEPAL** | Coletor com `/dimensions` lookup, alfabetizacao 4ª fonte | ~250 | 100 |
| **2.5 — Documentação** | `dbt docs generate`, ADR 0002, este documento | — | 100 |

**Total Fase 2: ~1.900 linhas SQL + 350 linhas Python adicional, 100 testes
dbt + 180 testes Python verdes.**

### 2.2 Stagings (7 fontes)

| Modelo | Fonte | Linhas | Materialização |
|---|---|---|---|
| `stg_worldbank__indicators` | World Bank Indicators API | 34.377 | view |
| `stg_unesco__indicators` | UIS REST API (post Fase 1.5) | 17.323 | view |
| `stg_oecd__flows` | OCDE SDMX (parser AllDimensions) | **2.886.018** | view |
| `stg_eurostat__datasets` | Eurostat JSON-stat (3 datasets) | 246.070 | view |
| `stg_ipea__series` | IPEADATA OData v4 | 22.610 | view |
| `stg_cepalstat__indicators` | CEPAL/ECLAC REST v1 | 20.855 | view |
| `stg_ibge__sidra_7136` | IBGE SIDRA tab 7136 | 4 | view |
| **TOTAL** | | **3.227.257** | |

### 2.3 Intermediates (5 modelos canônicos)

| Modelo | Linhas | Cobertura |
|---|---|---|
| `int_geografia__paises_harmonizados` | 97 | Países presentes em ≥1 fonte (drops AFE, EAS, WLD) |
| `int_geografia__ufs_brasil` | 27 | UFs com flag `observed_in_ipea` |
| `int_classificacoes__isced_2011` | 9 | ISCED com aliases por fonte (Eurostat ED*, OCDE ISCED11_*, UIS L*) |
| `int_indicadores__gasto_educacao` | 3.903 | World Bank + UNESCO + OCDE empilhados |
| `int_indicadores__alfabetizacao` | 1.193 | World Bank + UNESCO + IPEA + CEPALSTAT empilhados |

### 2.4 Validações cruzadas (data quality)

#### Gasto público em educação (% PIB), Brasil

| Ano | World Bank | UNESCO | OCDE | Comentário |
|---|---|---|---|---|
| 2018 | 6.089 | 6.089 | 4.954 | UIS=WB perfeito; OCDE -1.1pp por base UOE |
| 2019 | 5.963 | 5.963 | 4.890 | idem |
| 2020 | 5.771 | 5.771 | 4.586 | idem |
| 2021 | 5.497 | 5.497 | — | OCDE atrasa ~1 ano |
| 2022 | 5.619 | 5.619 | — | idem |

**WB é ressindicação de UIS** — match perfeito ao centésimo confirma.
**OCDE diverge ~1pp** consistentemente porque usa coleta UOE com
perímetro próprio (diferente do GFS-IMF usado por WB/UIS). Diferença
metodológica legítima, documentada no SQL.

#### Taxa de alfabetização 15+, Brasil

| Ano | WB | UNESCO | CEPAL | IPEA |
|---|---|---|---|---|
| 2015 | 92.05 | 92.05 | 92.05 | 93.30 |
| 2018 | 93.23 | 93.23 | — | 93.90 |
| 2022 | 94.38 | 94.38 | — | 94.40 (PNADCA) / 93.00 (Atlas DH) |
| 2024 | — | — | — | 94.70 |

**WB/UIS/CEPAL alinhados ao centésimo** (UIS é fonte primária).
**IPEA PNADCA difere ~1pp** por usar PNAD Contínua autodeclaratória
(metodologia diferente). Atlas DH (decenal Censo) também desvia.

### 2.5 Sistema de seeds e macros

**Seeds (3, total 131 linhas):**
- `iso_3166_paises` (95 países com agrupamento analítico latam/oecd/brics/asia/africa_mena/europe_other)
- `ibge_ufs` (27 UFs)
- `isced_2011` (9 níveis)

**Macros (6):**
- `harmonize_country_iso3` / `harmonize_country_iso2` / `harmonize_country_m49` / `harmonize_country_name_pt`
- `safe_to_year` (extrai 4 dígitos iniciais; cobre `2023`, `2022-Q1`, `2022M03`)
- `safe_to_double` (NULL para `..`, `...`, `-`, vazio)

### 2.6 Coletores reformados na Fase 1.5

Coletores que pararam de funcionar entre a Fase 1 e a primeira execução
real durante o Sprint 2.0:

| Fonte | Causa | Correção |
|---|---|---|
| **UNESCO UIS** | Migração SDMX → REST flat (fev/2026) | Novo `UisRestCollector` + flow + 11 testes |
| **OCDE SDMX** | Reorganização de dataflow IDs (DSD_EAG_FIN → DSD_EAG_UOE_FIN) | IDs atualizados + parser estendido para `dimensionAtObservation=AllDimensions` |
| **CEPALSTAT** | Migração de host + resposta agora dimensional (dim_* IDs) | Refactor completo (Sprint 1.5b): segunda chamada `/dimensions` resolve dim IDs em labels |
| **IPEADATA** | Séries `ANALF15M`, `IDEB_BR_*` aposentadas | Substituídas por `PNADCA_TXA15MUF`, `ADH_T_ANALF15M` |
| **Eurostat** | `RemoteProtocolError` transitório | Sem mudança — retry automático já existe |

---

## 3. Justificativas arquiteturais

Detalhes completos em [`ADR 0002`](../adrs/0002-fase-2-schema-canonico-silver.md). Resumo:

### 3.1 UNION ALL, não JOIN nem AVG entre fontes

Cada fonte vira uma linha separada com `source` distinto. Agregar
mascara metodologia. Diferenças de ~1pp entre fontes para o mesmo
país/ano são **legítimas, não bugs**.

### 3.2 Schema canônico fixo em todos `int_indicadores__*`

`country_iso3 · year · value · unit · indicator_id · indicator_name ·
source · source_indicator_id`. Tabelas extras (com std_error, isced_level,
sex, etc.) ficam para intermediates específicos quando a dimensão é
analiticamente relevante.

### 3.3 Granularidade `country_iso3` na Silver

Subnacional (UFs/municípios IPEA, regiões NUTS-2 Eurostat) é dimensão
ortogonal e ganha modelos separados. Misturar grãos quebra `JOIN` com
seed de países.

### 3.4 Filtragem rigorosa via INNER JOIN com seed

Agregados regionais (`AFE`, `EAS`, `WLD`) e códigos inválidos da fonte
desaparecem automaticamente — economiza checagens manuais.

### 3.5 Conversão pré-UNION para conceitos complementares

IPEA publica analfabetismo; convertemos para alfabetização (`100 - value`)
**antes** do UNION e marcamos `source_indicator_id` com sufixo `(inverted)`
para auditoria.

### 3.6 Dedup defensivo via `SELECT DISTINCT`

Chave natural `(country, year, source_indicator_id)`. Protege contra:
- Bronze com períodos sobrepostos (re-execução de coletor).
- Dimensões da fonte não filtradas (ex.: OCDE com `EXP_DESTINATION`).

### 3.7 Parser SDMX-JSON estendido para `AllDimensions`

OCDE atual responde com `observations` direto no `dataSet` quando
`dimensionAtObservation=AllDimensions`. O parser agora trata os dois
layouts (series-aware default + AllDimensions). Backwards-compatible —
todos os 38 testes existentes continuam passando.

---

## 4. Avanço do sistema

### 4.1 Por camada do CLAUDE.md

| Camada | Estado pré-Fase 2 | Estado pós-Fase 2 |
|---|---|---|
| **0. Fontes** | 9 mapeadas | 6 com dados reais (CEPAL, OECD, EUROSTAT, UIS, IPEA, WB) + SIDRA + INEP/IEA pendentes |
| **1. Ingestão** | ✅ | ✅ + UisRestCollector novo |
| **2. Bronze** | ✅ vazia | ✅ **3,2M observações** |
| **3. Silver** | ⏳ | ✅ **7 stagings + 5 intermediates** |
| **4. Gold** | ⏳ | ⏳ Próxima fase |
| **5. FastAPI** | 🟡 health | 🟡 idem |
| **6. CrewAI** | ⏳ | ⏳ |
| **7. Frontend** | 🟡 hello world | 🟡 idem |

### 4.2 Métricas finais

```
Stagings dbt:                    7 (todas as fontes com dados)
Intermediates dbt:               5 (3 dimensoes, 2 indicadores)
Materializacoes:                 3 seeds + 7 view + 5 table
Tests dbt:                       100 / 100 (PASS=100, ~4s)
Tests Python:                    180 / 180 (~170s)
Linhas Bronze (DuckDB):          3.227.257
Linhas Silver (intermediate):    5.229
Cobertura paises:                97 (de 95 da seed + 2 que apareceram extras)
Cobertura temporal:              1990-2024 (depende da fonte)
Indicadores cross-source:        2 (gasto_educacao, alfabetizacao)
```

### 4.3 Histórico de commits da Fase 2

```
425b8e6 feat(dbt): Fase 2 sprint 2.0 — seeds, macros e primeiros modelos Silver
17c7fac fix(data_pipeline): Fase 1.5 — manutencao dos coletores apos drift de APIs
bf260ef feat(dbt): Fase 2 sprint 2.1 — geografia, classificacoes e novas stagings
85e5726 feat(dbt): Fase 2 sprint 2.2 — stagings Eurostat e OECD
af69de7 feat(dbt): Fase 2 sprint 2.3 — int_indicadores__alfabetizacao cross-source
aa9cc01 fix(cepalstat): Sprint 1.5b — refactor parser para nova API REST v1
```

---

## 5. Próximos passos — Fase 3 (Gold Layer)

### 5.1 O que entra na Fase 3

A Fase 3 constrói os **datasets analíticos finais** que alimentarão o
FastAPI (Fase 4) e os agentes CrewAI (Fase 5). Não há mais harmonização
nesta fase — só análise.

#### Marts propostos

```
mart_br_vs_ocde__gasto_educacao_timeseries
    BRA + 38 países OCDE × 2000-2023 × % PIB (3 fontes empilhadas)
    Ranking BR no contexto OCDE (top/bottom percentil)

mart_alfabetizacao_latam_2020s
    20 países LATAM × 2020-2024 × literacy %
    BR vs media LATAM, gap em pp

mart_pisa_rankings  (precisa R + microdados PISA)
    BRA + 81 paises participantes × ciclos 2000-2022
    Rankings com plausible values e BRR (intsvy/EdSurvey)

mart_ideb_municipal  (precisa coletor INEP IDEB)
    5570 municipios × ciclos bienais
    Distribuicao de scores, ranking estadual

mart_comparativo_global_litera_gasto
    Cruza alfabetizacao × gasto_educacao
    Detecta paises com investimento alto + alfabetizacao baixa
```

#### Indicadores derivados (em mart, não em intermediate)

- Gap em pontos padronizados (BR – OCDE_mean) / OCDE_std
- Tendência linear 5/10 anos (slope, R²)
- Posição percentil dentro de OCDE/LATAM
- Convergência/divergência ano-a-ano

### 5.2 O que **NÃO** entra na Fase 3

- INEP IDEB municipal (precisa coletor INEP funcional + ZIP da Bronze)
- PISA/TIMSS/PIRLS (precisa R instalado e microdados)
- CEPALSTAT desagregação por sexo (precisa intermediate específico)
- Subnacional brasileiro (UFs/municípios IPEA/SIDRA — modelos separados)

Estes ficam para Fase 3.5 ou se redistribuem em Fase 5+.

### 5.3 Bloqueadores conhecidos

1. **R não instalado** — bloqueia `mart_pisa_rankings`. Solução
   imediata: instalar R 4.3+ e rodar `r_scripts/_packages.R`.
2. **Coletores INEP não executados** — bloqueia `mart_ideb_municipal`.
   ZIPs do INEP têm 1-10GB cada; precisa banda + espaço em disco.
3. **OpenMetadata não configurado** — bloqueia catálogo navegável da
   Gold. Adiável, mas útil quando começar a Fase 5 (agentes).

### 5.4 Estimativa Fase 3

| Sprint | Tarefa | Estimativa |
|---|---|---|
| 3.1 | 2-3 marts diretos (timeseries, rankings) | 2-3 dias |
| 3.2 | Indicadores derivados (z-scores, percentis) | 2 dias |
| 3.3 | OpenMetadata + lineage | 1-2 dias |
| 3.4 | Documentação dbt-docs serve + testes range | 1 dia |
| **Fase 3 completa** | | **~1.5 semanas** |

---

## 6. Débitos técnicos registrados

Maioria herdada da Fase 1, alguns novos:

1. **R não executado nesta máquina** — `r_scripts/*.R` não testados.
   Necessário R 4.3+ com `renv::restore()` antes de qualquer mart PISA.

2. **Coletor INEP não executado em produção** — URLs do ciclo corrente
   não foram validadas. Os scripts já tratam HTTP 404 com falha clara,
   mas a primeira execução real precisa banda larga e ~50GB de disco.

3. **CEPALSTAT desagregação por sexo não modelada** — `int_indicadores__alfabetizacao`
   filtra `sex='Both sexes'` para alinhar ao schema canônico. Mart
   futuro pode expor a desagregação como dimensão extra.

4. **Eurostat `t2020_42` (gasto % PIB) não coletado** — `educ_uoe_fine01`
   só traz absolutos. Para que Eurostat entre em `gasto_educacao`,
   precisa coletor adicional. Não bloqueia — WB/UIS/OCDE já cobrem
   bem o indicador.

5. **Cobertura de testes Python não medida formalmente** — `pytest-cov`
   nas devDependencies mas sem threshold. Adicionar `--cov-fail-under=85`
   em CI será trivial na Fase 4.

6. **`pre-commit` ainda não instalado globalmente** — atualizar antes
   de novos commits para garantir lint/format automáticos.

7. **Subnacional brasileiro (UFs/municípios IPEA + SIDRA)** — não modelado.
   `int_geografia__ufs_brasil` existe mas indicadores subnacionais ficam
   para Sprint 4+ ou Fase 3.5.

8. **OpenMetadata stub criado mas não configurado** — `infra/openmetadata/`
   é um placeholder vazio (.gitkeep). Configurar quando começar Fase 5.

---

## 7. Conclusão

A Fase 2 deixa o data lakehouse com **fundações sólidas para a Fase 3**:
o schema canônico Silver já foi estressado em 2 indicadores cross-source
distintos (gasto + alfabetização), com 4 metodologias diferentes
produzindo divergências reveladoras (não bugs). A escolha de UNION ALL
em vez de média/JOIN provou-se correta — a tabela canônica
**documenta a controvérsia metodológica**, não a esconde.

O próximo trabalho — modelar marts analíticos em Gold — começa de uma
Silver bem-tipada, testada e agnóstica de path, com 3,2M observações
queriáveis em DuckDB local. As decisões metodológicas estão registradas
em ADRs (0001 e 0002) e nos comentários inline de cada modelo dbt.

---

*Próxima fase: ver [`fase-3-analise.md`](./fase-3-analise.md) (a criar
ao iniciar). Documento de migração para outra máquina permanece em
[`fase-2-sprint-2.0-progresso.md`](./fase-2-sprint-2.0-progresso.md).*
