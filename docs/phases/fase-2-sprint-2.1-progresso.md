# Fase 2 — Sprint 2.1 (Geografia & Classificações + novas stagings)

> Sprint 2.1 (parcial) e expansao das stagings para refletir Bronze
> repopulada apos Fase 1.5.
> **Data:** 2026-04-28

---

## 1. Entregas

### 1.1 Stagings novas

| Modelo | Fonte | Materialization | Linhas | Testes |
|---|---|---|---|---|
| `stg_unesco__indicators` | UIS REST API (8 indicadores) | view | ~25k | 5 |
| `stg_ipea__series` | IPEADATA (6 series — 2 reais + 4 vazias) | view | ~22k | 4 |

### 1.2 Intermediates Sprint 2.1

| Modelo | Materialization | Linhas | Funcao |
|---|---|---|---|
| `int_geografia__ufs_brasil` | table | 27 | Tabela canonica das UFs com flag `observed_in_ipea` |
| `int_classificacoes__isced_2011` | table | 9 | ISCED 2011 com aliases por fonte (Eurostat/OCDE/UIS) |

### 1.3 Expansao do `int_indicadores__gasto_educacao`

UNION ALL de **2 fontes** agora (era so World Bank):

- `worldbank` (`SE.XPD.TOTL.GD.ZS`)
- `unesco` (`XGDP.FSGOV` — escolha validada por match perfeito com WB)

Total: **3.436 observacoes** (1.718 por fonte, 96 paises, 2000-2023).

### 1.4 Atualizacao do `int_geografia__paises_harmonizados`

Agora considera UNION de paises observados em World Bank + UNESCO (era so WB).
Cresceu de 96 para 96 paises (sem aumento — UIS subset esta dentro de WB).

---

## 2. Validacao cruzada

Match perfeito entre fontes para gasto educacao % PIB do Brasil (UNESCO `XGDP.FSGOV` vs World Bank `SE.XPD.TOTL.GD.ZS`):

| Ano | UNESCO | World Bank |
|---|---|---|
| 2018 | 6.089 | 6.089 |
| 2019 | 5.963 | 5.963 |
| 2020 | 5.771 | 5.771 |
| 2021 | 5.497 | 5.497 |
| 2022 | 5.619 | 5.619 |

Confirmacao de que UIS publica os dados originais que WB depois reutiliza,
sem discrepancias metodologicas.

### 2.1 Aprendizado: indicadores UIS com nomes parecidos

A primeira escolha ingenua foi `XGOVEXP.IMF` ("Government expenditure on
education as a percentage of total government expenditure"), que resultou
em valores ~2x maiores que WB (12-13% vs 5-6%). Foi diagnostico rapido
porque a validacao cruzada por design ja estava incluida no fluxo.

A escolha correta para "% PIB" e `XGDP.FSGOV`. Documentado no SQL do
intermediate como **AVISO** para evitar repetir o erro com outros ciclos
de exposicao.

---

## 3. Build dbt apos 1.5 + 2.1

```
3 seeds  ·  4 view models (staging)  ·  4 table models (intermediate)  ·  66 tests
PASS=77  WARN=0  ERROR=0  SKIP=0   (~6.8s end-to-end)
```

---

## 4. Pendencias para Sprint 2.2

### 4.1 Staging das fontes restantes

Bronze populada mas ainda sem staging dbt:

- [ ] `stg_eurostat__datasets` (3 datasets em Bronze, ~246k linhas)
- [ ] `stg_oecd__flows` (2 dataflows em Bronze, ~2.9M linhas)
- [ ] `stg_inep__censo_escolar`, `stg_inep__saeb`, `stg_inep__enem`,
      `stg_inep__ideb` (depende de executar coletores INEP — banda)
- [ ] `stg_iea__pisa`, `stg_iea__timss`, `stg_iea__pirls` (depende de R)
- [ ] `stg_cepalstat__indicators` (depende de Sprint 1.5b)

### 4.2 Indicadores cross-source

- [ ] `int_indicadores__alfabetizacao` (SIDRA + WB + UIS LR.AG15T99 + IPEA)
- [ ] `int_indicadores__avaliacoes_estudantes` (PISA + TIMSS + PIRLS + SAEB)
- [ ] Expandir `gasto_educacao` com OECD `DSD_EAG_UOE_FIN@DF_UOE_INDIC_FIN_GDP`
      e Eurostat `educ_uoe_fine01` (com filtros corretos por ISCED+source).

### 4.3 Seed ibge_municipios

- 5570+ municipios. Adiamento deliberado — nao bloqueia indicadores
  no nivel pais/UF e exige carregamento via download do IBGE
  (https://www.ibge.gov.br/explica/codigos-dos-municipios.php).

---

## 5. Referencias

- Schema canonico Silver: ver [`fase-2-analise.md`](./fase-2-analise.md#34-schema-canonico-silver) §3.4
- Manutencao Fase 1.5: ver [`fase-1.5-manutencao-coletores.md`](./fase-1.5-manutencao-coletores.md)
- Ponto de partida: ver [`fase-2-sprint-2.0-progresso.md`](./fase-2-sprint-2.0-progresso.md)
