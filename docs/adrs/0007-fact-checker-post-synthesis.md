# ADR 0007 — Fact Checker determinístico pós-Synthesizer (MP4)

- **Status:** aceito
- **Data:** 2026-05-15
- **Fase:** pós-Fase 6 (operação)

## Contexto

A avaliação de qualidade de **2026-05-14** ([quality-assessment](../quality-assessment-2026-05-14.md))
identificou um problema dominante: o Synthesizer ([`agents/src/agents/synthesizer.py`](../../agents/src/agents/synthesizer.py))
**inventa números** ao escrever o markdown final, mesmo quando os valores
canônicos estão presentes em `retrieved.primary_data` / `stats.key_metrics`.

Caso documentado: pergunta "Brasil × Finlândia × México 2020" — verdade
no Gold é `BRA=5,77%`, `FIN=6,68%`, `MEX=4,50%`. O modelo `mistral-nemo:12b`
escreveu `BRA=4,7%`, `FIN=6,9%`, `MEX=5,3%` (3/3 errados, com direcional
invertida).

MP4 do plano de remediação propunha um *fact-checker agent leve* (Haiku
ou qwen 7B) que recebe `markdown` + `primary_data` e devolve
`is_consistent: bool` + `divergences: list[str]`, bloqueando a resposta.

## Decisão

Implementar fact-check **determinístico em Python puro** (não como agente
LLM), em duas camadas:

### 1. Verificação por regex + tolerância numérica

[`crews/_helpers.py::check_numeric_consistency`](../../agents/src/crews/_helpers.py):
- Extrai números do markdown (regex `(?<![\w])(\d{1,4}(?:[.,]\d{1,3})?)(?![\w])`).
- Filtra anos (`1900-2099 sem decimal`).
- Compara cada um contra `primary_data[*].value` + `primary_meta.*`
  (`zscore_in_oecd`, `percentile_in_oecd`, `gap_to_oecd_mean`, `trend_slope`,
  `comparison_stats.*`).
- Tolerância padrão: 5%. Aceita variantes `*100` / `/100` para `%` vs
  proporção.
- Retorna `(is_consistent, list_of_unmatched)`. `is_consistent=False`
  se `unmatched / total > 20%`.

### 2. Retry do Synthesizer com divergências explícitas

[`crews/synthesis_crew.py::regenerate_final_after_fact_check`](../../agents/src/crews/synthesis_crew.py):

Quando `is_consistent=False`, dispara **1 chamada extra** apenas do
Synthesizer com:
- Lista de números proibidos (divergentes).
- Lista de números canônicos (vindos de `primary_data`).
- Markdown anterior como referência (mas instrução para não copiar valores).

Após o retry, re-roda o fact-check. Se ainda inconsistente, **não bloqueia**
— adiciona warning visível no `final.warnings`:

> *"Fact-check: N valores no markdown nao correspondem ao dado real (tolerancia 5%). Trate como ilustrativo, nao final."*

### Integração no master flow

[`master_flow.run_master`](../../agents/src/crews/master_flow.py) — passo 4
(após Synthesis, antes de acoplar citations). Emite eventos SSE:
- `agent_started/done "Fact Checker"` (`is_consistent`, `divergences`).
- Opcionalmente: `agent_started/done "Synthesizer (retry)"`.

## Por que determinístico e não outro agente LLM

| Critério | LLM agent | Determinístico (escolhido) |
|---|---|---|
| Latência | +~50-180s (qwen 14b/32b) | ~ms |
| Custo Ollama local | irrelevante mas tempo total dobra | 0 |
| Confiabilidade | LLM pode ele mesmo alucinar | regex + comparação numérica |
| Cobertura semântica | Pega "Brasil acima da média OCDE quando é abaixo" | NÃO pega — só compara números |
| Custo de implementar | ~5-8h (novo agente, prompt, schema) | ~2h |

Trade-off aceito: o determinístico pega **números errados** mas não
**direcionais errados** (ex.: dizer "abaixo" quando é "acima"). Para
direcional precisaria de LLM — fica como melhoria futura caso o fluxo
atual mostre divergências semânticas frequentes.

## Alternativas consideradas

1. **Bloquear totalmente respostas inconsistentes**: descartado — sistema
   acadêmico precisa entregar algo. Warning explícito é mais útil que erro
   500 ou markdown vazio.

2. **JSON Schema strict via Ollama `format=<schema>`**: forçaria o LLM a
   produzir valores diretamente dos campos do payload, sem prosa intermediária.
   Promissor mas requer reescrita do prompt e schema. Fica como **LP3** do
   quality plan.

3. **Self-consistency (3 amostras + voto)**: triplica o tempo. Para Ollama
   local ~60 min/run é inviável. Fica como **LP2**.

## Consequências

**Positivas:**
- Fact-check custa ~0 quando o Synthesizer acerta (caminho rápido).
- Retry só dispara quando necessário. Em testes com `qwen2.5:32b`,
  `is_consistent=True` na primeira tentativa.
- Warning honesto quando o retry também falha — usuário vê transparentemente
  que a resposta tem números suspeitos.

**Negativas:**
- Não pega direcionais errados ("acima" vs "abaixo") nem ordenações trocadas.
- Tolerância de 5% pode mascarar erros sutis (4.7 vs 4.50 = 4.4%, passa).
  Aperar para 2% reduz false negatives mas também rejeita arredondamentos
  legítimos. Trade-off aceito.

**Débitos:**
- Implementar MP4 completo (agente LLM) caso o determinístico mostre
  insuficiente em produção.
- LP3 (Ollama `format=<schema>`) deve tornar o fact-checker desnecessário
  por construção.

## Testes

12 testes unitários em [`tests/agents/test_fact_check.py`](../../agents/tests/agents/test_fact_check.py):

- Passes within tolerance
- Rounding aceito
- Anos filtrados (não considerados divergentes)
- Falha quando >20% divergentes
- Usa `primary_meta.zscore_in_oecd`, `percentile_in_oecd`, `comparison_stats`
- Aceita variants `*100` / `/100`
