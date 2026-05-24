# Fase D — Status (PISA + IDEB nos marts)

> Avaliação de viabilidade da Fase D do prompt
> `prompt-analises-pos-resultados.md`, que delega ao prompt próprio
> `prompt-implementar-pisa-ideb.md`. Verificado em 2026-05-24.

## Resumo

| Sub-fase | Estado | Nota |
|---|---|---|
| **IDEB (atalho rápido)** | ✅ **CONCLUÍDA** | Já implementada no commit `cef8013` (sessão anterior). |
| **PISA (esforço metodológico)** | ⛔ **BLOQUEADA** | Pré-requisitos de ambiente + dados + decisão metodológica ausentes nesta sessão. |

## 1. IDEB — concluída (commit `cef8013`)

A Fase A do `prompt-implementar-pisa-ideb.md` ("atalho rápido", IDEB
agregado sem plausible values) já está implementada e integrada:

- **Coleta:** `scripts/collect_ideb.py` baixa 6 planilhas municipais
  (3 etapas × ciclos 2019/2021) do INEP para `data/bronze/`.
- **dbt:** `stg_inep_ideb` (UNPIVOT ~250k linhas) →
  `int_ideb__br_serie_historica` → `int_indicadores__ideb` (schema
  canônico) → `mart_ideb__br_serie_historica` (21 linhas: AI/AF
  2005-2021, EM 2017-2021). **54 dbt tests verdes.**
- **Agentes:** enum `IndicatorId` recebeu `IDEB_AI/AF/EM` (schemas
  agents + api), `SourceTag` recebeu `inep`, prompts do
  Profiler/Retriever/Statistician atualizados. Confirmado na
  re-execução da Fase C: o sistema lista "IDEB_AI, IDEB_AF, IDEB_EM"
  entre os indicadores canônicos disponíveis.
- **Golden:** 4 itens (F-011..F-014, C-009) movidos de `out_of_scope`
  para `in_scope`.

Nada a fazer aqui — apenas registrar no balanço.

## 2. PISA — bloqueada (4 pré-requisitos ausentes)

A Fase B do `prompt-implementar-pisa-ideb.md` (PISA com Plausible
Values) **não pode ser executada autonomamente nesta sessão**. Não é
falta de autorização — são bloqueios materiais e uma regra
metodológica do próprio projeto:

1. **Toolchain R ausente.** `Rscript` não está instalado
   (`which Rscript` → vazio). As regras inegociáveis #1 do prompt PISA e
   o `methodology.md` Princípio 4 exigem `EdSurvey::edsurveyTable()` ou
   `intsvy::pisa.mean.pv()` — **proíbem explicitamente** tirar média
   simples dos 10 plausible values em Python (viesa erros-padrão).
   Implementar PV sem R seria violar a regra #1.

2. **Microdados PISA ausentes.** Não há `data/bronze/iea/pisa/`. O
   pipeline exige download dos microdados PISA 2018 + 2022 da OECD
   (vários GB), parametrizado via `Rscript pisa_extraction.R <anos>`.
   `r_scripts/pisa_extraction.R` ainda é placeholder (~115 linhas).

3. **dbt fora do PATH neste ambiente.** `dbt` não é invocável
   diretamente (`program not found`); os modelos novos
   (`stg_iea_pisa`, `int_pisa_long`, `mart_pisa__br_vs_ocde`) não podem
   ser construídos/testados aqui.

4. **Decisão metodológica pendente (PAUSE obrigatório).** A regra #10 do
   `CLAUDE.md` e a regra #6 do prompt PISA exigem escrever a ADR
   `0009-pisa-plausible-values.md` **antes** de tocar no Statistician,
   documentando: (a) R vs Python; (b) `EdSurvey` vs `intsvy`; (c) subset
   de domínios (math/read/sci); (d) janela temporal. Essas são escolhas
   do autor/orientador, não do agente.

### O que destrava a Fase D / PISA

Para uma sessão futura conseguir executar:

1. Instalar R + `renv` (`r_scripts/_packages.R` já define o ambiente).
2. Baixar microdados PISA 2018 + 2022 (OECD) para `data/bronze/iea/pisa/`.
3. Garantir `dbt` invocável (venv do `dbt_project`).
4. Autor/orientador validar a ADR 0009 (escolhas de PV).

Esforço estimado pelo prompt: **~4 semanas concentradas**. Impacto
projetado: ~22 itens `out_of_scope` viram `in_scope`, TIA in-scope
subindo de 55,6% para ~65-75%.

## 3. Recomendação

Fase D não é necessária para a submissão SBIE (notificação 2026-07-08):
as Fases A/B/C deste ciclo já tornam a avaliação defensável em Qualis
A3. A Fase D / PISA é o trabalho de maior impacto para o **camera-ready**
(~2026-08-15), mas requer as decisões e recursos acima. Recomenda-se
abrir uma sessão dedicada com R + dados PISA disponíveis e a ADR 0009
aprovada.
