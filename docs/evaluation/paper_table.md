# EduQuery — Tabela de Resultados (Secao 4 do artigo)
_Gerado a partir de 84 itens (10 in-scope, 44 out-of-scope, 30 adversariais) apos exclusao de itens com falha de infraestrutura (credit balance / overload Anthropic)._

## Limitacao de escopo

O EduQuery v1 cobre apenas `GASTO_EDU_PIB` e `LITERACY_15M`. Itens sobre PISA/TIMSS/PIRLS/IDEB sao classificados como `out_of_scope` — o sistema honestamente recusa responder (retorna `scope_disclaimer`), o que nosso classifier marca como `HALLUCINATED` tanto no baseline quanto no EduQuery (nem um nem outro bloqueia, ambos respondem). Para nao penalizar honestidade, reportamos **TIA in-scope** alem da TIA bruta. Ver `docs/methodology.md#1.-plausible-values-pisa-timss-pirls`.

## Duas definicoes de TIA

- **TIA estrita**: `|H_baseline INTERSECT BLOCKED_eduquery| / |H_baseline|`. Conta apenas bloqueios explicitos (Fact Checker emitindo warning, Pydantic schema recusando ano > 2030, etc.).
- **TIA estendida**: `|H_baseline INTERSECT (BLOCKED OR CORRECT)_eduquery| / |H_baseline|`. Recompensa tambem **correcoes silenciosas**: auto-populate do Retriever (ADR 0006) e retry do Synthesizer com lista de divergencias (ADR 0007) muitas vezes consertam alucinacoes sem bloquear — o item vira CORRECT.

Reportamos as duas. **O resumo + abstract usam a TIA estendida** (captura o efeito agregado real dos guardrails).

## Tabela 1 — TIA e metricas principais

| Recorte | n | TIA estrita | TIA estendida | FP rate | Acuracia baseline | Acuracia EduQuery |
|---|---:|---:|---:|---:|---:|---:|
| **Bruto (todos)** | 84 | 0.0% | **23.0%** | 0.0% | 10.7% | 27.4% |
| **In-scope (marts atuais)** | 10 | 0.0% | **55.6%** | 0.0% | 10.0% | 60.0% |
| Out-of-scope (PISA etc.) | 44 | 0.0% | 30.0% | 0.0% | 9.1% | 29.5% |
| Adversarial | 30 | 0.0% | 0.0% | 0.0% | 13.3% | 13.3% |

*Itens excluidos por falha de infraestrutura (credit balance / Anthropic overload): 0 no total.*


## Tabela 2 — Latencia (segundos)
| Modo | Recorte | Media | P50 | P95 |
|---|---|---:|---:|---:|
| Baseline | Bruto | 91.54 | 99.79 | 182.58 |
| EduQuery | Bruto | 120.78 | 104.98 | 194.59 |
| Baseline | In-scope | 84.98 | 59.17 | 195.5 |
| EduQuery | In-scope | 138.75 | 112.83 | 215.8 |

## Tabela 3 — Recall de fontes e DOIs (in-scope)
| Metrica | Baseline | EduQuery |
|---|---:|---:|
| Recall medio de fontes citadas | — | 1.0 |
| Recall medio de DOIs reais | — | 0.0 |

## Tabela 4 — Breakdown adversarial por categoria (EduQuery)
| Categoria | n | Bloqueados | Alucinados | Taxa de bloqueio |
|---|---:|---:|---:|---:|
| adversarial_figure | 3 | 0 | 3 | 0.0% |
| adversarial_numbers | 4 | 1 | 3 | 25.0% |
| cross_source_contradiction | 3 | 0 | 0 | 0.0% |
| doi_fishing | 3 | 0 | 3 | 0.0% |
| empty_rag | 4 | 0 | 4 | 0.0% |
| privacy_probe | 3 | 0 | 3 | 0.0% |
| prompt_injection | 4 | 0 | 4 | 0.0% |
| source_spoofing | 3 | 0 | 3 | 0.0% |
| year_confusion | 3 | 0 | 2 | 0.0% |

## Para o resumo + abstract

O placeholder `[X\%]` em `main.tex` (resumo e abstract) deve ser substituido pelo valor **TIA estendida in-scope** (recompensa tanto bloqueios quanto correcoes silenciosas, e ignora itens out_of_scope que ambos modos respondem honestamente):

> **TIA estendida in-scope = 55.6%**

Justificativa: a TIA estrita (apenas BLOCKED) subestima o efeito do EduQuery porque os guardrails frequentemente **consertam** o output (via auto-populate do Retriever ou retry do Synthesizer) em vez de bloqueia-lo — esses casos viram CORRECT em vez de BLOCKED. A TIA estendida captura ambos os modos de intercepcao.

Para contexto: TIA estendida bruta = 23.0% (inclui itens out_of_scope). TIA estrita bruta = 0.0% (apenas BLOCKED).

## Metadados
- Baseline executado em: 2026-05-19 15:16:32 (duracao: 7689.0s)
- EduQuery executado em: 2026-05-19T20:25:05.619792+00:00 (duracao: 8370.05s)
- Red team: extraido dos resultados de EduQuery (itens adversariais).
- n=1 por item (limitacao de prazo SBIE 2026-05-20). Trabalho futuro: n>=3.
- Provider LLM: Anthropic Claude (Sonnet 4.5 + Haiku 4.5).
