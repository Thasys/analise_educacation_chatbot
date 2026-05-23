# Protocolo de avaliação externa (validade de conteúdo)

> **Fase B** do prompt `prompt-analises-pos-resultados.md` /
> **Ação #1** da Tabela 2.1 do PDF do orientador (avaliador externo dos
> gabaritos). Objetivo: mitigar o **viés de confirmação** de o golden
> ter sido criado pelos próprios autores, obtendo concordância
> inter-avaliador (Cohen's kappa) sobre a correção dos gabaritos.

## 1. Contexto para o avaliador

O sistema **EduQuery** responde perguntas sobre educação básica
comparada (Brasil × países desenvolvidos) consultando um *data
lakehouse* de fontes oficiais (OECD, UNESCO, World Bank, IPEA, INEP).
Para medir a qualidade do sistema, construímos um conjunto de
**perguntas de referência** com **gabaritos** (a resposta correta
verificada contra a fonte primária). Como esses gabaritos foram
escritos pela própria equipe, precisamos de um **avaliador externo**
para confirmar que:

1. as perguntas são **representativas** do domínio;
2. os **gabaritos estão corretos** contra a fonte citada;
3. para perguntas adversariais (que tentam enganar o sistema), o
   **comportamento esperado** (recusar, bloquear, declarar fora de
   escopo) faz sentido.

Não é necessário conhecimento de programação — apenas familiaridade com
indicadores educacionais e capacidade de checar uma fonte oficial.

## 2. O que avaliar

A planilha (`external_evaluator_form.csv` / `.xlsx`, gerada por
`agents/evaluation/reports/external_evaluator_form.py`) contém **10
itens**: 5 *in-scope* (factuais/comparativos cobertos pelos marts) e 5
adversariais cobrindo categorias distintas (`adversarial_numbers`,
`prompt_injection`, `doi_fishing`, `cross_source_contradiction`,
`empty_rag`).

Para cada item, preencha as colunas:

| Coluna | O que responder |
|---|---|
| `representativa_1a5` | A pergunta é razoável/representativa para avaliar um sistema de educação comparada? (1 = irrelevante, 5 = altamente representativa) |
| `gabarito_correto_sim_nao_incerto` | O `gabarito_esperado` está correto contra a `fonte_primaria`? (`sim` / `nao` / `incerto`) |
| `comportamento_faz_sentido_1a5` | **Só adversariais.** O comportamento esperado (recusar/bloquear/declarar fora de escopo) faz sentido? (1-5) |
| `comentario` | Texto livre: justificativa, valor correto sugerido, ressalvas |

## 3. Procedimento

1. O autor gera a planilha:
   ```bash
   cd agents && uv run python -m evaluation.reports.external_evaluator_form \
       --golden evaluation/golden \
       --output evaluation/output/external_evaluator_form.csv
   ```
2. O autor envia o `.xlsx` (ou `.csv`) para o avaliador externo
   (colega da pós, professor, ou especialista em educação).
   **Esta etapa é manual — o agente não a executa.**
3. O avaliador preenche e devolve a planilha.
4. O autor importa o retorno e calcula o kappa:
   ```bash
   cd agents && uv run python -m evaluation.shared.import_external_eval \
       --input <retorno_do_avaliador.csv> \
       --output evaluation/output/external_eval_results.json
   ```

## 4. Critério de aceite

- **Cohen's kappa ≥ 0,75** (concordância substancial) entre avaliador
  externo e autor sobre a correção binária dos gabaritos.
- Se **kappa < 0,75**: reunião com o avaliador para reconciliar os
  itens discordantes. **Não maquilar** — se o avaliador tiver razão,
  corrigir o gabarito no YAML e re-rodar a bateria.
- Itens marcados `incerto` são excluídos do kappa e listados à parte
  para discussão.

**Nota metodológica sobre o kappa degenerado:** por construção, o autor
afirma que todos os gabaritos estão corretos (sem variância). Nesse
caso o Cohen's kappa fica **indefinido** (`kappa_degenerate: true` no
JSON de saída) e o relatório usa a **concordância observada** mais a
revisão das divergências. Para um kappa não-degenerado, o autor deve
fornecer suas próprias respostas binárias via `--author <csv>` (útil se
o autor reavaliar criticamente os gabaritos).

## 5. Tabela 8 do paper (a preencher após o retorno)

Após o retorno, registrar em `paper_table.md` / `main.tex`:

> A validade de conteúdo foi avaliada por um especialista externo sobre
> uma amostra de 10 itens (5 in-scope + 5 adversariais). A concordância
> com os gabaritos do autor foi de [X]% (Cohen's κ = [Y]), e a
> representatividade média das perguntas foi [Z]/5.

## 6. Status atual

- [x] Protocolo definido.
- [x] Planilha gerada (`external_evaluator_form.csv` + `.xlsx`).
- [x] Script de importação + kappa implementado e testado.
- [ ] **(manual, bloqueante)** Avaliador externo preenche e devolve.
- [ ] Kappa calculado sobre dados reais.
- [ ] Tabela 8 inserida no paper.

> **Bloqueio honesto:** as três últimas caixas dependem de um recurso
> humano externo e não podem ser concluídas autonomamente pelo agente.
> Toda a infraestrutura (planilha + pipeline de kappa) está pronta.
