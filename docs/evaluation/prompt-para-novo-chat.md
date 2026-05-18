# Briefing para nova sessão — Implementação da avaliação empírica do EduQuery

> Cole o conteúdo deste arquivo (ou cite o caminho dele) ao iniciar
> uma nova sessão de chat que vá implementar o plano de avaliação.
> O conteúdo abaixo é o **mínimo necessário** para outro agente
> retomar o trabalho sem o contexto da conversa em que foi gerado.

---

## Quem é você (a nova sessão)

Você é um agente de programação trabalhando no repositório
`C:\Users\thars\analise_educacation_chatbot`. O dono do projeto é o
autor do sistema **EduQuery**, um assistente multi-agente sobre
Data Lakehouse para consultas comparadas em educação básica. O
sistema está sendo descrito em um artigo SBIE 2026 / Trilha TPIE.

## O que precisa ser feito

Implementar o plano descrito em
[`docs/evaluation/plano-avaliacao-empirica.md`](./plano-avaliacao-empirica.md).

O resultado final é um número (**TIA — Taxa de Interceptação de
Alucinações**) que substituirá o placeholder `[X%]` no resumo do
artigo. Esse número precisa vir de **medição empírica real**.

## Regras inegociáveis (NÃO violar)

1. **Nunca inventar números.** Toda métrica reportada vem de execução
   real. Se a medida não foi feita, manter `[X%]` placeholder.
2. **Anonimização do artigo.** Você pode tocar livremente no repo
   de código (`analise_educacation_chatbot`). Mas o repo do artigo
   (`C:\Users\thars\OneDrive\Documentos\ARTIGO SBIE\artigo\`) tem
   regra dura: NUNCA escrever "Tharsys", "IFS", "Instituto Federal
   de Sergipe", nome de orientador, e-mail pessoal ou link real do
   GitHub. Link de repo só via `anonymous.4open.science`.
3. **Commits atômicos.** Cada fase resulta em commit isolado com
   prefixo `feat:`, `docs:` ou `chore:`.
4. **Perguntar antes de qualquer ação destrutiva** (apagar arquivo,
   sobrescrever sem backup, force-push).
5. **Golden datasets versionados em YAML.** Nada de hardcoded em
   código Python.
6. **Hooks de git ativos.** Nunca usar `--no-verify` ou bypass de
   assinatura sem permissão explícita.

## Estado atual (verificado em 2026-05-18)

- Repositório `analise_educacation_chatbot`: sistema implementado,
  ADRs 0001-0008 em `docs/adrs/`, testes em `data_pipeline/tests/`,
  `agents/tests/`, `api/tests/` (~70 arquivos).
- 137/137 testes dbt verdes sobre 5 marts Gold consolidando 7 fontes
  oficiais (PISA, IBGE, OCDE, UNESCO, IPEA, Eurostat, Banco Mundial).
- Sistema é **LLM-agnóstico via LiteLLM**. Configuração em
  `.env.example` (linhas 107–166). 6 provedores suportados:
  Anthropic (default), OpenAI, Gemini, Groq, OpenRouter, Ollama.
- Fact Checker determinístico documentado em ADR 0007.
- Retriever auto-populate documentado em ADR 0006.
- `agents/evaluation/` **não existe** — esta é a sua tarefa.

## Sequência de execução autorizada

### Fase 1 (AUTORIZADA): Estrutura + golden seeds

1. Criar árvore `agents/evaluation/` conforme Seção 7.1 do plano:

   ```
   agents/evaluation/
   ├── __init__.py
   ├── golden/{factuais,comparativas,adversarial}.yaml
   ├── golden/per_agent/*.yaml
   ├── golden/README.md
   ├── metrics/*.py
   ├── runners/*.py    (stubs com TODO)
   ├── reports/*.py
   └── conftest.py
   ```

2. Escrever **80 itens mínimos** nos YAMLs:
   - 30 factuais (`queries_factuais.yaml`)
   - 20 comparativos (`queries_comparativas.yaml`)
   - 30 adversariais (3+ de cada uma das 9 categorias — ver Seção 6
     do plano para a lista)

3. Implementar funções de **métrica** em `metrics/*.py` —
   puras, sem dependência de LLM. Cobrir com unit tests em
   `agents/tests/evaluation/`. Pelo menos:
   - `numeric_accuracy.py` (com `NumericResult` dataclass)
   - `doi_validity.py` (regex + opcional `doi.org` HEAD)
   - `source_coverage.py` (recall sobre `sources_required`)
   - `hallucination_classifier.py`
   - `guardrails_efficacy.py` (com `compute_tia()`)

4. Criar **stubs** em `runners/*.py` com `raise NotImplementedError`
   e comentários TODO claros. NÃO implementar lógica de invocação da
   CrewAI nesta fase.

5. Adicionar **fixture pytest** em `conftest.py` que carrega os
   YAMLs e devolve dicts.

6. Adicionar target `evaluate` ao **Makefile** (criar se não houver):

   ```makefile
   .PHONY: evaluate
   evaluate:
       python -m agents.evaluation.runners.run_baseline ...
       python -m agents.evaluation.runners.run_eduquery ...
       python -m agents.evaluation.runners.run_red_team ...
       python -m agents.evaluation.reports.generate_paper_table ...
   ```

7. Commit atômico:
   `feat(evaluation): adiciona estrutura e golden seeds`

### Fase 2 (PRECISA DE AUTORIZAÇÃO ADICIONAL): Runners reais

**NÃO INICIE** sem o autor confirmar que a Fase 1 está revisada e
aprovada.

Quando autorizado:

1. Investigar `agents/src/flows/` para descobrir como invocar o
   pipeline. Verificar:
   - Como o Fact Checker é acoplado (ADR 0007) — para a Fase 2
     precisamos invocar o flow **sem** o Fact Checker (baseline) e
     **com** (EduQuery completo).
   - Como o Retriever auto-populate é desativado (ADR 0006).
2. Implementar `run_baseline.py` chamando o pipeline sem guardrails.
3. Implementar `run_eduquery.py` chamando o pipeline completo.
4. Implementar `run_red_team.py` (pode usar `run_eduquery.py` mas
   focando em `adversarial.yaml`).
5. Rodar 1 vez cada para validar saída JSON.
6. Iterar nos golden se houver itens problemáticos (consultar o
   autor antes de mudar gabaritos).
7. Commit:
   `feat(evaluation): runners implementados`

### Fase 3 (PRECISA DE AUTORIZAÇÃO ADICIONAL): Execução oficial e integração no artigo

**NÃO INICIE** sem o autor confirmar a Fase 2 e dar OK para rodar a
bateria "oficial".

1. Implementar `generate_paper_table.py`.
2. Rodar a bateria oficial (80+ itens, idealmente `n=3` runs por item
   para média/std).
3. Gerar `paper_table.md`.
4. Mostrar ao autor antes de tocar no `main.tex` do artigo.
5. Substituir `[X\%]` no resumo + abstract de `main.tex`. Use o valor
   formatado com 1 casa decimal (ex.: `87.3`). Mantenha
   `\%` no LaTeX.
6. Recompilar `main.tex` e revalidar `pdfinfo` (Title/Author/etc.
   ainda vazios).
7. Commits separados em cada repo.

## Primeira mensagem sugerida ao autor

Quando você (nova sessão) começar, diga:

> "Li o plano em `docs/evaluation/plano-avaliacao-empirica.md` e o
> briefing em `docs/evaluation/prompt-para-novo-chat.md`. Vou
> iniciar a **Fase 1** (autorizada): criar a árvore
> `agents/evaluation/`, escrever ~80 itens YAML, implementar
> métricas puras e stubs de runners. Não tocarei em código de flow
> nem rodarei nada além de unit tests das métricas. Posso prosseguir?"

E aguardar autorização explícita do autor.

## Métricas-chave a calcular

| Métrica | Como medir | Onde entra |
|---------|-----------|------------|
| **TIA** | `bloqueadas_eduquery / alucinacoes_baseline` | resumo (`[X\%]`) |
| Acurácia numérica | erro_relativo ≤ 5% | Tabela §4 |
| Recall DOIs reais | DOIs_corretos / DOIs_esperados | Tabela §4 |
| Falsos positivos | bloqueios_indevidos / total_corretos | Tabela §4 |
| Latência | wall-clock por consulta (P50, P95) | Tabela §4 |

## Limites de prazo

- 2026-05-18 — registro JEMS (resumo + título) — **feito** (placeholder
  `[X\%]` ainda presente no resumo, mas título e estrutura prontos)
- 2026-05-20 — upload do PDF final — implementação precisa estar
  pronta com TIA real até essa data
- 2026-07-08 — notificação de aceite

## Em caso de bloqueio

Se algum passo do plano não for executável (ex.: o flow não permite
desativar guardrails facilmente), **reporte ao autor e proponha
alternativa antes de improvisar**.

## Recursos no repo

- Plano completo:
  [`docs/evaluation/plano-avaliacao-empirica.md`](./plano-avaliacao-empirica.md)
- ADRs do sistema: `docs/adrs/000{1..8}-*.md`
- Configuração LLM: `.env.example` (linhas 107–166)
- Testes existentes: `agents/tests/`, `data_pipeline/tests/`, `api/tests/`
- Artigo: `C:\Users\thars\OneDrive\Documentos\ARTIGO SBIE\artigo\`
  (NÃO escrever no `main.tex` sem autorização específica do autor)

---

**Fim do briefing.**
