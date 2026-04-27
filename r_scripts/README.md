# Scripts R — Avaliações Internacionais (PISA, TIMSS, PIRLS)

Scripts de extração e agregação de microdados das três grandes avaliações
internacionais cujas análises corretas exigem **plausible values** (PVs) com
metodologia **BRR/Jackknife**. Implementadas em R porque os pacotes oficiais
(`EdSurvey`, `intsvy`) são a referência canônica.

> **Por que R e não Python?** A maioria das análises em Python que existe na
> literatura para PISA tira média simples dos 10 plausible values, o que
> **viesa drasticamente os erros-padrão**. As funções `intsvy::pisa.mean.pv`
> e `EdSurvey::edsurveyTable` aplicam BRR/Jackknife conforme o manual técnico
> oficial. Nenhuma análise estatisticamente válida pode pular esse passo.

## Estrutura

```
r_scripts/
├── _packages.R               # lista canônica de pacotes (alimenta renv)
├── pisa_extraction.R         # OECD PISA (Brasil 2000+; lacuna 2003)
├── timss_extraction.R        # IEA TIMSS (Brasil 2003 e 2023)
├── pirls_extraction.R        # IEA PIRLS (Brasil 2021)
└── README.md
```

## Setup (uma vez por máquina)

```bash
# 1. Instalar R 4.3+
# 2. No diretório r_scripts:
Rscript -e 'install.packages("renv"); renv::init()'

# 3. Restaurar pacotes a partir do _packages.R:
Rscript -e 'source("_packages.R"); renv::snapshot()'
```

A primeira execução de `EdSurvey::downloadPISA()` baixa os microdados SPSS para
`data/_cache/iea/` (≈ 4 GB para todos os ciclos PISA).

## Execução

```bash
# PISA: ano único ou múltiplos
Rscript pisa_extraction.R 2018 2022

# TIMSS: ano único
Rscript timss_extraction.R 2023

# PIRLS:
Rscript pirls_extraction.R 2021
```

Cada script salva agregados pré-calculados em `data/bronze/iea/<study>/<year>/`
no formato Parquet, prontos para consumo por dbt e pelas Gold tables.

## Brasil — janelas de participação

| Estudo | Anos com Brasil                                |
| ------ | ---------------------------------------------- |
| PISA   | 2000, 2003, 2006, 2009, 2012, 2015, 2018, 2022 |
| TIMSS  | 1995, 1999, 2003, **(lacuna 2007–2019)**, 2023 |
| PIRLS  | **2021** (primeira participação)               |

⚠ A lacuna do TIMSS impede tendências comparáveis pré-2007 sem ressalvas
metodológicas explícitas. Documentar em qualquer análise.

## Brasil NÃO participa de

- **PIAAC** (alfabetização adultos) → usar INAF como análogo
- **ICILS** (letramento digital) → usar TIC Educação (CETIC.br)

Os scripts não cobrem essas avaliações; substitutos vivem em outras
camadas da Bronze (futuros coletores específicos).
