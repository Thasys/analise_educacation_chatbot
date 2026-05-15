# Notas metodológicas

Regras que existem para garantir **validade acadêmica dos resultados**.
Violar qualquer uma invalida a pesquisa.

## 1. Plausible Values (PISA, TIMSS, PIRLS)

Microdados de avaliações internacionais usam **10 plausible values** em
vez de um único score. Análises corretas:

- Sempre usar pacotes especializados: `intsvy`, `EdSurvey`, `RALSA`
  (todos R — ver [`../r_scripts/README.md`](../r_scripts/README.md)).
- Ou em Python: `pisapy` / exportar agregados pré-calculados via OECD
  Data Explorer.
- **NUNCA tirar média simples dos PVs** — viesa erros-padrão.
- Aplicar pesos BRR ou Jackknife conforme metodologia do estudo.
- Referência: OECD PISA Data Analysis Manual (2024).

O Statistician Agent retorna `method="plausible_values_pending"` quando
detecta pergunta sobre PISA/TIMSS/PIRLS — a pipeline ainda não implementa
essa metodologia.

## 2. Harmonização de códigos

- **Países:** ISO-3166-alpha3 (`BRA`, `FIN`, `USA`, etc.)
- **UFs:** códigos IBGE (2 dígitos)
- **Municípios:** códigos IBGE **7 dígitos** (não usar 6 dígitos legado)
- **Níveis educacionais:** **ISCED 2011**
  - 0: ECEC (Educação Infantil)
  - 1: Ensino Fundamental Anos Iniciais
  - 2: Ensino Fundamental Anos Finais
  - 3: Ensino Médio
  - 4+: pós-secundário

A camada `intermediate/` no dbt aplica essas harmonizações.

## 3. Comparabilidade temporal

| Avaliação | Cobertura Brasil | Cuidados |
|---|---|---|
| PISA | 2000 → presente | Comparável; mais sólido para tendências |
| TIMSS | 2003 + 2023 | **Lacuna de 20 anos** — tendências de longo prazo são complicadas |
| PIRLS | 2021 → presente | Brasil participou pela primeira vez em 2021 |
| Censo Escolar | 2007 → presente | Ruptura metodológica em 2007 (Educacenso) |
| SAEB | 1995 → presente | Antes de 2019 era ANEB/Prova Brasil; **escalas diferentes** |

O Comparativist Agent recebe instruções para incluir essas ressalvas em
`methodological_caveats` quando aplicável.

## 4. Brasil não participa de

| Avaliação | Análogo brasileiro |
|---|---|
| **PIAAC** (letramento de adultos) | INAF (Instituto Paulo Montenegro) |
| **ICILS** (letramento digital) | TIC Educação (CETIC.br) |

Para perguntas envolvendo esses domínios, o sistema deve indicar a
ausência de comparabilidade direta.

## 5. Copyright e citação

- Citar **sempre** a fonte oficial em toda resposta ao usuário
  (`sources_cited` no `FinalAnswer`).
- Não reproduzir mais de 15 palavras literais de qualquer fonte sem
  aspas explícitas.
- Para citações acadêmicas, usar **DOI** sempre que disponível.
- Respeitar **licença Open Government** dos datasets.
- O Citation Agent + guardrail `is_real_doi` ([ADR 0007](adrs/0007-fact-checker-post-synthesis.md))
  garantem que apenas DOIs com formato válido e fora da lista negra
  (`10.xxxx/...`, `10.yyyy/...`, etc.) chegam ao FinalAnswer.

## 6. APIs externas — observações

### `stats.oecd.org` foi descontinuado em 01/07/2024

Usar sempre **`sdmx.oecd.org/public/rest/`**. Rate limit: 60
queries/hora/IP (sem autenticação).

### Outras APIs

| Fonte | Endpoint atual | Notas |
|---|---|---|
| IBGE SIDRA | `https://apisidra.ibge.gov.br/values/...` | Sem rate limit conhecido |
| IPEADATA | `http://www.ipeadata.gov.br/api/odata4/` | OData v4, paginação via `@odata.nextLink` |
| World Bank | `https://api.worldbank.org/v2/...` | JSON, paginação por `page=N` |
| UNESCO UIS | `https://api.uis.unesco.org/api/public/...` | Migrou de SDMX para REST flat em 02/2026 |
| Eurostat | `https://ec.europa.eu/eurostat/api/dissemination/...` | JSON-stat 2.0 |
| OECD | `https://sdmx.oecd.org/public/rest/...` | SDMX-JSON 2.0 |
| CEPAL | `https://api-cepalstat.cepal.org/...` | REST v1, requer 2 chamadas (data + dimensoes) |

Coletores em `data_pipeline/src/collectors/<fonte>/` encapsulam essas
diferenças via `BaseCollector._http_fetch_json` / `_http_fetch_paginated`.

## 7. Fact-check e mitigação de alucinação

O sistema usa LLMs locais (Ollama Qwen 2.5) que ocasionalmente alucinam
números ou DOIs. Mitigações implementadas:

| Camada | Guardrail | Local |
|---|---|---|
| Numéricos | `check_numeric_consistency` — regex + tolerância 5% | [`crews/_helpers.py`](../agents/src/crews/_helpers.py) |
| DOIs | `is_real_doi` — rejeita `10.xxxx/...`, placeholders | [`tools/rag_tools.py`](../agents/src/tools/rag_tools.py) |
| Plotly | `_validate_figure` — rejeita `x`/`y` como string | [`tools/viz_tools.py`](../agents/src/tools/viz_tools.py) |
| Retriever | auto-populate determinístico | [`crews/analysis_crew.py`](../agents/src/crews/analysis_crew.py) |

Detalhes em [`adrs/0006-retriever-autopopulate.md`](adrs/0006-retriever-autopopulate.md)
e [`adrs/0007-fact-checker-post-synthesis.md`](adrs/0007-fact-checker-post-synthesis.md).

## 8. Referências bibliográficas fundamentais

Indexadas no RAG ChromaDB (`agents/src/rag/seeds/manifest.yaml` — 25 papers seed):

1. Schleicher, A. (2019). *World Class: How to Build a 21st-Century School System*. OECD Publishing.
2. Hanushek, E. A., & Woessmann, L. (2011). The economics of international differences in educational achievement. *Economic Policy*, 26(67).
3. Carnoy, M., Khavenson, T., Costa, L., & Marotta, L. (2015). A educação brasileira e o PISA. *Cadernos de Pesquisa*, 45(157).
4. Soares, J. F., & Alves, M. T. G. (2003). Desigualdades raciais no sistema brasileiro de educação básica. *Educação e Pesquisa*, 29(1).
5. Fernandes, R. (2007). *Índice de Desenvolvimento da Educação Básica (Ideb)*. Série Documental INEP, n.26.
6. Angrist, N., Djankov, S., Goldberg, P. K., & Patrinos, H. A. (2021). Measuring human capital using global learning data. *Nature*, 592.
7. OECD. (2024). *Education at a Glance 2024*. <https://doi.org/10.1787/c00cad36-en>
8. Mullis, I. V. S., et al. (2023). *PIRLS 2021 International Results in Reading*. Boston College.
9. UNESCO. (2020). *Global Education Monitoring Report 2020: Inclusion and Education*.
10. Barro, R. J., & Lee, J. W. (2013). A new data set of educational attainment in the world, 1950–2010. *Journal of Development Economics*, 104.

Manifest completo em [`agents/src/rag/seeds/manifest.yaml`](../agents/src/rag/seeds/manifest.yaml).

## 9. Glossário

| Sigla | Significado |
|---|---|
| **Medallion** | Padrão de data lake com 3 camadas (Bronze/Silver/Gold) |
| **BRR** | Balanced Repeated Replication — método de variância para amostras complexas |
| **Jackknife** | Técnica similar ao BRR para replicação de pesos |
| **Plausible Values** | Múltiplos valores simulados de proficiência (PISA/TIMSS/PIRLS) |
| **ISCED** | International Standard Classification of Education |
| **IDEB** | Índice de Desenvolvimento da Educação Básica (INEP) |
| **SAEB** | Sistema de Avaliação da Educação Básica (INEP) |
| **ENEM** | Exame Nacional do Ensino Médio (INEP) |
| **PISA** | Programme for International Student Assessment (OCDE) |
| **TIMSS** | Trends in International Mathematics and Science Study (IEA) |
| **PIRLS** | Progress in International Reading Literacy Study (IEA) |
| **ERCE** | Estudio Regional Comparativo y Explicativo (LLECE/UNESCO) |
| **TALIS** | Teaching and Learning International Survey (OCDE) |
| **SDMX** | Statistical Data and Metadata eXchange (padrão de APIs estatísticas) |
| **UOE** | UNESCO-OCDE-Eurostat (coleta conjunta) |
| **dbt** | data build tool (transformações SQL versionadas) |
| **RAG** | Retrieval-Augmented Generation |
| **SSE** | Server-Sent Events |
| **PNE** | Plano Nacional de Educação (Lei 13.005/2014) |
