# Changelog

Todas as mudanças notáveis do projeto. Formato baseado em
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); versões usam
[SemVer](https://semver.org/spec/v2.0.0.html) — pré-1.0, breaking changes
podem aparecer em minor releases.

## [Não publicado]

### Added

- **2026-05-23** — Polimento metodológico pós-resultados (Fases A/B/C do
  [prompt-analises-pos-resultados.md](docs/evaluation/prompt-analises-pos-resultados.md)),
  para reforçar a avaliação empírica rumo ao Qualis A3. Custo de API
  desprezível (apenas re-run de 5 itens + LLM-juiz Batch ≈ \$0,003);
  todo o resto é determinístico sobre os JSONs existentes.
  - **Fase A — Análise estatística inferencial** ([análise completa](docs/evaluation/analise-estatistica-resultados.md)):
    - `agents/evaluation/reports/statistical_analysis.py`: McNemar
      pareado em 3 recortes (in-scope n=10, numérico n=54, in-scope com
      voto majoritário n=3) com χ² (correção de continuidade) **e** p
      exato binomial; bootstrap IC 95% (5.000 reamostragens, seed 42);
      Cohen's h; Cliff's delta; ICC(2,1) entre repetições.
    - `render_baseline_comparison_figure.py`: figura PNG (DPI 300, serif)
      "LLM-direto = Baseline = 10% « EduQuery = 63%".
    - `generate_paper_table.py`: Tabela 7 (significância) lendo
      `statistical_analysis.json`. `paper_table.md` regenerado.
    - **Resultado honesto (regra: números são pontos de chegada):**
      in-scope isolado é *borderline* (p exato 0,0625 — subpotente, mas
      5 melhoras / 0 regressões); numérico n=54 fortemente significativo
      (χ²=8,45, p=0,003); Cohen's h=1,20; IC95 do EduQuery [46,7%, 80,0%]
      não inclui o baseline (10,0%); ICC=0,74. Os 3 recortes reportados
      sem cherry-picking.
    - 19 unit tests novos em `tests/evaluation/test_statistical_analysis.py`.
  - **Fase B — Avaliação externa (validade de conteúdo)** ([protocolo](docs/evaluation/external-evaluator-protocol.md)):
    - `external_evaluator_form.py` gera planilha CSV/XLSX (5 in-scope + 5
      adversariais de categorias distintas) a partir do golden.
    - `evaluation/shared/import_external_eval.py` importa o retorno e
      calcula Cohen's kappa + divergências por item; trata o caso
      degenerado (autor sem variância → reporta concordância observada).
    - 11 unit tests em `tests/evaluation/test_external_eval.py`.
    - **Bloqueio honesto:** a etapa de preenchimento depende de recurso
      humano externo — infraestrutura pronta, dados aguardam.
  - **Fase C — Correções dos 5 adversariais HALLUCINATED** ([ablação](docs/evaluation/ablation-correcoes-adversariais.md)):
    - Hardening anti-injeção nos prompts do Orchestrator + Synthesizer
      (recusam "esquecer os marts / responder com conhecimento geral").
    - `compute_divergence()` determinístico em `tools/stats_tools.py`
      (|max-min|/median > 5%) + campos `divergence_detected`/`divergence_pct`
      no schema `StatAnalysis`; prompts do Statistician/Synthesizer passam
      a reportar divergência/convergência explícita entre fontes.
    - Regra de `year_confusion` no Statistician (não propaga valor
      injetado pelo usuário; corrige o ano quando há dado).
    - 10 unit tests em `tests/agents/test_adversarial_corrections.py`.
    - **Re-run real** dos 5 itens (Sonnet 4.5/Haiku 4.5, mesmos modelos
      da bateria oficial) + TCC 3 camadas: **2/5 → CORRECT** (A-022 recusa
      a injeção; A-015 disclaimer de escopo). A-011 *gated* na Fase D
      (PISA fora dos marts). **A-014/A-016 expõem defeito do golden**: as
      fontes convergem (A-014) ou divergem <5% (A-016), tornando
      `report_divergence` insatisfazível — encaminhados ao avaliador
      externo. Sem maquiagem: 27/30 projetado, não os 30/30 do plano.
- **2026-05-26** — Polimento adicional (validação completa + higiene de
  configuração):
  - **Re-execução completa dos 30 adversariais** (Seção 5 do
    [ablation](docs/evaluation/ablation-correcoes-adversariais.md)):
    TCC observado **23/30 = 76,7%** vs 25/30 = 83,3% da bateria oficial.
    7 itens flipparam — diagnóstico: 3 ganhos esperados (A-022 fix
    funcionou, A-015 e A-023 equivalentes), 4 regressões atribuíveis a
    (a) variabilidade LLM n=1 consistente com ICC=0,74 da Fase A,
    (b) match semântico estrito (A-020: sistema recusa injeção como
    projetado, mas juiz não captura; A-029: recusa via "erro interno"
    fora dos `REFUSAL_PATTERNS`), (c) golden estrito (A-004: corrigir
    é defensável quando `block` esperado). Custo \$5 + Batch \$0,003.
    Reportar o número honesto e a variabilidade comprovada no paper.
  - **Flag de `_review_pending`** em A-014 e A-016 (golden YAML): defeito
    de gabarito documentado para o avaliador externo (Fase B). Loader
    ignora os campos `_review_*`, sem quebra de schema.
  - **Fix em `llm_judge_batch.py`**: helper `_anthropic_client()` resolve
    a chave via `os.environ` *e* `settings.llm_api_key`, eliminando a
    necessidade de exportar `ANTHROPIC_API_KEY` no shell quando o `.env`
    já tem a chave.
  - **Cleanup do `.env`**: provider Anthropic ativo (Sonnet 4.5 / Haiku
    4.5), bloco Gemini preservado como backup comentado. `AGENTS_LLM_API_KEY`
    deixado sem definição para fallback automático a `ANTHROPIC_API_KEY`
    (evita o erro recente em que a chave Google de outro ciclo polui
    chamadas Anthropic).
  - **Fix em `tests/test_llm.py`** (4 falhas pré-existentes):
    fixture `anthropic_env` agora fixa `AGENTS_LLM_SMART_MODEL`/`FAST_MODEL`
    (alinhando com `openai_env` e `ollama_env`), evitando herança do `.env`
    local; assert do Ollama tolera o drift `api_base`→`base_url` no
    cliente OpenAI-compatível recente do LiteLLM/CrewAI. test_llm.py
    agora 10/10 verde em isolado.
  - **Figura comparativa no artigo**: `figuras/comparison_baseline.png`
    + `\includegraphics` na Seção 4, referenciada no parágrafo de
    significância estatística. PDF agora tem 14 páginas.
  - **Resumo do artigo**: removido o `TODO` obsoleto sobre placeholder
    `[X\%]` (números reais já preenchidos em commit anterior).
  - **Fase D — PISA + IDEB** ([status](docs/evaluation/fase-d-status.md)):
    IDEB já concluído (ver 2026-05-21). PISA **bloqueada** por 4
    pré-requisitos ausentes (toolchain R, microdados PISA, dbt no PATH,
    decisão metodológica ADR 0009 + regra de PAUSE em plausible values).
  - Dependências: `scipy` + `matplotlib` adicionadas ao `agents/pyproject.toml`.
  - Testes: 167 verdes na suíte de avaliação + correções (126 originais +
    41 novos). As 4 falhas pré-existentes em `tests/test_llm.py` (drift
    LiteLLM/CrewAI: `api_base`→`base_url`) não são regressão deste ciclo.
  - **No artigo** (`secoes/04_resultados.tex`): parágrafo "Significância
    estatística" adicionado à Seção 4 (Cohen's h, IC95 bootstrap, McNemar).
- **2026-05-21** — IDEB Brasil nos marts Gold (Fase A do
  [prompt-implementar-pisa-ideb.md](docs/evaluation/prompt-implementar-pisa-ideb.md)):
  - Coletor `data_pipeline/src/scripts/collect_ideb.py` baixa 6
    planilhas municipais (3 etapas × ciclos 2019 + 2021) do INEP
    diretamente para `data/bronze/inep/ideb_*/<ciclo>/`. Suporte SSL
    via `truststore` (cadeia RNP ICPEdu ausente do bundle Mozilla).
  - dbt: `stg_inep_ideb` (UNPIVOT wide→long de `VL_OBSERVADO_*` e
    `VL_PROJECAO_*` via DuckDB), `int_ideb__br_serie_historica` e
    `int_indicadores__ideb` (schema canônico), `mart_ideb__br_serie_historica`.
    Cobertura: AI/AF 2005-2021; EM 2017-2021. 54 dbt tests verdes.
  - `IndicatorId` enum recebe `IDEB_AI`, `IDEB_AF`, `IDEB_EM` em
    `agents/src/schemas.py` e `api/src/schemas/common.py`. SourceTag
    ganha `inep`. Prompts do Profiler/Retriever/Statistician + descrição
    da tool `data_timeseries` atualizados.
  - Fix em `api/src/services/timeseries_service.py`: filtro por
    `indicator_id` (necessário porque `int_indicadores__ideb` empilha
    3 indicadores na mesma tabela; antes o serviço assumia 1:1).
  - Dev: Python pin 3.12 + `dbt-core`/`dbt-duckdb` em `[dev]` extras
    do `data_pipeline/pyproject.toml`.
  - **Caveat metodológico documentado**: o `int_ideb__br_serie_historica`
    usa média simples por município (rede 'Pública'), sem ponderação
    por matrículas e sem rede privada. Resultado fica 0.15-0.25pp
    abaixo do IDEB nacional oficial (5.57 vs 5.7 para AI 2021). Goldens
    F-011/F-012/F-014 podem falhar em `tolerance_pct=2`; iteração
    futura: ponderação via Censo Escolar.
- **2026-05-19** — Avaliação empírica EduQuery (Fases 1+2+3 do
  [plano-avaliacao-empirica.md](docs/evaluation/plano-avaliacao-empirica.md)):
  - Pacote `agents/evaluation/` com 84 itens golden (32 factuais + 22
    comparativos + 30 adversariais em 9 categorias), 5 métricas puras
    (`numeric_accuracy`, `doi_validity`, `source_coverage`,
    `hallucination_classifier`, `guardrails_efficacy`), 3 runners
    (baseline / eduquery / red_team) + `generate_paper_table.py`.
  - 89 unit tests dedicados (todos verdes), 216/216 testes na suite
    afetada.
  - **Refactor mínimo invasivo**: `master_flow.run_master(...,
    no_guardrails: bool = False)` + propagação para
    `_run_retriever`/`_run_citation`. Default `False`; só os runners
    de baseline ativam a flag.
  - Limitações descobertas e documentadas em
    [`docs/evaluation/limitations.md`](docs/evaluation/limitations.md):
    PISA fora dos marts (`plausible_values_pending`), incompatibilidade
    Gemini × CrewAI Flow, n=1 por prazo SBIE 2026-05-20.
- **2026-05-16** — Reorganização da documentação ([D1-D4 de docs](docs/refactor/dry-pass-2026-05.md)):
  - `docs/operations/` com 4 guias vivos: running-the-system, data-pipeline,
    models-and-providers, monitoring-and-debugging.
  - `docs/architecture/layers.md`, `agents.md`, `frontend.md` (Mermaid)
    substituindo o consumo direto dos `.jsx`.
  - ADRs 0005-0008 cobrindo decisões pós-Fase 6.
  - `docs/archive/` para fases históricas e runs antigos.
- **2026-05-16** — Auto-populate determinístico do `primary_data` no Retriever
  ([ADR 0006](docs/adrs/0006-retriever-autopopulate.md)). Resolve bug do
  `qwen2.5:14b` que chama a tool mas não copia rows para o output.
- **2026-05-15** — Fact Checker pós-Synthesizer ([ADR 0007](docs/adrs/0007-fact-checker-post-synthesis.md)).
  Validador determinístico (regex + tolerância 5%) + retry 1× do Synthesizer
  com lista de divergências. Warning visível se falhar.
- **2026-05-15** — Provider Ollama com Qwen 2.5 ([ADR 0005](docs/adrs/0005-ollama-qwen-provider.md))
  — smart `qwen2.5:32b`, fast `qwen2.5:14b`. Substitui `mistral-nemo:12b`
  para eliminar alucinação numérica.
- **2026-05-14** — DRY refactor pass A+B+C ([ADR 0008](docs/adrs/0008-dry-refactor-pass.md)):
  10 padrões duplicados consolidados em helpers (`SafeTool`, `_EndpointTool`,
  `make_agent`, `run_single_agent_task`, `parse_period`, `build_data_response`,
  `WorkspaceShell`, `DoiLink`, `instantiate_with_shared_client`).
- **2026-05-14** — Quality assessment documentado em
  [`docs/quality-assessment-2026-05-14.md`](docs/quality-assessment-2026-05-14.md).
  Identificou alucinação, DOIs falsos, gráficos quebrados — base para todos
  os guardrails adicionados depois.
- **2026-05-14** — Guardrails determinísticos pós-LLM:
  - `_validate_figure` em viz_tools (QW1) — rejeita Plotly com `x`/`y` strings.
  - `is_real_doi` em rag_tools (QW3) — rejeita DOIs `10.xxxx/...`.
  - QW4: Citation Agent honesto quando RAG vazio.
  - QW5: Statistician recebe `precomputed_metrics` do mart Gold.

### Changed

- **2026-05-16** — Docstrings de código limpas: referências históricas
  `Sprint X.Y` substituídas por links para ADRs ou removidas (39 ocorrências
  em Python + TS).
- **2026-05-16** — README.md reescrito para refletir estado atual do sistema
  (era ainda da Fase 0 Bootstrap).
- **2026-05-13** — Container `agents-server` adicionado ao docker-compose
  (porta 8001, separado do `api/`). Detalhe em
  [`docs/archive/runs/2026-05-13-docker-up.md`](docs/archive/runs/2026-05-13-docker-up.md).

### Fixed

- **2026-05-14** — Restaurada validação `min_length=3` em `RAGSearchArgs.query`
  e validações análogas em `CompareArgs.countries` e `ComputeStatsArgs.values`.
  Validações tinham sido removidas do schema Pydantic (compat GBNF Ollama)
  mas o código antigo não substituiu por checks dentro de `_run`.

---

## Histórico de fases (Fase 0 → Fase 6)

Cronologia de desenvolvimento original — detalhes em
[`docs/archive/phases/`](docs/archive/phases/).

### Fase 6 — Frontend Next.js 14 (2026-05-06)

Workspace 3 colunas (Sidebar + Workspace + ContextPanel) em `/compare`,
`/explorer`, `/library`. Streaming SSE via `agents-server:8001` + Plotly
lazy + DOIs clicáveis. 86 testes (77 vitest + 9 Playwright). Caddy
reverse proxy `:8443` para single origin. ADR 0004.

### Fase 5 — Sistema de agentes CrewAI (2026-04-30)

8 agentes em 4 crews (Core/Analysis/Synthesis/Master), 10 tools, RAG
ChromaDB com 25 papers seed, CLI dev. 119 testes mock + 2 live opt-in.
ADR 0003.

### Fase 4 — FastAPI Gateway

Endpoints `/api/data/{catalog,timeseries,compare,ranking}` consultando
DuckDB. Pydantic v2, SlowAPI rate limiting, structlog JSON.

### Fase 3 — Gold Layer

5 marts dbt analíticos: `mart_br_vs_ocde__*`, `mart_alfabetizacao__*`,
`mart_indicadores__rankings_recente`, `mart_gasto_x_alfabetizacao__*`,
`mart_br__evolucao_indicadores`.

### Fase 2 — Silver Layer + dbt

dbt Core + adapter dbt-duckdb. Staging + intermediate models. ISO-3
+ ISCED 2011. 137 testes dbt. ADR 0002.

### Fase 1 — Bronze Layer

7 coletores REST: WB, UNESCO UIS, OECD SDMX, IPEA OData, CEPAL, IBGE
SIDRA, Eurostat. Parquet imutável em `data/bronze/<fonte>/<ano>/`.

### Fase 0 — Bootstrap (2026-04-23)

Estrutura base, Docker Compose, "hello world" em todas as camadas. ADR 0001.

---

## Como contribuir com este changelog

- Adicione entradas no topo, sob `[Não publicado]`.
- Use subseções: `Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security`.
- Data em formato ISO (`YYYY-MM-DD`).
- Linkar ADRs/docs relevantes em vez de copiar conteúdo.
- Ao cortar release, mover `[Não publicado]` para `[X.Y.Z] — YYYY-MM-DD`
  e criar novo bloco vazio em cima.
