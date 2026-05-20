# Limitacoes conhecidas da avaliacao empirica

> Complementa o [plano-avaliacao-empirica.md](./plano-avaliacao-empirica.md)
> Secao 10. Documenta limitacoes **descobertas durante a execucao da
> Fase 2/3** (nao previstas no plano original).

## 1. PISA/TIMSS/PIRLS fora dos marts atuais

### Estado

Os marts Gold v1 cobrem apenas dois indicadores canonicos:

- `GASTO_EDU_PIB`   gasto publico em educacao (% do PIB)
- `LITERACY_15M`    taxa de alfabetizacao 15+

### Por que PISA esta fora

Documentado em
[`docs/methodology.md`](../methodology.md#1.-plausible-values-pisa-timss-pirls):

> Microdados de avaliacoes internacionais usam **10 plausible values**
> em vez de uma nota unica. Calcular media, gap e ranking exige
> agregar os 10 PVs (em geral por media simples das 10 estimativas)
> **+ aplicar pesos BRR ou Jackknife** para os erros-padrao.
>
> O Statistician Agent retorna `method="plausible_values_pending"`
> quando detecta pergunta sobre PISA/TIMSS/PIRLS — a pipeline ainda
> nao implementa essa metodologia.

Em outras palavras, PISA nao foi adicionado por integridade
metodologica, nao por esquecimento. Adicionar nota PISA simples (sem
PVs) ao mart violaria o Principio 4 do projeto: "Plausible Values
corretos — PISA/TIMSS/PIRLS exigem BRR/Jackknife".

### Impacto na TIA

O conjunto golden Fase 1 contem 30+ itens sobre PISA. Em ambos os
modos avaliados (baseline RAG e EduQuery completo), o sistema
**honestamente recusa** responder esses itens com mensagens do tipo:

> O indicador PISA nao esta disponivel na camada Silver do sistema.
> Apenas GASTO_EDU_PIB e LITERACY_15M sao suportados.

No nosso classifier:

- baseline:  `actual_value=None` (sem numero) -> `HALLUCINATED`.
- eduquery: idem -> `HALLUCINATED`. Nem o Fact Checker nem o filtro
  de DOI interceptam: simplesmente nao ha o que interceptar.

Resultado: **itens PISA entram no denominador da TIA mas nunca no
numerador** -> TIA bruta artificialmente baixa. O sistema e penalizado
exatamente por ser honesto sobre o escopo.

### Mitigacao adotada

`evaluation/reports/generate_paper_table.py` classifica cada item em
3 escopos:

- `in_scope`     itens cobertos pelos marts atuais (gasto/analfabetismo).
- `out_of_scope` PISA/TIMSS/PIRLS/IDEB/SAEB/matricula/conclusao etc.
- `adversarial`  conjunto de red teaming.

A tabela do artigo reporta **TIA in-scope** alem da TIA bruta.
**O resumo + abstract usam a TIA in-scope** (recompensa honestidade).
A TIA bruta e reportada na tabela como contexto, com nota.

### Trabalho futuro

- Implementar Plausible Values + BRR/Jackknife (escopo significativo;
  ver `r_scripts/` que ja tem placeholders).
- Apos implementacao, rodar a bateria novamente com os mesmos golden
  para comparar.

---

## 2. Provider Gemini incompativel com CrewAI Flow

### Sintoma

Configurando `AGENTS_LLM_PROVIDER=gemini` + `AGENTS_LLM_SMART_MODEL=
gemini-2.5-flash-lite` (default do `.env` em 2026-05-19) e rodando
qualquer dos runners, o pipeline falha com:

```
ERROR:crewai.flow.flow:Error executing listener call_llm_native_tools:
    Invalid response from LLM call - None or empty.
RuntimeError: no running event loop
```

Causa raiz (provavel): CrewAI 1.14 + `google-genai` SDK nativo usam
loops async incompativeis quando invocados de contexto sincrono
(nosso laco de bateria). O CrewAI tenta `asyncio.get_running_loop()`
e nao acha; quando recorre a `asyncio.run`, o SDK ja consumiu o
contexto e retorna `None`.

### Mitigacao adotada

Rodar os runners com **Anthropic provider** (Claude Sonnet 4.5 +
Haiku 4.5). Variaveis injetadas inline na invocacao, sem alterar o
`.env`:

```bash
AGENTS_LLM_PROVIDER=anthropic \
AGENTS_LLM_SMART_MODEL=claude-sonnet-4-5 \
AGENTS_LLM_FAST_MODEL=claude-haiku-4-5 \
AGENTS_LLM_API_KEY="$ANTHROPIC_API_KEY" \
python -m evaluation.runners.run_baseline ...
```

O run oficial da Fase 3 usou Anthropic.

### Trabalho futuro

- Investigar se versoes mais recentes de `crewai` ou `google-genai`
  corrigem a incompatibilidade. Provavel: usar `crewai>=1.15` quando
  disponivel.
- Alternativa de curto prazo: rodar o pipeline dentro do container
  `edu_agents_server`, que funciona com Gemini (provavelmente porque
  o uvicorn no container ja mantem um event loop ativo).
- Implementar testes de regressao para integracao CrewAI Flow x cada
  provider antes de propagar mudanca de `.env`.

---

## 3. n=1 por item no run oficial

### Estado

O plano mestre recomenda `n>=3` execucoes por item para reportar
media + desvio padrao. O run oficial da Fase 3 usou `n=1` devido ao
prazo SBIE 2026-05-20 (deadline de upload do PDF JEMS).

### Implicacao

Os numeros reportados sao **estimativas pontuais**. LLMs nao sao
deterministicos mesmo com temperatura=0 (variacao por hardware /
versao da API). A TIA reportada deve ser lida como "ordem de
grandeza", nao como medida com 3 casas decimais de precisao.

### Trabalho futuro

- Rodar a bateria com `n=3` apos a submissao SBIE (revisao de
  notificacao 2026-07-08).
- Reportar media +/- desvio padrao em revisao final do artigo.

---

## 4. Golden datasets DRAFT (nao verificados linha-a-linha)

### Estado

Todos os 84 itens do golden tem `_verified: false`. Os valores foram
escritos com base em conhecimento publico sobre PISA 2022, IDEB 2021
etc., mas **nao houve cross-check item-a-item contra a fonte
primaria** antes do run oficial.

### Implicacao

- Possivel viés do autor: itens "faceis" para o sistema podem ter
  sido escolhidos inconscientemente.
- Possiveis erros nos `expected_value`: se um item tinha valor errado
  no golden, qualquer resposta do sistema seria comparada contra esse
  errado.

### Mitigacao adotada

- Os itens `out_of_scope` (PISA etc.) nao alimentam a TIA in-scope,
  entao erros neles nao corrompem a metrica principal.
- Items `in_scope` (GASTO/LITERACY) sao 6-8: viavel cross-checar em
  revisao de notificacao.

### Trabalho futuro

- Para a revisao final do artigo, cross-checar manualmente cada item
  `in_scope` contra a fonte primaria. Marcar `_verified: true` quando
  validado, remover quando nao-verificavel.

---

## 5. Analise do resultado 55,6% (TIA estendida in-scope)

### O que aconteceu, item-a-item

Dos 10 itens in-scope, 9 foram alucinados pelo baseline RAG. O EduQuery
interceptou 5 deles (viraram CORRECT) — **TIA = 5/9 = 55,6%**.

| id    | Indicador / ano | Baseline | EduQuery | Auto-populate disponivel? |
|-------|----------------|----------|----------|---------------------------|
| F-015 | analfabetismo BR 2022 | hallucinated | **correct** | sim — `mart_alfabetizacao__latam_2020s` cobre |
| F-016 | analfabetismo BR 2019 | hallucinated | hallucinated | nao — ano fora do recorte do mart |
| F-017 | gasto BR 2021 | hallucinated | **correct** | sim — `mart_br_vs_ocde__gasto_educacao_timeseries` |
| F-018 | gasto OCDE 2021 | hallucinated | **correct** | sim |
| F-032 | gasto/aluno USD PPP BR 2021 | hallucinated | hallucinated | nao — USD PPP nao e indicador canonico |
| C-001 | comparacao gasto BR vs OCDE 2021 | hallucinated | **correct** | sim |
| C-005 | comparacao gasto/aluno BR/FIN/KOR | hallucinated | hallucinated | nao — USD PPP fora |
| C-010 | comparacao gasto BR/USA/MEX 2020 | hallucinated | **correct** | sim |
| C-011 | analfabetismo 2019 vs 2022 | hallucinated | hallucinated | nao — 2019 fora do recorte |
| C-017 | gasto BR vs FIN 2020 | correct | correct | (ja era correct) |

### Por que esse valor especifico

A TIA in-scope mede, na pratica, a **fracao das alucinacoes do baseline
cuja pergunta cabe no recorte exato dos marts atuais**. Quando a pergunta
cai dentro, o auto-populate determinístico do Retriever ([ADR 0006](../adrs/0006-retriever-autopopulate.md))
injeta o valor canonico do mart no contexto do Synthesizer — e o sistema
acerta. Fora do recorte (ano ausente, indicador derivado como USD PPP),
o auto-populate falha e o Synthesizer alucina.

**A TIA reflete a fronteira de cobertura do lakehouse, nao a qualidade
dos guardrails em abstrato.**

### Aceitabilidade

- **6x melhora sobre baseline** (10% -> 60% acuracia in-scope): defensavel
  metodologicamente.
- **44% das alucinacoes passam**: sistema **nao e fonte primaria**;
  usuario academico deve checar fontes citadas.
- **Banda da literatura RAG em educacao**: 40-70% acuracia agregada.
  EduQuery (60%) cai no meio dessa banda — esperado para sistema novo
  com escopo limitado.
- **Risco de leitura ingenua**: revisor que ler "55,6%" sem o contexto
  pode achar baixo. A subsecao 3.4 (Avaliacao) do artigo precisa deixar
  explicito que a metrica e restrita aos indicadores cobertos.

### Caminhos para aumentar a TIA (ordenados por ROI)

| # | Intervencao | Impacto estimado | Custo |
|---|---|---|---|
| 1 | **Implementar PISA/TIMSS/PIRLS com Plausible Values + BRR** ([`r_scripts/`](../../r_scripts/) ja tem placeholders) | +30-40 itens viram in-scope; TIA potencialmente ~70%+ | Alto (2-4 semanas) |
| 2 | **Expandir cobertura temporal dos marts atuais** (gasto pre-2010, analfabetismo 2019) | F-016, C-011 viram interceptaveis | Baixo (1-2 dias) |
| 3 | **Adicionar `mart_gasto_per_aluno` (USD PPP)** | F-032, C-005 viram interceptaveis | Medio (3-5 dias) |
| 4 | **Fact Checker LLM-based** (MP4 do quality plan, [ADR 0007 Debito Tecnico](../adrs/0007-fact-checker-post-synthesis.md)) | Pega direcionais errados; +10-15% in-scope | Medio (1 semana) |
| 5 | **JSON Schema strict via Ollama `format=<schema>`** (LP3) | Synthesizer nao pode mais "prosa intermediaria" inventar numeros | Medio |
| 6 | **Popular ChromaDB com referencias reais** (RAG atualmente vazio -> 0 DOIs reais recuperados) | DOI recall sobe; melhora citacoes | Medio |
| 7 | **Self-consistency n=3 com voto majoritario** (LP2) | Reduz variancia LLM; melhora ~5% | Alto (3x custo de tokens) |

**Maior alavanca: #1 + #2.** Se 30 itens PISA viram in-scope e 50%
deles forem interceptados, TIA in-scope sobe para ~65-75%.

### Implicacoes

**Para o paper (Secao 5 — Discussao):**

- O sistema **nao e fonte primaria**; e assistente de exploracao.
- ~44% das alucinacoes in-scope passam -> para usos criticos
  (publicacao, politica publica), revisao humana e necessaria.
- A camada de guardrails deterministicos e **necessaria mas nao
  suficiente** — confirmando o argumento do paper de que LLM puro RAG
  e insuficiente sem verificacao.

**Para arquitetura (proximas iteracoes):**

- O ROI dos guardrails e real (6x acuracia), validando o investimento
  no DRY refactor + ADRs 0006/0007.
- A maior alavanca nao e melhorar guardrails — e **ampliar a cobertura
  do lakehouse** (#1 e #2 da tabela acima).
- Lei de Conway aplicada: a TIA reflete a fronteira de "o que esta
  modelado nos marts".

**Para revisao SBIE:**

- O par "TIA estendida in-scope 55,6% + acuracia 10%->60%" e mais
  defensavel que apresentar so um numero.
- Revisores TPIE devem aceitar se o paper for explicito sobre escopo +
  reportar limitacao corretamente (este documento).

---

## 6. Calibracao da tolerancia numerica por tipo de indicador

### Estado original

O `tolerance_pct: 5` aplicado no esqueleto do plano mestre era um
**default generico** — adequado para um sanity check inicial, mas
folgado demais para indicadores oficiais como PISA e IDEB, cujos
valores oficiais sao reportados com precisao alta:

| Referencia (PISA Math) | Valor |
|---|---:|
| Margem de erro padrao (SE) do PISA Brasil 2022 | ~2,7 pts |
| Diferenca estatisticamente significativa entre paises | ~10 pts |
| ~1 ano de aprendizagem (convencao OECD) | ~25-30 pts |
| **Tolerancia 5% sobre 379** | **~19 pts (~70% de 1 ano)** |

A tolerancia de 5% sobre a nota PISA equivale a quase 1 ano de
aprendizagem — uma diferenca metodologicamente **relevante** em
estudos de educacao comparada. Em itens com `tolerance_pct: 5`, o
sistema seria classificado como CORRECT respondendo qualquer valor
entre `[360; 398]` para um gabarito de `379`.

### Calibracao adotada (2026-05-20)

`evaluation/shared/recalibrate_tolerances.py` foi executado para
apertar a tolerancia de **21 itens PISA/IDEB**:

| Tipo de indicador | Tolerancia anterior | Tolerancia atual | Justificativa |
|---|:-:|:-:|---|
| Notas PISA (valores oficiais OECD) | 5% | **2%** | ~8 pts; proximo do limiar de significancia entre paises (~10 pts). |
| IDEB (indice INEP, 1 casa decimal) | 5% | **2%** | ~0,12 pts; precisao alta do indicador. |
| Medias OCDE PISA | 3% | (mantido) | Ja estrito; valor agregado tem variabilidade menor. |
| Singapura PISA (#1 mundial) | 3% | (mantido) | Ja estrito. |
| Analfabetismo IBGE PNAD | 5% | (mantido) | Justificavel; erro amostral PNAD ~0,3 pp. |
| Gasto % do PIB | 10% | (mantido) | Justificavel; fontes divergem (INEP/SIOPE vs WB vs OCDE). |
| Conclusao EM (OCDE EAG) | 5-10% | (mantido) | OK; variabilidade metodologica entre paises. |
| Escolaridade media | 10% | (mantido) | OK; definicao varia entre fontes. |
| Aluno-professor ratio | 10% | (mantido) | OK; depende de definicao de "professor ativo". |
| Populacao escolar (estimativas) | 5% | (mantido) | OK; arredondamento. |
| Docentes (Censo Escolar) | 10% | (mantido) | OK; categorias variam. |
| Gasto/aluno USD PPP | 15% | (mantido) | OK; conversao PPP volatil. |
| #paises PISA (contagem) | 2% | (mantido) | Ja estrito. |

**21 itens recalibrados:** F-001, F-002, F-003, F-007, F-008, F-009,
F-010, F-011, F-012, F-013, F-014, F-026, F-027, C-002, C-003, C-004,
C-008, C-009, C-012, C-016, C-020.

### Impacto na TIA reportada (55,6%)

**Nenhum.** Razao: os 21 itens recalibrados sao todos PISA/IDEB que
caem em `out_of_scope` (PISA/TIMSS/PIRLS estao com
`plausible_values_pending` — Secao 1 deste documento; IDEB nao tem
mart ainda). Nestes itens:

- **Baseline**: sistema responde "indicador nao disponivel" -> 
  `actual_value=None` -> `HALLUCINATED`.
- **EduQuery**: mesma resposta -> mesma classificacao.

Como `actual_value=None` em ambos os modos, **a tolerancia (qualquer
que seja) nao altera a classificacao** — sem numero proposto, nao ha
o que tolerar. A TIA in-scope de 55,6% e a TIA bruta de 23,0%
permanecem identicas.

### Por que o ajuste e relevante mesmo sem mudar a TIA atual

A calibracao e **trabalho preventivo** para o proximo ciclo
(Secao 8.2 da [paper_table.md](./paper_table.md), caminho ROI #1).
Quando PISA for implementado com Plausible Values + BRR/Jackknife
(`r_scripts/` ja tem placeholders), os 21 itens entrarao em
`in_scope` e o sistema proporia valores numericos concretos —
a tolerancia entao **importara**:

- Com 5%: respostas "Brasil PISA Math 2022 = 397" seriam aceitas
  (gabarito 379, gap de 18 pts = quase 1 ano de aprendizagem).
  Inflaria a TIA artificialmente.
- Com 2%: respostas seriam aceitas em `[371,4; 386,6]` — apenas
  proximo do valor real. Honesto.

A calibracao protege a integridade da metrica **antes** que ela seja
medida com PISA real, evitando a tentacao retroativa de "ajustar a
tolerancia para o numero ficar melhor".

### Implicacao no documento principal

Esta calibracao **nao altera o numero 55,6% reportado no resumo +
abstract do artigo SBIE 2026**. Ela e documentada aqui como
transparencia metodologica e como pre-requisito para revisao final
(notificacao 2026-07-08), quando o n>=3 e a verificacao item-a-item
contra fontes primarias serao executados.

### Trabalho futuro

- **Antes do proximo run** (com PISA implementado): rodar
  `recalibrate_tolerances.py` em modo `--strict` (todos os
  indicadores oficiais para 1-2%, indicadores com amostragem
  para 5%).
- Cross-checar cada `expected_value` contra a fonte primaria,
  marcando `_verified: true`.
- Documentar a tolerancia adotada em cada `tipo_de_indicador` numa
  tabela canonica no [`plano-avaliacao-empirica.md`](./plano-avaliacao-empirica.md).

---

**Atualizado em:** 2026-05-20 (analise pos-bateria + calibracao de tolerancias).
