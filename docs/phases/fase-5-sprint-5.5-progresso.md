# Fase 5 — Sprint 5.5 (RAG ChromaDB + Citation Agent) — Progresso

> Estado da Sprint 5.5 da Fase 5 (Sistema de agentes CrewAI).
> Complementa [`fase-5-analise.md`](./fase-5-analise.md) e
> [`fase-5-sprint-5.4-progresso.md`](./fase-5-sprint-5.4-progresso.md).
> **Data:** 2026-04-29
> **Status:** ✅ Concluída.

---

## 1. Objetivo

Adicionar fundamentação bibliográfica ao sistema:

- ChromaDB embedded com 25 papers seed da bibliografia do `CLAUDE.md`
  + complementares (SciELO PT-BR, OECD, NBER, IEA, UNESCO).
- 2 tools novas (`RAGSearchTool`, `CiteResolveTool`).
- 1 agente novo: **Citation & Evidence Agent** (Haiku 4.5) que produz
  `Citations` com 2-5 DOIs reais.
- **Comparativist atualizado** para acoplar `RAGSearchTool` —
  passa a poder ancorar afirmações em literatura.

---

## 2. Entregáveis

### 2.1 Arquivos novos

| Arquivo | Linhas | Descrição |
|---|---|---|
| `agents/src/rag/client.py` | 165 | `RagClient` (PersistentClient/EphemeralClient), `StubEmbedding` 32-dim para testes, `get_rag_client()` singleton |
| `agents/src/rag/ingest.py` | 95 | `ingest_manifest(path)` idempotente — id estável via sha256(DOI ou título), upsert em ChromaDB |
| `agents/src/rag/search.py` | 80 | `search_papers(query, k, lang, source, year_from, year_to)` com filtros via `where` $and |
| `agents/src/rag/seeds/manifest.yaml` | 280 | 25 papers seed (10 fundamentais do CLAUDE.md + 15 complementares Brasil/internacional/metodologia/economia da educação) |
| `agents/src/tools/rag_tools.py` | 175 | `RAGSearchTool` + `CiteResolveTool` (validação DOI + lookup local) + `build_rag_tools(client)` |
| `agents/src/agents/citation.py` | 30 | `build_citation(client)` Haiku 4.5 + 2 tools |
| `agents/src/prompts/citation_system.txt` | 65 | regras: filtragem por relevance ≥ 0.55, max 5 itens, proibição de inventar DOI |
| `agents/tests/rag/test_rag_client_search.py` | 175 | 17 testes (StubEmbedding, ingest, search com filtros, isolamento por collection name) |
| `agents/tests/tools/test_rag_tools.py` | 100 | 9 testes (rag_search com lang filter, cite_resolve formato + lookup) |
| `agents/tests/agents/test_citation.py` | 130 | 4 testes (build, real DOI from RAG, empty case) |

### 2.2 Edições

| Arquivo | Mudança |
|---|---|
| `agents/src/schemas.py` | +`Citation`, +`Citations`; `FinalAnswer.citations: list[Citation]` |
| `agents/src/tools/__init__.py` | +exports `RAGSearchTool`, `CiteResolveTool`, `build_rag_tools` |
| `agents/src/agents/__init__.py` | +`build_citation` |
| `agents/src/agents/comparativist.py` | acopla `RAGSearchTool` (não `cite_resolve`); aceita `client` opcional |
| `agents/tests/conftest.py` | +fixture `rag_client_in_memory` (collection name único por chamada) |
| `agents/tests/agents/test_statistician_comparativist.py` | atualizou teste `test_build_comparativist_loads_prompt_with_rag_tool` |
| `agents/pyproject.toml` | filtro `DeprecationWarning:chromadb.*` |

**Total Sprint 5.5: ~1.000 linhas Python + 280 linhas YAML + 65 linhas prompt.**

---

## 3. Decisões aplicadas

### 3.1 ✅ ChromaDB embedded com `PersistentClient` em produção

Sem servidor, sem porta. Diretório default
`data/chromadb/edu_literature/` (configurável via `AGENTS_RAG_PERSIST_DIR`).
Em testes: `EphemeralClient` + collection name único por fixture (UUID
hex 12 chars), pois `EphemeralClient` em ChromaDB 1.1.1 ainda compartilha
o tenant default entre instâncias do mesmo processo.

### 3.2 ✅ `StubEmbedding` 32-dim baseado em MD5 (testes)

Evita o download de ~500 MB do modelo
`paraphrase-multilingual-MiniLM-L12-v2` em CI. Determinístico (mesmo
texto → mesmo vetor) e não-zero (textos diferentes → vetores diferentes).
NÃO usa em produção: similaridade semântica é zero, apenas identidade
textual aproxima.

Implementa `name() = "stub_md5"` para suprimir o warning de futura API
mudança do ChromaDB.

### 3.3 ✅ Manifest YAML com IDs estáveis via sha256

`_stable_id(entry)` gera id 24-char a partir de sha256(DOI lowercased)
ou sha256(título lowercased) como fallback. Garante:
- **Idempotência**: re-rodar `ingest_manifest` não duplica.
- **Estabilidade**: mesmo paper sempre mesmo id, mesmo entre execuções.
- **Privacidade**: id não expõe título no log.

### 3.4 ✅ Manifest com `abstract` PRÓPRIO (não cópia literal)

Cada entrada do `manifest.yaml` traz metadados públicos (DOI, título,
autores, ano, journal) + um abstract PROPRIO em 2-4 frases para fins de
busca semântica. Não reproduz texto original — respeita a regra do
CLAUDE.md (15 palavras literais sem aspas).

### 3.5 ✅ Filtros via `where` ChromaDB com `$and` automático

`_build_where(lang, source, year_from, year_to)` constrói cláusula
ChromaDB válida:
- 0 condições → `None` (sem filtro).
- 1 condição → dict simples `{lang: {$eq: "pt"}}`.
- 2+ condições → `{$and: [...]}`.

Validado em `test_build_where_*` e usado pelos hits filtrados por
língua e janela temporal.

### 3.6 ✅ `relevance_score` normalizado em [0, 1]

ChromaDB devolve `distance` (cosine ∈ [0, 2]). Convertemos para
`relevance_score = max(0, min(1, (1 - distance + 1) / 2))`. Permite
ao agente filtrar com threshold simples (≥ 0.55 sugerido no prompt).

### 3.7 ✅ `CiteResolveTool` valida formato DOI + lookup local

Sprint 5.5: stub local. Valida regex `^10\.\d{4,9}/[-._;()/:A-Za-z0-9]+$`
e busca o DOI exato na metadata da coleção. Retorna estrutura clara:
`{ok, valid, doi, found_in_rag, metadata?}`. Network call ao
crossref.org fica para Sprint 5+ se necessário (com cache 30 dias).

### 3.8 ✅ Comparativist ganhou só `RAGSearchTool` (não `cite_resolve`)

Decisão consciente: o Comparativist usa o RAG para **fundamentar
afirmações** ("Hanushek-Woessmann mostraram que..."), mas a formatação
de citações com DOIs validados fica com o Citation Agent. Evita
duplicação de responsabilidade e inflar o tool set.

### 3.9 ⚠️ Coleção compartilhada vs unique-name por teste

Descoberto que `chromadb.EphemeralClient()` em 1.1.1 **não isola**
estado entre instâncias do mesmo processo. Solução: `RagClient` aceita
`collection_name` no init; fixture de teste injeta UUID por chamada.
Em produção fica `settings.rag_collection_name = "edu_literature"`
(único, persistente).

---

## 4. Métricas finais

```
Pacotes adicionados:           +13 (chromadb 1.1.1 + sentence-transformers 5.4.1
                               + torch 2.11 + transformers 5.7 + scikit-learn 1.8
                               + scipy 1.17 + ...)
Tamanho .venv (delta):         +~700 MB (~1.9 GB total)
Linhas Python adicionadas:     ~1.000 (src + tests Sprint 5.5)
Linhas YAML manifest:          ~280 (25 entradas)
Linhas de prompt:              +65 (citation)
Testes pytest TOTAL:           110 / 110 PASS (~44s)
Testes especificos Sprint 5.5: 30 / 30 PASS
  - rag client/ingest/search: 17 testes (~1s)
  - rag tools: 9 testes (~1s)
  - citation agent: 4 testes (~7s)
Custo Anthropic:               $0.00 (LLM mockado)
RAG seed entries:              25 papers (era 0)
```

---

## 5. Estrutura do `agents/` após Sprint 5.5

```
agents/
├── src/
│   ├── schemas.py               (+ Citation, Citations; FinalAnswer.citations)
│   ├── agents/
│   │   ├── orchestrator.py
│   │   ├── profiler.py
│   │   ├── retriever.py
│   │   ├── statistician.py
│   │   ├── comparativist.py    (atualizado: + RAGSearchTool, aceita client)
│   │   ├── visualizer.py
│   │   ├── synthesizer.py
│   │   └── citation.py         ✅ NOVO
│   ├── prompts/
│   │   ├── orchestrator_system.txt
│   │   ├── profiler_system.txt
│   │   ├── retriever_system.txt
│   │   ├── statistician_system.txt
│   │   ├── comparativist_system.txt
│   │   ├── visualizer_system.txt
│   │   ├── synthesizer_system.txt
│   │   └── citation_system.txt ✅ NOVO
│   ├── crews/
│   │   ├── core_crew.py
│   │   └── synthesis_crew.py
│   ├── tools/
│   │   ├── data_tools.py
│   │   ├── stats_tools.py
│   │   ├── viz_tools.py
│   │   └── rag_tools.py        ✅ NOVO
│   └── rag/
│       ├── __init__.py         ✅ NOVO
│       ├── client.py           ✅ NOVO
│       ├── ingest.py           ✅ NOVO
│       ├── search.py           ✅ NOVO
│       └── seeds/
│           └── manifest.yaml   ✅ NOVO (25 papers)
└── tests/
    ├── agents/
    │   ├── test_orchestrator_profiler.py
    │   ├── test_retriever.py
    │   ├── test_statistician_comparativist.py  (1 teste atualizado)
    │   ├── test_visualizer_synthesizer.py
    │   └── test_citation.py    ✅ NOVO
    ├── tools/
    │   ├── test_data_tools.py
    │   ├── test_stats_tools.py
    │   ├── test_viz_tools.py
    │   └── test_rag_tools.py   ✅ NOVO
    └── rag/
        └── test_rag_client_search.py  ✅ NOVO
```

---

## 6. Próximo: Sprint 5.6 (Master Flow + CLI + suite live)

A Sprint 5.6 amarra TODAS as crews (Core → Analysis → Synthesis) num
fluxo orquestrador único, expõe um CLI dev e adiciona a primeira suite
**live** com chamadas Anthropic reais para validar tool-call loop.

### 6.1 Entregáveis previstos

- `agents/src/crews/master_flow.py` — `run_master(question, *, client) → FinalAnswer`
  orquestrando: `run_core_flow` → `run_analysis_flow` → `run_synthesis_flow`.
- `agents/src/crews/analysis_crew.py` — Retriever + Statistician +
  Comparativist + Citation em sequência (com encadeamento de outputs).
- `agents/src/cli.py` — `python -m src.cli "<pergunta>"` imprime
  FinalAnswer (markdown + viz JSON + sources).
- Marker `live` opt-in: `pytest -m live agents/tests/e2e/`.
- 3 testes live (1 por fluxo simple/data/deep) com asserts soft (≥1
  sources, latência < 60s, custo < $0.20).
- Inicialização Langfuse opcional via `AGENTS_LANGFUSE_*`.

### 6.2 Critério de avanço

`python -m src.cli "Como BR se compara com FIN em gasto educacional 2022?"`
retorna em ≤ 40s mediana com ≥ 1 viz, ≥ 1 citation real, custo ≤
US$0.10. Cobre o critério §10.7-10.9 do `fase-5-analise.md`.

---

## 7. Pendências registradas

1. ⏳ Suite live (`-m live`) com tool-call loop e custo real só Sprint 5.6.
2. ⏳ ADR 0003 — Sprint 5.7.
3. ⚠️ Manifest seed com 25 entradas. Expansão para 50+ via SciELO/ERIC
   crawler fica para Sprint 5+ — manifesto suporta append idempotente.
4. ⚠️ `CiteResolveTool` é stub local. Crossref.org real (com cache 30
   dias) só se tornar bottleneck.
5. ⚠️ `StubEmbedding` MD5 cobre testes mas mistura semântica e
   identidade textual. Quando o suite live rodar com sentence-transformers
   real, alguns asserts de relevance_score podem precisar ajuste.
6. ⚠️ ChromaDB faz download de ~80 MB do modelo onnx default na
   primeira vez que alguém chama `Client()` sem `embedding_function`.
   Em produção usaremos sentence-transformers; em testes usamos
   StubEmbedding — não disparamos esse download intencionalmente.

---

*Próximo doc: `fase-5-sprint-5.6-progresso.md` (a criar quando Sprint
5.6 começar).*
