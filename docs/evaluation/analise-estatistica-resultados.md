# Análise estatística inferencial dos resultados (Seção 4 do paper)

> **Fase A** do prompt `prompt-analises-pos-resultados.md`.
> Gerado por `agents/evaluation/reports/statistical_analysis.py` sobre os
> JSONs já existentes — **custo $0, 100% determinístico, nenhum LLM
> invocado**. Reproduza com:
>
> ```bash
> cd agents && uv run python -m evaluation.reports.statistical_analysis \
>     --baseline evaluation/output/baseline_official.json \
>     --eduquery evaluation/output/eduquery_official_tcc.json \
>     --n3 evaluation/output/eduquery_n3.json \
>     --llm-direct evaluation/output/llm_direct.json \
>     --output evaluation/output/statistical_analysis.json
> ```

## Resumo executivo

A diferença de acurácia in-scope entre o pipeline RAG convencional
(baseline, 10,0%) e o EduQuery completo (63,3%) é **um efeito grande e
real** (Cohen's h = 1,20; IC 95% bootstrap do EduQuery [46,7%, 80,0%]
**não inclui** a média do baseline). O teste de McNemar pareado é
**fortemente significativo no conjunto numérico completo** (n=54,
p = 0,0026) e **borderline no recorte in-scope isolado** (n=10,
p exato = 0,0625) — honestamente subpotente por causa do n pequeno, não
por ausência de efeito. Reportamos os três recortes sem cherry-picking.

## 1. McNemar pareado (significância da diferença de acurácia)

McNemar é o teste correto para comparar dois classificadores sobre os
**mesmos itens** (pareamento por `id`). Contamos as transições
discordantes:

- `n_b` = baseline **errou** e EduQuery **acertou** (melhora);
- `n_c` = baseline **acertou** e EduQuery **errou** (regressão).

Reportamos o χ² com correção de continuidade de Yates **e** o p-valor
exato binomial (preferível quando `n_b + n_c` é pequeno).

| Recorte | n | n_b | n_c | χ² (cc) | p exato | Sig. α=0,05 |
|---|---:|---:|---:|---:|---:|:--:|
| **In-scope (claim principal)** | 10 | 5 | 0 | 3,20 | 0,0625 | **não** |
| Numérico (factual + comparativo) | 54 | 17 | 3 | 8,45 | 0,0026 | sim |
| In-scope, voto majoritário n=3 | 10 | 6 | 0 | 4,17 | 0,0312 | sim |

**Leitura honesta (regra #2 do prompt — números são pontos de chegada):**

- No recorte in-scope (n=10), **todos** os 5 pares discordantes favorecem
  o EduQuery (5 melhoras, 0 regressões). Mas com tão poucos itens o
  p exato é 0,0625 — *não* cruza α=0,05. Isso é uma limitação de
  **poder estatístico**, não de efeito: P(5 sucessos em 5 sob H0) = 1/32,
  e o teste two-sided dobra para 0,0625.
- No conjunto numérico completo (n=54), a diferença é **fortemente
  significativa** (p = 0,0026), com 17 melhoras contra apenas 3
  regressões.
- Usando a medida mais confiável do EduQuery (voto majoritário das 3
  repetições), o recorte in-scope cruza para significativo (p = 0,0312).

**Conclusão:** o efeito existe, é grande e consistente; o teste in-scope
isolado é apenas subpotente. Isso *motiva* aumentar n como trabalho
futuro (já parcialmente endereçado pelo n=3).

## 2. IC 95% bootstrap (acurácia in-scope)

5.000 reamostragens com reposição, `numpy.random.default_rng(seed=42)`.

| Modo | n obs. | Média | IC 95% |
|---|---:|---:|---:|
| Baseline | 10 | 10,0% | [0,0%, 30,0%] |
| EduQuery (n=3, 30 obs.) | 30 | 63,3% | [46,7%, 80,0%] |

O intervalo do EduQuery **não contém** a média do baseline (10,0%), o
que é evidência direta da diferença mesmo com o McNemar in-scope
borderline. Os intervalos **não se sobrepõem**.

## 3. Tamanhos de efeito

| Métrica | Valor | Interpretação |
|---|---:|---|
| Cohen's h (0,10 vs 0,633) | 1,20 | efeito **grande** (convenção: 0,2 / 0,5 / 0,8) |
| Cliff's delta (in-scope, binário) | 0,50 | dominância clara do EduQuery |
| ICC(2,1) entre repetições n=3 | 0,74 | confiabilidade **boa** do classifier |

O ICC ≈ 0,74 indica que o classificador determinístico é confiável entre
repetições: das 10 perguntas in-scope, 8 tiveram as 3 repetições
idênticas; apenas F-015 e F-016 oscilaram em 1 das 3 (ambas na fronteira
da tolerância de ±5%).

## 4. Frase sugerida para o `main.tex` (Seção 4 — Resultados)

> A diferença de acurácia in-scope entre o EduQuery e o pipeline RAG
> convencional corresponde a um tamanho de efeito grande (Cohen's
> *h* = 1,20), com o intervalo de confiança de 95% via bootstrap do
> EduQuery ([46,7\%, 80,0\%]) não incluindo a média do baseline (10,0\%).
> No conjunto completo de itens numéricos (*n* = 54), a diferença é
> estatisticamente significativa pelo teste de McNemar pareado
> (χ² = 8,45; *p* = 0,003). No recorte in-scope isolado (*n* = 10), todas
> as transições discordantes favorecem o EduQuery (5 melhoras, 0
> regressões), embora o teste seja subpotente pelo tamanho amostral
> (*p* exato = 0,06) — limitação que motiva a ampliação da bateria como
> trabalho futuro.

## 5. Limitações desta análise

- **n pequeno in-scope.** Apenas 10 itens cobertos pelos marts atuais
  (`GASTO_EDU_PIB`, `LITERACY_15M`). A Fase D (PISA + IDEB) ampliaria
  este conjunto e elevaria o poder do teste in-scope.
- **Baseline n=1.** O baseline foi executado uma única vez por item;
  o pareamento ideal usaria também n=3 do baseline.
- **Cliff's delta sobre binário** reduz a métrica a uma comparação de
  proporções; reportado por completude, não como evidência principal.
