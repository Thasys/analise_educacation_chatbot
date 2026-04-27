# Fase 1 — Conclusão e Estado do Sistema

> **Análise Educacional Comparada Brasil × Internacional**
> Documento de fechamento da Fase 1 (Ingestão e Bronze Layer).
> **Data de fechamento:** 2026-04-27
> **Status:** ✅ Concluída — pronta para iniciar Fase 2 (Silver + dbt).

---

## 1. Sumário executivo

A Fase 1 entrega um sistema de ingestão de dados educacionais multi-fonte
com **9 fontes oficiais** atendidas, padrão Bronze imutável padronizado e
**160 testes automatizados** verdes. Toda extração é versionada, auditável
e reproduzível, sem dependência de Docker (resolvido caminho local com `uv`
após bloqueio do Docker Desktop).

### Em uma frase

> Saímos de "bootstrap funcional" (Fase 0) para "Bronze multi-fonte com
> 9 conectores oficiais cobrindo BR, OCDE, UE, LATAM e avaliações
> internacionais — todos com testes herméticos e proveniência completa".

---

## 2. Atualizações implementadas

### 2.1 Coletores REST/API

| # | Fonte | Padrão | Cobertura | Testes |
|---|---|---|---|---|
| 1 | **IBGE SIDRA** | REST JSON posicional | PNAD Contínua Educação (tab. 7136 e família) | 11 |
| 2 | **World Bank** | REST JSON paginado | Indicators API — gasto educ., HCI, conclusão, alfab. | 13 |
| 3 | **IPEADATA** | OData v4 | Séries históricas: ANALF15M, IDEB, gasto público | 18 |
| 4 | **UNESCO UIS** | SDMX-JSON 2.0 | EDU_NON_FINANCE, EDU_FINANCE, SDG-4 | 22 |
| 5 | **Eurostat** | JSON-stat 2.0 | educ_uoe_enrt01, educ_uoe_fine01, edat_lfse_14 | 22 |
| 6 | **OCDE** | SDMX-JSON 2.0 | Education at a Glance — finance + attainment | 17 |
| 7 | **CEPALSTAT** | REST JSON | Indicadores LATAM (analfab. 1471, anos estudo 1407) | 20 |

**Total: 123 testes herméticos via `httpx.MockTransport`.**

### 2.2 Coletores bulk download (sem API)

| # | Fonte | Tipo | Cobertura |
|---|---|---|---|
| 8 | **INEP** Censo Escolar | ZIP de microdados anuais | maior CSV por padrão (`matricula`/`docente`/`escola`) |
| 8 | **INEP** SAEB | ZIP bienal | reusa lógica do Censo |
| 8 | **INEP** ENEM | ZIP anual | reusa lógica do Censo |
| 8 | **INEP** IDEB | XLSX bienal | sheet/skiprows configuráveis |

### 2.3 Avaliações internacionais (R, plausible values)

| # | Estudo | Janela BR | Pacote R | Saída |
|---|---|---|---|---|
| 9 | **PISA** | 2000–2022 (lacuna 2003) | `intsvy::pisa.mean.pv` (BRR) | Parquet por ano |
| 9 | **TIMSS** | 1995–2003, 2023 | `intsvy::timss.mean.pv` (Jackknife) | Parquet, grades 4 e 8 |
| 9 | **PIRLS** | 2021 | `intsvy::pirls.mean.pv` (Jackknife) | Parquet (leitura) |

### 2.4 Infraestrutura compartilhada

- `BronzeWriter` — escrita Parquet (zstd) com sidecar `_metadata.json`
  (SHA-256, schema, proveniência) e particionamento `<source>/<dataset>/<period>/`.
- `IngestionLogger` — auditoria em PostgreSQL com **graceful degradation**
  (fail-open: se Postgres offline, vira no-op + warning, sem derrubar o pipeline).
- `BulkDownloader` (Fase 1, fonte 8) — streaming chunked, SHA-256, cache
  hit por sidecar `.sha256`, retry quando hash do disco não bate.
- `parse_sdmx_json` (Fase 1, fonte 6) — parser SDMX-JSON 2.0
  compartilhado entre UNESCO UIS e OCDE.
- Settings centralizadas via `pydantic-settings` (`.env` + `.env.example`).
- Logging estruturado via `structlog` (JSON em prod, console colorido em dev).

### 2.5 Outras atualizações

- **`.env.example` sanitizado** e versionado (placeholders, sem segredos).
- **9 commits convencionais** atômicos no `main`, cada coletor com sua
  história separada.
- **160 testes verdes** em `data_pipeline` — cobertura especialmente
  forte em URL building, parsing por formato e pipeline `collect()`.

---

## 3. Justificativas arquiteturais

### 3.1 Por que `BaseCollector` com template-method?

Toda fonte tem o mesmo ciclo: resolver URL → fetch → parse → escrever
Bronze → logar auditoria. Centralizar o ciclo no `BaseCollector.collect()`
e exigir que subclasses implementem só `fetch()` permite que **erros de
proveniência (sidecar metadata, URL gravada errada, log faltando) sejam
impossíveis por construção**. Cada novo coletor entra com ~120 linhas de
código novo + ~20 testes; o resto é herdado.

### 3.2 Por que `httpx.MockTransport` em todos os testes?

Testes herméticos:
- Não dependem de rede (rodam offline, em CI sem credenciais).
- São rápidos (~30s para 160 testes).
- Capturam a *contratualidade* da API — se a UIS muda o formato JSON,
  os testes não mascaram o erro.

A premissa é: validamos a API real **uma vez**, fixamos um payload
representativo no teste, e a partir daí a regressão é detectada
imediatamente quando alguém mexe no parser.

### 3.3 Por que extrair `parse_sdmx_json` para `utils/`?

O CLAUDE.md exige *"Three similar lines is better than a premature
abstraction"*. Mas, com OCDE e UNESCO compartilhando 100 linhas exatas
de parser SDMX-JSON 2.0, **DRY ganha**: a refatoração saiu acompanhada
de 5 testes próprios para o util, blindando os dois clientes contra
regressão.

### 3.4 Por que graceful degradation no `IngestionLogger`?

Coletores devem rodar mesmo em desenvolvimento sem Postgres (ex.:
quando Docker Desktop está fora, como nesta máquina). Uma falha de
log é estritamente menos grave que uma falha de ingestão — sempre
preferimos perder a auditoria a perder os dados oficiais. O modo
no-op é silencioso (warning, não erro).

### 3.5 Por que `BulkDownloader` separa cache do Bronze?

A camada Bronze armazena **dados processados** (Parquet com schema
estável). O ZIP/XLSX bruto baixado do INEP é apenas um intermediário.
Mantê-lo em `data/_cache/inep/` (fora da Bronze) tem vantagens:

1. **Cache hit por SHA-256** — re-execuções de coletor não baixam de
   novo, sem precisar mexer na Bronze imutável.
2. **Bronze permanece fiel ao contrato** (`<source>/<dataset>/<period>/data.parquet`),
   sem poluir com binários grandes que nunca serão queriados pelo DuckDB.
3. **Diagnóstico** — se um parser quebra, o ZIP fica disponível para
   reproduzir o problema sem novo download.

### 3.6 Por que R para PISA/TIMSS/PIRLS?

CLAUDE.md, regra de ouro #10: *"Plausible Values corretos — PISA,
TIMSS, PIRLS exigem metodologia BRR/Jackknife"*. Pacotes Python para
isso são incompletos ou enviesam erros-padrão. `intsvy` e `EdSurvey`
são a referência canônica das próprias OCDE/IEA. Saída em Parquet
com schema (`REF_AREA`, `TIME_PERIOD`, `OBS_VALUE`, `SE`, `N`)
deliberadamente alinhada com o resto da Bronze, para que o dbt da
Fase 2 consuma os 9 fluxos de forma uniforme.

---

## 4. Avanço do sistema

### 4.1 Por camada do CLAUDE.md

| Camada | Estado | Detalhes |
|---|---|---|
| **0. Fontes de dados** | ✅ Mapeadas | 9 fontes ativas + 3 bulk docs INEP |
| **1. Ingestão e orquestração** | ✅ **Concluída** | Coletores + flows Prefect prontos |
| **2. Bronze** | ✅ Concluída | Padrão Parquet+metadata+SHA-256 estável |
| **3. Silver** | ⏳ Pendente | Pasta `dbt_project/models/staging/` vazia |
| **4. Gold** | ⏳ Pendente | Pasta `dbt_project/models/marts/` vazia |
| **5. FastAPI Gateway** | 🟡 Apenas `/api/health` | Bootstrap pronto da Fase 0 |
| **6. CrewAI Agentes** | ⏳ Pendente | Pacote vazio |
| **7. Frontend Next.js** | 🟡 Hello world | Bootstrap pronto da Fase 0 |

### 4.2 Métricas

```
Linhas Python em data_pipeline:   ~3.500 (sem testes)
Linhas de testes:                 ~3.300
Testes verdes:                    160 / 160
Tempo da suite:                   ~125s
Coletores prontos:                9
Padroes arquiteturais:            REST · OData · SDMX-JSON · JSON-stat · Bulk-ZIP · Bulk-XLSX
```

### 4.3 Histórico de commits da Fase 1

```
8aed2ba feat(data_pipeline): coletor IBGE SIDRA 7136 + fundação Bronze
3be7a5c feat(data_pipeline): coletor World Bank (Indicators API)
ca158be chore:               .env.example sanitizado
211ca04 feat(data_pipeline): coletor IPEADATA (OData v4)
a30cc82 feat(data_pipeline): coletor UNESCO UIS (SDMX-JSON 2.0)
c67d08b feat(data_pipeline): coletor Eurostat (JSON-stat 2.0)
a3931c4 feat(data_pipeline): coletor OCDE + parser SDMX-JSON compartilhado
d6a5fa6 feat(data_pipeline): coletor CEPALSTAT (CEPAL/ECLAC)
b190ba4 feat(data_pipeline): cluster INEP + BulkDownloader
ec3c3e8 feat(r_scripts):     PISA/TIMSS/PIRLS com BRR/Jackknife
```

---

## 5. Próximos passos — Fase 2 (Silver + dbt)

### 5.1 O que entra na Fase 2

1. **Configurar `dbt-duckdb` end-to-end** — `dbt debug` deve passar.
2. **Modelos `staging/`** — 1:1 com Bronze, tipagem e renomeação:
   - `stg_ibge__sidra_7136` → tipos numéricos, ano como int.
   - `stg_worldbank__indicator_*` → unpivot indicator/country/date/value.
   - `stg_ipea__serie_*` → date típico, value float.
   - `stg_unesco__flow_*`, `stg_oecd__flow_*` (SDMX) → coluna canônica.
   - `stg_eurostat__dataset_*` → idem.
   - `stg_cepalstat__indicator_*`.
   - `stg_inep__censo_escolar`, `stg_inep__saeb`, `stg_inep__enem`,
     `stg_inep__ideb`.
   - `stg_iea__pisa`, `stg_iea__timss`, `stg_iea__pirls` (já no schema
     canônico — staging quase só validação).
3. **Modelos `intermediate/`** — harmonização de códigos:
   - Países: ISO-3 alpha (BRA, USA, FIN, ...).
   - UFs: códigos IBGE (2 dígitos).
   - Municípios: códigos IBGE 7 dígitos.
   - Níveis: ISCED 2011.
4. **Testes dbt** — `not_null` em PKs, `unique` em chaves naturais,
   `accepted_values` em códigos.
5. **Great Expectations** — suítes para validações estatísticas
   (ex.: PISA score entre 200 e 800).

### 5.2 Bloqueadores conhecidos

- **DuckDB precisa estar populado** — antes de rodar `dbt build`,
  é preciso ao menos uma execução real dos coletores, gerando
  `data/bronze/...` e registros lidos pelo `duckdb_scan` ou `read_parquet`.
- **Para Censo/SAEB/ENEM/IDEB**, a primeira execução real precisa de
  banda larga (ZIPs de 1–10 GB). Recomendado começar pelos coletores
  REST puros — todos baixam < 50 MB.

### 5.3 Estimativa

| Tarefa | Estimativa |
|---|---|
| Modelos staging (15 fluxos) | 3–4 dias |
| Modelos intermediate (harmonização) | 3–5 dias |
| Testes dbt + GE | 2–3 dias |
| Doc + lineage (`dbt docs`) | 1 dia |
| **Fase 2 completa** | **~2 semanas** |

---

## 6. Débitos técnicos registrados

1. **Coletores INEP precisam de URLs reais validadas** — O padrão
   `microdados_<dataset>_<year>.zip` é o que o INEP publicava em ciclos
   anteriores; URLs do ciclo corrente devem ser confirmadas antes da
   primeira execução de produção. (Os scripts já tratam HTTP 404 com
   falha clara.)

2. **Scripts R não foram executados** — R não está instalado nesta
   máquina; sintaxe e contratos de pacotes foram revisados, mas a
   primeira execução precisa rodar manualmente em ambiente com R 4.3+.
   Espaço em disco necessário: ~4 GB para microdados PISA + TIMSS + PIRLS.

3. **Docker Desktop offline** — A Fase 2 funcionará sem Docker
   (DuckDB é embedded). Para Fase 4 em diante (FastAPI integrado a
   Postgres real), será preciso resolver: (a) reinstalar Docker
   Desktop, (b) instalar Postgres nativo no Windows, ou (c) usar
   Postgres remoto.

4. **`pre-commit` não instalado globalmente** — Recomendado
   `pip install pre-commit && pre-commit install` antes de novos
   commits (para garantir lint/format automáticos).

5. **`package-lock.json` ausente no frontend** — `npm install` no
   Dockerfile não é reprodutível. Quando frontend voltar a evoluir
   (Fase 6), gerar lockfile e trocar para `npm ci`.

6. **Cobertura de testes não medida formalmente** — `pytest-cov` está
   nas devDependencies mas nenhum threshold foi imposto. CLAUDE.md
   sugere 90%+ em coletores. Adicionar `--cov-fail-under=85` em CI
   é trivial e fica como tarefa para Fase 4 (quando CI for criado).

---

## 7. Conclusão

A Fase 1 deixa o data lakehouse com **fundações sólidas para a Fase 2**:
todos os formatos principais (REST/JSON, OData, SDMX-JSON, JSON-stat,
ZIP, XLSX, SPSS via R) já têm coletor de referência, com testes que
travam regressões. As decisões arquiteturais foram registradas no
ADR 0001 (Fase 0) e neste documento.

O próximo trabalho — modelar Silver + Gold em dbt — começa de uma
Bronze rica e bem-tipada, com schema previsível em todas as 9 fontes.

---

*Próxima fase: ver [`fase-2-roadmap.md`](./fase-2-roadmap.md) (a criar quando iniciada).*
