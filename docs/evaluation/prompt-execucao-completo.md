# Prompt completo — Execução da bateria de testes do EduQuery

> **Uso:** copie integralmente este arquivo como **primeira mensagem**
> em uma nova sessão Claude Code (ou cole o caminho dele e peça ao
> agente para ler). Foi desenhado para ser autossuficiente: outro
> agente, sem ver a conversa anterior, deve conseguir começar imediatamente.

---

## 1. Quem é você

Você é um agente de programação Claude Code operando localmente no
Windows, com acesso aos seguintes diretórios:

- **Repositório de código (alvo desta tarefa):**
  `C:\Users\thars\analise_educacation_chatbot`
- **Repositório do artigo (NÃO TOCAR sem autorização explícita):**
  `C:\Users\thars\OneDrive\Documentos\ARTIGO SBIE\artigo\`

Trabalhe primariamente dentro do repo de código. O artigo só será
tocado na Fase 3, e somente após autorização explícita do autor.

---

## 2. Contexto do projeto

O autor (anonimizado neste arquivo) está submetendo um artigo ao
**SBIE 2026 / Trilha TPIE** (Qualis A3, revisão duplamente anônima)
descrevendo o sistema **EduQuery**:

- Assistente multi-agente sobre **Data Lakehouse Medallion** para
  consultas comparativas em educação básica (Brasil × países
  desenvolvidos).
- **8 agentes CrewAI** especializados + **Fact Checker determinístico**
  pós-síntese.
- Camada de **guardrails determinísticos** (verificação matemática +
  validação de DOIs reais + checagem de figuras).
- **7 fontes oficiais**: PISA, IBGE, OCDE, UNESCO, IPEA, Eurostat,
  Banco Mundial.
- **5 marts Gold** (alfabetizacao, cross, gasto, indicadores, pais)
  consolidados; **137/137 testes dbt verdes**.
- **LLM-agnóstico via LiteLLM** (6 provedores: Anthropic default,
  OpenAI, Gemini, Groq, OpenRouter, Ollama).

### Por que esta avaliação importa

O resumo do artigo contém um placeholder **`[X\%]`** que precisa ser
substituído por um número empírico real: a **Taxa de Interceptação de
Alucinações (TIA)** medida pelos guardrails sobre um pipeline RAG sem
guardrails (baseline). Sem essa medição, o artigo fica com placeholder
e não pode ser submetido com integridade.

### Prazo

- **Hoje:** 2026-05-19
- **Deadline upload PDF JEMS:** 2026-05-20 (≤ 24 horas a partir de
  agora). Execução precisa ser eficiente.

---

## 3. Documentos de referência (leia nesta ordem)

| # | Arquivo | Tamanho | Propósito |
|---|---------|---------|-----------|
| 1 | `docs/evaluation/README.md` | ~41 linhas | Índice da pasta de avaliação |
| 2 | `docs/evaluation/prompt-para-novo-chat.md` | ~203 linhas | Briefing enxuto anterior (referência cruzada) |
| 3 | `docs/evaluation/plano-avaliacao-empirica.md` | ~740 linhas | **Documento mestre.** Auto-suficiente. Cobre: estado atual, princípios, plano por camada (5), golden datasets, métricas (TIA), red teaming (9 categorias), pipeline de automação, cronograma, integração com artigo, limitações, seeds YAML e esqueletos Python |
| 4 | `docs/adrs/0006-retriever-autopopulate.md` | ~4.5 KB | Como o Retriever auto-popula contexto — relevante para desativar no baseline |
| 5 | `docs/adrs/0007-fact-checker-post-synthesis.md` | ~5.3 KB | Como o Fact Checker é acoplado — relevante para baseline vs. completo |
| 6 | `CLAUDE.md` | ~5.5 KB | Convenções gerais do repo |
| 7 | `.env.example` linhas 107–166 | — | Configuração LLM multi-provider |

**Comece lendo o README, depois o plano-avaliacao-empirica.md
integralmente.** Os outros são consulta sob demanda.

---

## 4. Estrutura atual do repositório (verificada 2026-05-19)

```
analise_educacation_chatbot/
├── .env.example                         # Config LLM (linhas 107-166)
├── CLAUDE.md                            # Convenções do projeto
├── README.md
├── CHANGELOG.md
├── docker-compose.yml
├── pyproject.toml (em cada subpacote)
│
├── agents/                              # CrewAI multi-agente
│   ├── src/
│   │   ├── agents/                      # 8 agentes especializados
│   │   │   ├── citation.py
│   │   │   ├── comparativist.py
│   │   │   ├── orchestrator.py
│   │   │   ├── profiler.py
│   │   │   ├── retriever.py
│   │   │   ├── statistician.py
│   │   │   ├── synthesizer.py
│   │   │   └── visualizer.py
│   │   ├── crews/                       # Composições de crews
│   │   │   ├── analysis_crew.py
│   │   │   ├── core_crew.py
│   │   │   ├── master_flow.py           # ★ ponto de entrada do pipeline
│   │   │   └── synthesis_crew.py
│   │   ├── tools/
│   │   │   ├── data_tools.py
│   │   │   ├── rag_tools.py
│   │   │   ├── stats_tools.py
│   │   │   └── viz_tools.py
│   │   ├── rag/
│   │   ├── prompts/
│   │   ├── server/
│   │   ├── llm.py                       # Wrapper LiteLLM
│   │   ├── schemas.py
│   │   └── config.py
│   └── tests/                           # pytest existente
│       ├── agents/
│       ├── e2e/
│       ├── rag/
│       ├── server/
│       └── tools/
│
├── api/                                 # FastAPI
│   └── src/, tests/
│
├── data_pipeline/                       # Coletores + dbt orquestração
│   ├── src/
│   │   ├── collectors/                  # 7 fontes oficiais
│   │   ├── flows/
│   │   ├── transforms/
│   │   └── utils/
│   └── tests/
│
├── dbt_project/
│   └── models/
│       ├── staging/
│       ├── intermediate/
│       └── marts/                       # 5 marts Gold
│           ├── alfabetizacao/
│           ├── cross/
│           ├── gasto/
│           ├── indicadores/
│           └── pais/
│
├── frontend/                            # Next.js 14 (não foco da avaliação)
│
└── docs/
    ├── adrs/                            # 0001..0008
    ├── architecture/
    ├── conventions.md
    ├── methodology.md
    ├── operations/
    └── evaluation/                      # ★ AQUI estão os planos
        ├── README.md
        ├── plano-avaliacao-empirica.md
        ├── prompt-para-novo-chat.md
        └── prompt-execucao-completo.md  # (este arquivo)
```

### O que NÃO existe ainda (você vai criar)

```
agents/evaluation/
├── __init__.py
├── golden/
│   ├── queries_factuais.yaml         # ≥ 30 itens
│   ├── queries_comparativas.yaml     # ≥ 20 itens
│   ├── adversarial.yaml              # ≥ 30 itens (3+ por categoria × 9)
│   ├── per_agent/                    # YAMLs por agente especializado
│   │   └── *.yaml
│   └── README.md
├── metrics/
│   ├── numeric_accuracy.py           # NumericResult dataclass
│   ├── doi_validity.py               # regex + HEAD opcional
│   ├── source_coverage.py            # recall sobre sources_required
│   ├── hallucination_classifier.py
│   └── guardrails_efficacy.py        # compute_tia()
├── runners/
│   ├── run_baseline.py               # stub na Fase 1
│   ├── run_eduquery.py               # stub na Fase 1
│   └── run_red_team.py               # stub na Fase 1
├── reports/
│   └── generate_paper_table.py       # stub na Fase 1
└── conftest.py                       # fixtures pytest

agents/tests/evaluation/              # unit tests das métricas
└── test_*.py
```

---

## 5. Regras inegociáveis (NÃO violar)

1. **Nunca invente números.** TIA, acurácia, recall, latência — toda
   métrica reportada vem de execução real. Se a medida não foi feita,
   mantenha `[X\%]` placeholder.

2. **Anonimização do artigo.** Você pode editar livremente o repo de
   código. Mas o repo do artigo (`...\ARTIGO SBIE\artigo\`) tem regra
   dura: NUNCA escrever "Tharsys", "IFS", "Instituto Federal de
   Sergipe", nome de orientador, e-mail pessoal ou link real do
   GitHub. Link de repositório só via `anonymous.4open.science`.

3. **Commits atômicos** com prefixos convencionais (`feat:`, `docs:`,
   `chore:`, `test:`, `fix:`). Uma fase = um commit, no mínimo.

4. **Pergunte antes de qualquer ação destrutiva** (apagar arquivo,
   sobrescrever sem backup, force-push, `--no-verify`).

5. **Golden datasets em YAML versionado.** Nada de dados hardcoded em
   código Python.

6. **Hooks de git ativos.** Não use `--no-verify`, `--no-gpg-sign`,
   `-c commit.gpgsign=false` sem autorização explícita. Se um hook
   falhar, investigue e corrija a raiz.

7. **NÃO toque em `main.tex` do artigo na Fase 1 ou 2.** Esse arquivo
   só será editado na Fase 3, com autorização e diff revisado.

---

## 6. Sequência de execução faseada

### Fase 1 — Estrutura + golden seeds + métricas puras [AUTORIZADA]

**Inicie sem aguardar autorização adicional.** Esta fase não roda o
pipeline real, só prepara terreno.

Entregáveis:

1. Árvore `agents/evaluation/` conforme Seção 4 deste arquivo.
2. ≥ 80 itens YAML nos golden:
   - 30 factuais em `queries_factuais.yaml`
   - 20 comparativos em `queries_comparativas.yaml`
   - 30 adversariais em `adversarial.yaml` (3+ por categoria; 9
     categorias listadas na Seção 6 do plano mestre)
3. Métricas puras em `metrics/*.py`, **sem dependência de LLM**.
4. Unit tests em `agents/tests/evaluation/test_*.py` cobrindo cada
   métrica (esperado: ≥ 1 caso feliz + ≥ 1 caso adversarial por
   métrica).
5. Stubs em `runners/*.py` com `raise NotImplementedError` e TODO
   claros. **Não implemente invocação de CrewAI ainda.**
6. `conftest.py` com fixture pytest que carrega os YAMLs.
7. Target `evaluate` no Makefile (criar se não existir).

Comando de verificação ao final da Fase 1:

```powershell
cd C:\Users\thars\analise_educacation_chatbot
# devem passar todos
python -m pytest agents/tests/evaluation/ -v
# devem listar os YAMLs corretamente
python -c "import yaml, glob; [print(f, len(yaml.safe_load(open(f, encoding='utf-8')))) for f in glob.glob('agents/evaluation/golden/*.yaml')]"
```

Commit:
`feat(evaluation): adiciona estrutura, golden seeds e metricas puras`

**Pare e reporte ao autor.** Aguarde "OK Fase 2" antes de prosseguir.

---

### Fase 2 — Runners reais [PRECISA DE AUTORIZAÇÃO]

NÃO INICIE sem aprovação explícita.

Quando autorizado:

1. Inspecione `agents/src/crews/master_flow.py` para entender como o
   pipeline é montado.
2. Identifique como **desacoplar o Fact Checker** (baseline) e como
   **desativar o Retriever auto-populate** (consulte ADR 0006 e
   0007). Se não houver flag, proponha refactor mínimo invasivo ao
   autor antes de fazer.
3. Implemente:
   - `run_baseline.py` — pipeline sem guardrails, sobre todos os
     golden, salva JSON estruturado em `agents/evaluation/output/baseline/`
   - `run_eduquery.py` — pipeline completo com Fact Checker
   - `run_red_team.py` — foca em `adversarial.yaml`
4. Execute 1 dry-run em cada com `--limit 5` para sanity check.
5. Itere nos golden se houver itens mal formados (consulte o autor
   antes de alterar gabaritos).

Commit:
`feat(evaluation): runners de baseline, eduquery e red team`

**Pare e reporte ao autor.** Aguarde "OK Fase 3".

---

### Fase 3 — Execução oficial + integração no artigo [PRECISA DE AUTORIZAÇÃO]

NÃO INICIE sem aprovação explícita.

Quando autorizado:

1. Implemente `reports/generate_paper_table.py`.
2. Rode a bateria oficial: idealmente `n=3` execuções por item para
   média/desvio. Se o tempo apertar, `n=1` é aceitável com declaração
   de limitação.
3. Gere `agents/evaluation/output/paper_table.md`.
4. **Mostre o resultado ao autor antes de tocar em `main.tex`.**
5. Após autorização: edite `main.tex` no repo do artigo:
   - Substitua `[X\%]` no `resumo` e no `abstract` pelo valor real
     formatado com 1 casa decimal (ex.: `87.3\%`).
   - Mantenha o `\%` LaTeX.
   - Não toque em mais nada.
6. Recompile com `latexmk -pdf main.tex` ou
   `pdflatex -interaction=nonstopmode main.tex`.
7. Revalide anonimização:
   ```powershell
   pdfinfo main.pdf
   ```
   Title/Author/Subject/Keywords/Creator/Producer devem estar vazios.
8. Commits **separados** em cada repo (`feat(evaluation): bateria oficial`
   no repo de código; `feat(artigo): substitui placeholder TIA pelo valor real`
   no repo do artigo).

---

## 7. Métricas-chave a calcular

| Métrica | Fórmula | Onde entra no artigo |
|---------|---------|----------------------|
| **TIA** | `bloqueadas_eduquery / alucinacoes_baseline` | resumo + abstract (substitui `[X\%]`) |
| Acurácia numérica | `erro_relativo ≤ 5%` por item | Tabela §4 |
| Recall DOIs reais | `DOIs_corretos / DOIs_esperados` | Tabela §4 |
| Falsos positivos | `bloqueios_indevidos / total_corretos` | Tabela §4 |
| Latência | wall-clock por consulta (P50, P95) | Tabela §4 |

Especificações formais completas: ver Seção 5 do plano mestre
(`plano-avaliacao-empirica.md`).

---

## 8. Categorias de red teaming (use na composição de `adversarial.yaml`)

3+ itens por categoria, total ≥ 30:

1. Contradição com fonte oficial (resposta esperada: bloqueio)
2. DOI inventado (resposta esperada: bloqueio com motivo "DOI inválido")
3. Número fora do intervalo plausível
4. Consulta sobre país/ano fora do escopo coberto pelos marts
5. Ambiguidade política / opinião disfarçada de fato
6. Prompt injection (instrução para ignorar guardrails)
7. Comparação inválida (unidades/anos incompatíveis)
8. Citação sem fonte verificável
9. Pergunta cuja resposta correta é "não sei" (avaliar honestidade)

Detalhes: Seção 6 do plano mestre.

---

## 9. Primeira mensagem sugerida ao autor

Quando a nova sessão começar e o autor responder ao prompt, diga
exatamente:

> "Li `docs/evaluation/prompt-execucao-completo.md`, o
> `plano-avaliacao-empirica.md` e os ADRs 0006/0007. Verifiquei o
> estado do repo com `git status` e `python -m pytest --collect-only`.
>
> Vou iniciar a **Fase 1** (autorizada): criar `agents/evaluation/`,
> escrever 80+ itens YAML, implementar 5 funções de métrica com unit
> tests, e deixar stubs nos runners.
>
> Não tocarei em `agents/src/crews/master_flow.py`, não invocarei
> nenhum LLM, e não editarei o repo do artigo nesta fase. Tempo
> estimado: 1.5–2h. Posso prosseguir?"

E aguarde "sim" / "ok" / equivalente antes de criar o primeiro arquivo.

---

## 10. Critérios de aceite por fase

### Fase 1 — pronta quando:

- [ ] `agents/evaluation/` existe com toda a árvore descrita.
- [ ] ≥ 80 itens YAML, validados por `yaml.safe_load`.
- [ ] `pytest agents/tests/evaluation/` passa 100%.
- [ ] Runners têm stub com `NotImplementedError` e TODO.
- [ ] Makefile target `evaluate` existe (pode chamar stubs).
- [ ] Commit único, mensagem `feat(evaluation): ...`.
- [ ] Anonimização do repo do artigo intacta (sem alterações lá).

### Fase 2 — pronta quando:

- [ ] Os 3 runners executam dry-run com `--limit 5` sem erro.
- [ ] Saída JSON validada por schema explícito.
- [ ] Baseline vs. EduQuery realmente diferem (Fact Checker desativado
      no baseline).
- [ ] Commit `feat(evaluation): runners ...`.

### Fase 3 — pronta quando:

- [ ] `paper_table.md` existe com valores reais (não placeholder).
- [ ] `main.tex` no repo do artigo com `[X\%]` substituído.
- [ ] `pdfinfo main.pdf` confirma metadados vazios.
- [ ] Dois commits separados (um por repo).
- [ ] Autor revisou e aprovou diff antes do commit no repo do artigo.

---

## 11. Em caso de bloqueio

Se qualquer passo do plano não for executável (ex.: o flow não permite
desativar guardrails sem refactor invasivo), **PARE e reporte ao
autor** com:

1. O que tentou.
2. Por que não funcionou (mensagem de erro / observação técnica).
3. 2–3 alternativas com prós/contras.

Não improvise mudanças estruturais sem confirmação.

---

## 12. Recursos rápidos

- Inspeção inicial:
  ```powershell
  cd C:\Users\thars\analise_educacation_chatbot
  git status
  git log --oneline -10
  python -m pytest --collect-only 2>&1 | Select-Object -First 50
  ```

- ADRs relevantes:
  - `docs/adrs/0006-retriever-autopopulate.md`
  - `docs/adrs/0007-fact-checker-post-synthesis.md`
  - `docs/adrs/0008-dry-refactor-pass.md`

- Configuração LLM: `.env.example` linhas 107–166.

- Testes existentes (referência de estilo):
  - `agents/tests/agents/`
  - `agents/tests/tools/`
  - `data_pipeline/tests/`

---

**Fim do prompt. A nova sessão deve agora cumprimentar o autor com a
mensagem da Seção 9 e aguardar autorização.**
