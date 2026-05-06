# Fase 5 — Análise de Desenvolvimento (Sistema de agentes CrewAI)

> **Análise Educacional Comparada Brasil × Internacional**
> Documento analítico sobre o desenvolvimento da **Fase 5 — Sistema de agentes CrewAI**.
> Complementa o roadmap em [`CLAUDE.md`](../../CLAUDE.md#fase-5--sistema-de-agentes-crewai-semanas-1215)
> e parte das conclusões da [`Fase 4`](./fase-4-conclusao.md).
> **Data:** 2026-04-29

---

## Sumário

1. [Contexto e ponto de partida](#1-contexto-e-ponto-de-partida)
2. [Objetivos da Fase 5](#2-objetivos-da-fase-5)
3. [Decisões arquiteturais propostas](#3-decisões-arquiteturais-propostas)
4. [Catálogo de agentes e tools](#4-catálogo-de-agentes-e-tools)
5. [RAG sobre literatura científica](#5-rag-sobre-literatura-científica)
6. [Padrões de código](#6-padrões-de-código)
7. [Estratégia de testes](#7-estratégia-de-testes)
8. [Sequência de implementação (sprints)](#8-sequência-de-implementação-sprints)
9. [Riscos e mitigações](#9-riscos-e-mitigações)
10. [Critérios de aceitação](#10-critérios-de-aceitação)

---

## 1. Contexto e ponto de partida

A Fase 4 entregou 4 endpoints REST (`catalog`, `timeseries`, `compare`,
`ranking`) sobre os 5 marts Gold em DuckDB, com 19 testes verdes via
`TestClient`. A regra crítica do `CLAUDE.md` ("agentes não escrevem SQL
livre") está implementada: o único caminho dos agentes para os dados é
via HTTP, com Pydantic v2 validando inputs e SQL parametrizado no
service.

A Fase 5 conecta **LLMs Claude** (via API Anthropic) ao gateway,
montando 8 agentes especializados (CrewAI) que roteiam três fluxos
distintos de execução conforme a complexidade da pergunta.

### Ponto de partida quantitativo

```
agents/ apenas com pyproject.toml + Dockerfile  · src/ vazio
0 agentes · 0 tools · 0 crews · 0 prompts · 0 testes
ChromaDB sem coleção criada · sem documentos indexados
ANTHROPIC_API_KEY definida no .env (placeholder no .env.example)
```

### Insumos disponíveis

- **Gateway estável** em `http://localhost:8000/api/data/*` (4 endpoints).
- **Catálogo** com 5 marts e respectivas descrições/tags.
- **2 indicadores canônicos** (`GASTO_EDU_PIB`, `LITERACY_15M`) cobrindo
  6 fontes (worldbank, unesco, oecd, eurostat, ipea, cepalstat).
- **8 groupings** analíticos (oecd, oecd_g7, latam_oecd, latam, brics,
  asia, africa_mena, europe_other).

---

## 2. Objetivos da Fase 5

### 2.1 Objetivos primários

1. **8 agentes CrewAI** funcionais com prompts versionados em arquivos
   `.txt` (Orchestrator, Profiler, Retriever, Statistician,
   Comparativist, Citation, Visualizer, Synthesizer).
2. **3 crews** orquestrando os agentes em processos sequenciais e
   hierárquicos (Core, Analysis, Synthesis).
3. **3 fluxos de execução** validados ponta a ponta:
   - Simples (~5–10s, ~5k tokens, conceitual sem dados).
   - Com Dados (~20–40s, ~15k tokens, default).
   - Deep Research (~60–120s, ~80k tokens, multifator + RAG).
4. **Tools tipadas** chamando o gateway via `httpx`, **sem acessar
   DuckDB diretamente**. Validação via Pydantic v2 antes do POST.
5. **RAG ChromaDB** populado com ≥30 abstracts/papers seed (lista em §5)
   para sustentar citações DOI nas respostas.
6. **Observabilidade** via Langfuse self-hosted (ou stub para dev) com
   trace por crew + span por agente + span por tool call.

### 2.2 Objetivos secundários

7. **Adaptação ao perfil** detectado (researcher / policy / student) na
   etapa de síntese, com 3 templates de resposta.
8. **Testes E2E** via `pytest` rodando os 3 fluxos com fixture de LLM
   mockado (sem custo Anthropic) + uma suite "live" opt-in que requer
   `ANTHROPIC_API_KEY`.
9. **CLI dev** (`python -m src.cli`) que aceita uma pergunta e imprime
   a resposta — útil para debugging fora do frontend.

### 2.3 Não-objetivos (escopo das Fases 6+)

- **Frontend Next.js** (Fase 6).
- **Streaming SSE bidirecional** — apenas estrutura preparada
  (`yield`-based generator) que a Fase 6 conectará via `EventSource`.
- **Memória de longo prazo do agente** (cross-session) — agentes operam
  stateless por enquanto; histórico é responsabilidade do frontend.
- **Fine-tuning de LLM** — usaremos Sonnet 4.5 + Haiku 4.5 via API.

---

## 3. Decisões arquiteturais propostas

### 3.1 Tools chamam o gateway HTTP, nunca DuckDB

**Por quê**: a regra do `CLAUDE.md` é arquitetural, não cosmética. Se a
tool falar com DuckDB direto, todo SQL/segurança/dedup do `services/`
do `api/` precisaria ser duplicado e teria que conviver com a versão de
prod. Mantemos um único contrato.

**Como**: `agents/src/api_client.py` expõe `EduGatewayClient` com
métodos tipados (`catalog()`, `timeseries(...)`, `compare(...)`,
`ranking(...)`) que serializam Pydantic → JSON → POST. Tools CrewAI são
wrappers finos sobre o client.

```python
class CompareCountriesTool(BaseTool):
    name = "compare_countries"
    description = (
        "Compara um indicador entre N paises (1-50) num ano-fonte. "
        "Use para perguntas tipo 'BR vs FIN em gasto educacional 2022'."
    )
    args_schema = CompareCountriesArgs  # Pydantic

    def _run(self, indicator, countries, year, source="worldbank"):
        client: EduGatewayClient = self._client_factory()
        return client.compare(
            indicator=indicator, countries=countries,
            year=year, source=source,
        ).model_dump()
```

### 3.2 LLM por agente — Sonnet 4.5 vs Haiku 4.5

| Agente | LLM | Justificativa |
|---|---|---|
| Orchestrator | Haiku 4.5 | Roteamento + classificação de fluxo |
| Profile & Intent | Haiku 4.5 | Classificação leve |
| Data Retrieval | Haiku 4.5 | Chama tools — pouco raciocínio |
| Statistical Analyst | Sonnet 4.5 | Raciocínio metodológico (PVs, CIs) |
| Comparative Education | Sonnet 4.5 | Síntese contextual + RAG |
| Citation & Evidence | Haiku 4.5 | Filtragem e formatação de DOIs |
| Visualization | Haiku 4.5 | Gera Plotly spec a partir de dados |
| Response Synthesizer | Sonnet 4.5 | Adaptação ao perfil + qualidade |

Resultado esperado: ~70% das chamadas em Haiku 4.5 (custo baixo),
casos críticos em Sonnet 4.5.

### 3.3 Sem `LiteLLM`, com `langchain-anthropic`

CrewAI suporta múltiplos providers via `LLM` wrapper. Para
**rastreabilidade**, usamos `langchain-anthropic` (pacote oficial) que
garante mapeamento direto de tokens em Langfuse e suporta os IDs
canônicos da Anthropic (`claude-sonnet-4-5`, `claude-haiku-4-5`).

### 3.4 Process: sequential dentro das crews + manager hierárquico

- **Core Crew**: Orchestrator chama Profiler → publica resultado.
- **Analysis Crew**: process=sequential — Retriever → Statistician →
  Comparativist → Citation. Compartilham contexto via output_pydantic.
- **Synthesis Crew**: Visualizer || Synthesizer (paralelo).
- **Master flow** em código Python (não em CrewAI manager) — mais
  simples de testar e logar.

### 3.5 Schemas tipados com `output_pydantic`

Cada agente declara `output_pydantic=ResponseModel`. Isso força CrewAI
a entregar JSON parseável, não markdown solto. Schemas em
`agents/src/schemas.py`:

- `IntentDecision` — fluxo escolhido + perfil.
- `DataNeeded` — quais tools chamar com quais argumentos.
- `StatAnalysis` — resultado estatístico + ressalvas metodológicas.
- `ComparativeContext` — narrativa BR × Internacional.
- `Citations` — lista de DOIs/refs com snippets.
- `VizSpec` — Plotly figure dict (subset de schema válido).
- `FinalAnswer` — markdown + viz refs + sources + warnings.

### 3.6 Tools são "thin wrappers" sobre o client

Tool não embute lógica de negócio. Por exemplo:
`RankingTool._run(...)` chama `client.ranking(...)` e devolve o JSON
serializado. Se o ano não tem dados, repassa o 404 do gateway como erro
estruturado para o agente decidir o próximo passo.

### 3.7 RAG isolado em coleção ChromaDB local

`/data/chromadb/edu_literature/` — coleção embedded (sem servidor),
acessada via cliente em `agents/src/rag/`. Embeddings:
`paraphrase-multilingual-MiniLM-L12-v2` (suporta PT-BR + EN). Metadata
fields: `doi`, `title`, `authors`, `year`, `journal`, `lang`, `source`
(scielo / capes / oecd / iea / unesco / nber / ssrn).

### 3.8 Observabilidade: Langfuse self-hosted opt-in

Em dev, defaults a stdout via structlog. Se `LANGFUSE_HOST` configurado,
pluga callbacks no `langchain-anthropic`. Trace IDs propagados como
`X-Request-ID` para o gateway — fica fácil amarrar uma resposta a quais
queries de DuckDB rodaram.

---

## 4. Catálogo de agentes e tools

### 4.1 Resumo dos 8 agentes

| Agente | Crew | LLM | Tools |
|---|---|---|---|
| Orchestrator | Core | Haiku 4.5 | `classify_flow`, delega às outras crews |
| Profile & Intent | Core | Haiku 4.5 | `extract_entities`, `detect_profile` |
| Data Retrieval | Analysis | Haiku 4.5 | `catalog`, `timeseries`, `compare`, `ranking` |
| Statistical Analyst | Analysis | Sonnet 4.5 | `compute_stats` (puro Python) |
| Comparative Education | Analysis | Sonnet 4.5 | `rag_search`, `cite_resolve` |
| Citation & Evidence | Analysis | Haiku 4.5 | `rag_search`, `format_citation` |
| Visualization | Synthesis | Haiku 4.5 | `make_plotly_spec` (template) |
| Response Synthesizer | Synthesis | Sonnet 4.5 | nenhuma (puro LLM) |

### 4.2 Lista canônica de tools (10)

| Tool | I/O | Endpoint backing |
|---|---|---|
| `data_catalog` | () → list | GET /api/data/catalog |
| `data_timeseries` | TimeseriesArgs → series | POST /api/data/timeseries |
| `data_compare` | CompareArgs → table+stats | POST /api/data/compare |
| `data_ranking` | RankingArgs → ranked list | POST /api/data/ranking |
| `compute_stats` | series → mean/median/cv/trend | local Python |
| `rag_search` | (query, k) → docs | ChromaDB local |
| `cite_resolve` | doi → metadata | crossref.org / cache local |
| `extract_entities` | text → {countries, indicator, year} | Haiku via prompt |
| `detect_profile` | text → researcher\|policy\|student | Haiku via prompt |
| `make_plotly_spec` | series → plotly dict | template Python |

Tools 1–4 dependem do gateway up. Tools 5–10 funcionam offline
(exceto `cite_resolve` que cacheia agressivamente).

### 4.3 Fluxo de chamadas típico

```
User: "BR investe muito em educacao comparado com OCDE?"
  ↓
[Orchestrator] flow=DATA, profile=policy?
  ↓
[Profiler] entities={indicator:GASTO_EDU_PIB, country:BRA, peers:OECD, year:2022}
  ↓
[Retriever] -> data_compare({indicator, [BRA + 38 OECD], 2022, OECD source})
                returns 39 rows + stats {mean, median, BRA percentile}
  ↓
[Statistician] BRA gasto z-score = +0.6, percentil 82, gap +0.61pp vs media
  ↓
[Comparativist] -> rag_search("Brazil education spending OECD comparison")
                contextualiza: Hanushek 2011, Carnoy 2015, OECD EAG 2024
  ↓
[Citation] formata DOIs com snippets (3-5 refs)
  ↓
[Visualizer] gera bar chart horizontal: BRA + top-10 OECD em gasto
  ↓
[Synthesizer] markdown adaptado a "policy maker" com referencia ao PNE
              meta 20 (gasto >= 7% PIB ate 2024)
```

---

## 5. RAG sobre literatura científica

### 5.1 Seeds de papers (mínimo Sprint 5.5)

Lista canônica baseada na bibliografia do `CLAUDE.md` + papers
acessíveis (open access ou preprint):

1. Schleicher (2019). *World Class*. OECD.
2. Hanushek & Woessmann (2011). Economic Policy 26(67).
3. Carnoy, Khavenson, Costa, Marotta (2015). Cad. Pesquisa.
4. Soares & Alves (2003). Educação e Pesquisa 29(1).
5. Fernandes (2007). Série Documental INEP n.26.
6. Angrist, Djankov, Goldberg, Patrinos (2021). Nature 592.
7. OECD (2024). *Education at a Glance 2024*.
8. Mullis et al. (2023). PIRLS 2021 International Results.
9. UNESCO (2020). GEM Report 2020.
10. Barro & Lee (2013). J. Dev. Economics 104.

+20 abstracts adicionais via SciELO (consulta `educacao basica
comparada`) e ERIC (consulta `cross-national education achievement`).

### 5.2 Pipeline de ingestão (offline)

`agents/src/rag/ingest.py`:
- Lê manifesto YAML `data/chromadb/seeds/manifest.yaml` com (doi, title,
  abstract, authors, year, journal, lang, source).
- Gera embeddings via `sentence-transformers` (modelo multilingual).
- Persiste em `data/chromadb/edu_literature/`.
- Idempotente: dedup por DOI; re-embedding só se modelo mudar.

### 5.3 Search

`agents/src/rag/search.py` — `search(query, k=5, filter=None)` →
`list[Document]`. Filtro por `lang`, `source`, `year_range`. Retornos
trazem snippet (passagem com maior similaridade, 200 chars).

---

## 6. Padrões de código

### 6.1 Estrutura final do `agents/`

```
agents/
├── pyproject.toml
├── Dockerfile
├── src/
│   ├── __init__.py
│   ├── config.py              # Settings com prefix AGENTS_*
│   ├── logging_config.py      # structlog (mesmo padrao do api/)
│   ├── api_client.py          # EduGatewayClient (httpx)
│   ├── llm.py                 # factory Claude Sonnet/Haiku
│   ├── schemas.py             # output_pydantic dos agentes
│   ├── cli.py                 # python -m src.cli "pergunta"
│   ├── crews/
│   │   ├── core_crew.py
│   │   ├── analysis_crew.py
│   │   ├── synthesis_crew.py
│   │   └── master_flow.py     # orquestrador Python (sem CrewAI manager)
│   ├── agents/
│   │   ├── orchestrator.py
│   │   ├── profiler.py
│   │   ├── retriever.py
│   │   ├── statistician.py
│   │   ├── comparativist.py
│   │   ├── citation.py
│   │   ├── visualizer.py
│   │   └── synthesizer.py
│   ├── tools/
│   │   ├── data_tools.py      # 4 tools de dados
│   │   ├── stats_tools.py     # compute_stats
│   │   ├── rag_tools.py       # rag_search, cite_resolve
│   │   └── viz_tools.py       # make_plotly_spec
│   ├── prompts/
│   │   ├── orchestrator_system.txt
│   │   ├── profiler_system.txt
│   │   ├── retriever_system.txt
│   │   ├── statistician_system.txt
│   │   ├── comparativist_system.txt
│   │   ├── citation_system.txt
│   │   ├── visualizer_system.txt
│   │   └── synthesizer_system.txt
│   └── rag/
│       ├── client.py          # ChromaDB client + embeddings
│       ├── ingest.py
│       ├── search.py
│       └── seeds/manifest.yaml
└── tests/
    ├── conftest.py            # fixtures: client mock, llm mock
    ├── test_config.py
    ├── test_api_client.py
    ├── tools/
    │   ├── test_data_tools.py
    │   ├── test_stats_tools.py
    │   └── test_rag_tools.py
    ├── agents/
    │   └── test_profiler.py
    └── e2e/
        ├── test_flow_simple.py
        ├── test_flow_data.py
        └── test_flow_deep.py
```

### 6.2 Settings com prefix `AGENTS_*`

Mesma decisão da Fase 4 — prefix dedicado evita colisão com vars de
outros serviços. Aceita `AGENTS_GATEWAY_BASE_URL`,
`AGENTS_ANTHROPIC_API_KEY`, `AGENTS_LLM_DEFAULT_MODEL`,
`AGENTS_RAG_PERSIST_DIR`, etc.

Aliases (`AliasChoices`) cobrem as vars genéricas existentes
(`ANTHROPIC_API_KEY`).

### 6.3 Convenções de prompts

- Cada prompt vive em `prompts/<agente>_system.txt`, plain UTF-8.
- Formato: descrição da identidade + contexto do projeto + regras
  metodológicas críticas (PVs, harmonização ISCED, fontes oficiais) +
  formato de saída esperado.
- Versionados no Git. Mudanças passam por PR.

### 6.4 LLM factory

`llm.py`:

```python
def make_llm(role: Literal["fast", "smart"]) -> LLM:
    """fast=Haiku 4.5, smart=Sonnet 4.5. Configura temperatura e max_tokens."""
```

Centraliza modelo+temperatura para ser fácil A/B testar.

### 6.5 Prefixar logs com agente/fluxo

Todos os agentes bindam `agent_name` e `flow_id` em
`structlog.contextvars` antes de qualquer chamada. Isso permite filtrar
logs por agente em Langfuse/Grafana.

---

## 7. Estratégia de testes

### 7.1 Pirâmide

```
         /\        E2E live (opt-in, requer ANTHROPIC_API_KEY)
        /  \       3 testes — 1 por fluxo
       /----\
      /      \     E2E mockado (default)
     /        \    LLM substituido por respostas fixas; valida orquestracao.
    /----------\
   /            \  Integracao
  /              \ Tools chamando gateway local (httpx.MockTransport).
 /----------------\
                   Unitarios
                   API client puro, schemas, stats helpers, RAG helpers.
```

### 7.2 Mocking de LLM

`pytest` fixture `mock_llm` que substitui `langchain-anthropic`'s
`AnthropicMessagesGenerator` por um stub que devolve respostas
pré-definidas por (agent_name, prompt_hash). Permite rodar suite
inteira em ~1s sem custo.

### 7.3 Suite "live" opt-in

`pytest -m live` — pula por default; só roda com flag. Cobertura ~3
casos canônicos (1 por fluxo). Útil para detectar regressões em
prompts/modelos quando a Anthropic atualiza Sonnet/Haiku.

### 7.4 Cobertura-alvo

- `api_client.py`: 95%+ (crítico)
- `tools/`: 90%+ (crítico para segurança/qualidade)
- `agents/`: 70%+ (lógica fina é prompt; testar via E2E)
- `rag/`: 85%+ (afeta citações)

---

## 8. Sequência de implementação (sprints)

| Sprint | Foco | Entregáveis | Duração |
|---|---|---|---|
| **5.0** | Setup + scaffold | venv, `config.py`, `logging_config.py`, `api_client.py`, schemas, conftest, 2 suites teste | 1 dia |
| **5.1** | Profile + Orchestrator | 2 agentes, prompts, 2 tools (`extract_entities`, `detect_profile`), Core Crew | 2 dias |
| **5.2** | Data Retrieval Agent | 4 tools (`data_*`), agente, integração com gateway local | 2 dias |
| **5.3** | Statistician + Comparativist | 2 agentes, `compute_stats`, ressalvas metodológicas (PVs) | 2 dias |
| **5.4** | Visualization + Synthesizer | 2 agentes, templates Plotly, adaptação a perfil | 1.5 dia |
| **5.5** | RAG ChromaDB | ingest pipeline, ≥30 seeds, search tool, Citation Agent | 2 dias |
| **5.6** | E2E + Langfuse + CLI | 3 fluxos verdes, observability, `python -m src.cli` | 1.5 dia |
| **5.7** | Conclusão + ADR 0003 | `fase-5-conclusao.md`, ADR FastAPI+CrewAI | 0.5 dia |
| **Total Fase 5** | | | **~12 dias úteis** |

### 8.1 Marcos por sprint

- **Após 5.0**: `pytest tests/test_api_client.py` ≥ 5 testes verdes; gateway
  local respondendo via mock transport.
- **Após 5.2**: pergunta exemplo "compare BRA e FIN em gasto 2022" retorna
  JSON estruturado do retriever (sem LLM real, fluxo determinístico).
- **Após 5.4**: pergunta exemplo gera markdown + Plotly spec coerentes.
- **Após 5.5**: resposta inclui 2-3 DOIs reais com snippets relevantes.
- **Após 5.6**: 3 perguntas canônicas atravessam fluxos completos com
  Sonnet 4.5 real, em ≤ 40s mediana, custo ≤ US$0.10/pergunta.

---

## 9. Riscos e mitigações

| # | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|
| R1 | CrewAI muda API entre minor versions | média | alto | Pin exato `crewai==0.80.x` + smoke test antes de upgrade |
| R2 | Custo Anthropic explode em testes | média | médio | LLM mock por default; `-m live` opt-in; budget alarm em Anthropic console |
| R3 | Prompts mal calibrados → respostas erradas | alta | alto | Suite `tests/e2e/` com asserts de fato (ex.: "BRA percentil ∈ [0.7, 0.9]") |
| R4 | RAG cita papers irrelevantes | média | médio | Filtros pré-search por idioma + ano; threshold de similaridade 0.55 |
| R5 | Plausible Values mal aplicados | baixa | crítico | Sprint 5.3 só usa indicadores agregados (% PIB, % literacy); PVs PISA/TIMSS ficam para Fase 5+ |
| R6 | DOIs inválidos / link rot | média | baixo | `cite_resolve` valida via crossref + cache 30 dias |
| R7 | Tool retorna 422 e agente trava | média | alto | Tool wrapper captura ValidationError, devolve `{error, suggestion}` para o agente refazer |
| R8 | Haiku 4.5 indecisivo em routing | baixa | médio | Prompt com poucos exemplos + fallback para Sonnet se confidence baixa |

---

## 10. Critérios de aceitação

A Fase 5 está **concluída** quando:

1. ✅ `pytest agents/tests/` ≥ 50 testes verdes (default mock)
2. ✅ `pytest -m live agents/tests/e2e/` 3 testes verdes
3. ✅ 8 agentes implementados com prompts versionados
4. ✅ 3 crews montadas e roteadas pelo `master_flow`
5. ✅ 10 tools com schemas Pydantic e cobertura ≥ 90%
6. ✅ ChromaDB com ≥ 30 documentos indexados
7. ✅ `python -m src.cli "BR investe muito em educacao?"` retorna
   resposta markdown com ≥ 1 dado, ≥ 1 viz spec, ≥ 1 citação
8. ✅ Custo médio ≤ US$0.10/pergunta no fluxo "Com Dados"
9. ✅ Latência mediana ≤ 40s no fluxo "Com Dados"
10. ✅ `docs/adrs/0003-arquitetura-fastapi-crewai.md` criada
11. ✅ `docs/phases/fase-5-conclusao.md` documentando sprints e métricas

---

*Próximo passo: implementar Sprint 5.0 (setup + scaffold + primeiros
testes do api_client). Ver progresso em
`docs/phases/fase-5-sprint-5.0-progresso.md` (a criar).*
