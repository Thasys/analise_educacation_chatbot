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

**Atualizado em:** 2026-05-19 (final da Fase 3).
