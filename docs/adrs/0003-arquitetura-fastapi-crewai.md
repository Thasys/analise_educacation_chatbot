# ADR 0003 — Arquitetura FastAPI + CrewAI: separação de responsabilidades, regra "agente nunca toca SQL", e roteamento por fluxo

- **Status:** aceito
- **Data:** 2026-04-30
- **Fase:** 5 (Sistema de agentes CrewAI)

## Contexto

A Fase 4 entregou um gateway FastAPI estável (4 endpoints REST sobre os
5 marts Gold em DuckDB), e a Fase 5 construiu sobre ele um sistema
multi-agente CrewAI (8 agentes, 10 tools, 4 crews). Esta ADR consolida
as decisões arquiteturais que governam essa separação api/agents — em
particular as que viraram "regras invioláveis" durante as Sprints 5.0
a 5.6.

A força dessa arquitetura está em que **nenhum agente jamais executa
SQL livre nem fala diretamente com o DuckDB**. Toda leitura de dados
passa pelo FastAPI, com SQL parametrizado e service layer validado. Sem
essa disciplina, o sistema seria suscetível a SQL injection via prompt
e a inconsistências metodológicas (ex.: misturar fontes sem dedup).

## Decisões

### 1. Separação de processo: `api/` e `agents/` são serviços distintos

| Aspecto | `api/` | `agents/` |
|---|---|---|
| Linguagem | Python 3.11+ | Python 3.11+ |
| venv | `api/.venv` | `agents/.venv` |
| Entrypoint | `uvicorn src.main:app` | `python -m src.cli` ou import |
| Acesso a DuckDB | **sim** (read-only via lifespan) | **NUNCA** (proibido) |
| Acesso à API Anthropic | nunca | sim (CrewAI LLM) |
| Acesso ao ChromaDB | nunca | sim (`rag/client.py`) |
| Comunicação | recebe HTTP | envia HTTP para `api/` |

Mesma máquina, processos separados. Essa fronteira evita que mudanças
em uma camada (ex.: schema Pydantic do gateway) quebrem a outra fora
do contrato OpenAPI.

### 2. Tools chamam o gateway HTTP, sem exceção

A regra crítica do `CLAUDE.md` ("agentes não escrevem SQL livre") é
honrada **arquiteturalmente**, não por convenção:

- `agents/src/api_client.py::EduGatewayClient` é o único canal de
  acesso a dados do `agents/`.
- Cada tool de dados (`DataCatalogTool`, `DataTimeseriesTool`,
  `DataCompareTool`, `DataRankingTool`) é um wrapper fino sobre o
  client HTTP — não tem `import duckdb` em lugar algum do `agents/`.
- Inputs validados via Pydantic (`args_schema`) ANTES do POST; SQL
  parametrizado vive apenas no `api/src/services/`.

**Por quê.** Mesmo se o LLM for instruído (ou prompt-injected) a "rode
SELECT * FROM users", o agente não tem caminho para fazê-lo. O único
verbo HTTP disponível é `POST /api/data/{compare,timeseries,ranking}` ou
`GET /api/data/catalog`, e cada um devolve apenas dados Gold pré-validados.

### 3. `_SafeDataTool` mixin: erros estruturados em vez de exceções

Descoberto na Sprint 5.2: `crewai.tools.BaseTool.run()` levanta
`ValueError` quando `args_schema` valida e falha — quebrando o loop do
agente CrewAI. Solução padrão para todas as tools que chamam o gateway:

```python
class _SafeDataTool(BaseTool):
    def run(self, *args, **kwargs):
        try:
            return super().run(*args, **kwargs)
        except ValueError as exc:
            return _validation_error_payload(str(exc))  # JSON serializado
```

O LLM recebe `{"ok": false, "error": {"error_type": "validation",
"message": "..."}}` e pode reformular a chamada em vez de travar.
Mitigação direta do risco R7 do `fase-5-analise.md`.

### 4. Cliente compartilhado via `_client_override` (ClassVar)

CrewAI `BaseTool` é Pydantic e recusa atributos arbitrários em runtime.
Para injetar um `EduGatewayClient` ou `RagClient` mockado em testes,
usamos um `ClassVar` por classe de tool:

```python
class DataCompareTool(_SafeDataTool):
    _client_override: ClassVar[EduGatewayClient | None] = None
```

A factory `build_data_tools(client=...)` grava o override em **todas**
as classes antes de instanciar. Em produção fica `None` e cada tool
cria seu client com defaults das settings.

**Trade-off conhecido:** em testes paralelos (`pytest-xdist`) pode
haver race no ClassVar. Como rodamos sequencial (4-CPU dev, ~80s),
não foi observado. Documentar se paralelizarmos.

### 5. LLM por papel: Haiku 4.5 (rotina) vs Sonnet 4.5 (raciocínio)

`agents/src/llm.py::make_llm("fast" | "smart")` resolve o modelo:

| Agente | LLM | Justificativa |
|---|---|---|
| Orchestrator | Haiku 4.5 | Roteamento + classificação curta |
| Profiler | Haiku 4.5 | Extração de entidades |
| Retriever | Haiku 4.5 | Decisão de qual tool chamar |
| Statistician | Sonnet 4.5 | Raciocínio metodológico (z-score, PVs) |
| Comparativist | Sonnet 4.5 | Síntese contextual + RAG |
| Citation | Haiku 4.5 | Filtragem e formatação de DOIs |
| Visualizer | Haiku 4.5 | Decisão de chart type |
| Synthesizer | Sonnet 4.5 | Adaptação de perfil + qualidade redacional |

Resultado esperado: ~70% das chamadas em Haiku (custo baixo), 30% em
Sonnet (qualidade). Custo médio estimado por pergunta no fluxo `data`:
US$0.05–0.10 (a confirmar com suite live).

### 6. CrewAI 1.x: `LLM` factory retorna `AnthropicCompletion`

`crewai.LLM(model="anthropic/<id>", ...)` aciona o native provider
Anthropic do CrewAI 1.14 e devolve uma instância **`AnthropicCompletion`**
(subclasse de `BaseLLM`, **não** de `LLM`). Isso afeta:

- `isinstance(llm, LLM)` é `False`. Use `isinstance(llm, BaseLLM)`.
- `llm.model` strip do prefixo `anthropic/` — para checar provider use
  `llm.provider == "anthropic"`.
- Mock de `LLM.call` precisa cobrir **ambas** as classes:
  `monkeypatch.setattr(LLM, "call", fake)` E
  `monkeypatch.setattr(AnthropicCompletion, "call", fake)`.

Documentado na fixture `mock_llm_call` do `tests/conftest.py`.

### 7. Roteamento por fluxo no `master_flow`

`run_master(question)` decide o pipeline a partir de
`IntentDecision.flow`:

```
simple → Core → Comparativist → Citation → Synthesis
                (placeholders vazios para Retrieved/Stat)
data   → Core → Analysis (Retriever → Stat → Comp → Citation) → Synthesis
deep   → idem data (Sprint 5+ pode aumentar max_iter)
```

Implementação: condicional em Python, não CrewAI manager. Mais simples
de testar (mock por agente), trace por etapa, falha granular por etapa.

### 8. `final.citations` SEMPRE vem do Citation Agent

Decisão de **fonte única de verdade**: o `master_flow` sobrescreve
`FinalAnswer.citations` com `citations.items` do Citation Agent, mesmo
que o Synthesizer também tenha preenchido o campo. Consequência:

- Toda DOI no markdown final foi validada pelo Citation Agent contra o
  RAG (`cite_resolve` + `rag_search`).
- Synthesizer não pode injetar DOI alucinado.
- Validado em `test_master_flow_citations_come_from_citation_agent`.

### 9. RAG embedded ChromaDB (sem servidor)

Decisão de simplicidade vs flexibilidade futura:

- `chromadb.PersistentClient(path="data/chromadb/edu_literature/")`.
- Sem porta HTTP, sem deploy adicional, sem auth.
- Embedding `paraphrase-multilingual-MiniLM-L12-v2` (PT/EN/ES) baixado
  on demand (~500 MB) na primeira execução em produção.
- Em testes: `StubEmbedding` 32-dim baseado em MD5 — determinístico,
  zero download.

Quando virar gargalo (centenas de papers, múltiplos consumidores),
migrar para `chromadb` server ou pgvector. Por agora, embedded basta.

### 10. ChromaDB 1.1.1 EphemeralClient não é isolado entre instâncias

Descoberto na Sprint 5.5: `chromadb.EphemeralClient()` em 1.1.1
compartilha o tenant default entre instâncias do mesmo processo. Para
isolar testes:

- `RagClient` aceita `collection_name` opcional.
- Fixture `rag_client_in_memory` injeta UUID hex 12-char por chamada.
- Em produção fica `settings.rag_collection_name = "edu_literature"`
  (único, persistente).

### 11. Telemetria CrewAI/PostHog desabilitada por default

`run_master` faz `os.environ.setdefault("OTEL_SDK_DISABLED", "true")` e
`os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")` no início.
Evita tráfego não autorizado num projeto acadêmico. Pode ser
sobrescrito explicitamente via env var pré-definida.

### 12. Logs em `sys.__stderr__` (não `sys.stderr`)

`structlog.PrintLoggerFactory(file=sys.__stderr__)` (não `sys.stderr`)
porque pytest capsys substitui `sys.stderr` por test e fecha o handle
no teardown. `sys.__stderr__` aponta para o stderr original do
processo, sobrevive a essas substituições. Side effect intencional:
`pytest -s` mostra logs direto no terminal.

### 13. Schemas espelhados em `agents/`, não importados de `api/`

`agents/src/schemas.py` redefine `IndicatorId`, `CountryISO3`,
`GroupingTag`, `SourceTag` com Pydantic v2 — em vez de importar de
`api/src/schemas/common.py`.

**Por quê.** `agents/` e `api/` têm venvs distintos (`agents/.venv` ~1.9
GB, `api/.venv` ~200 MB). Importar entre eles exigiria PYTHONPATH
hacks ou pacote shared, ambos frágeis. Quando o contrato OpenAPI
estabilizar, podemos gerar `schemas.py` automaticamente via
`datamodel-code-generator` (sprint futura, baixa prioridade).

## Consequências

### Positivas

1. **Segurança**: prompt injection não consegue rodar SQL.
2. **Reprodutibilidade**: toda análise é trace-ável (X-Request-ID
   propagado de agente → tool → API → query).
3. **Testabilidade**: 119 testes mock verdes em ~80s, $0 custo. Suite
   live opt-in para validação periódica.
4. **Modularidade**: trocar Sonnet por Opus 4.7 (futuro) é mudar 1
   string em `config.py`. Trocar provider (OpenAI) é estender o factory
   `make_llm()`.
5. **Custo controlado**: ~70% das chamadas em Haiku 4.5 baixa custo
   estimado para US$0.05–0.10 por pergunta data flow.

### Negativas / dívidas técnicas

1. **Latência**: 4 chamadas LLM sequenciais no Analysis (~10–20s cada
   com Sonnet). Sprint 5+ pode paralelizar Comparativist || Visualizer.
2. **Schemas duplicados**: `agents/schemas.py` espelha
   `api/schemas/common.py`. Drift possível; mitigado por tests do
   gateway que falham se contrato muda.
3. **ClassVar override em tools**: não thread-safe sob `pytest-xdist`.
4. **Suite live nunca rodada com chave real**: $0.10–0.20 por execução.
   Pendente decisão do usuário.

## Alternativas consideradas e rejeitadas

### A. CrewAI Process.hierarchical com manager LLM

Rejeitado: CrewAI manager LLM é caixa preta — debugging do roteamento
fica difícil, custo extra de 1 chamada Sonnet por pergunta. Roteamento
em Python com `if intent.flow == ...` é transparente e testável.

### B. Tools acessando DuckDB diretamente

Rejeitado pela razão central da ADR. Quebraria a regra crítica do
`CLAUDE.md` e duplicaria o service layer do `api/`.

### C. ChromaDB server (Docker)

Adiado: complexidade extra (mais um serviço no docker-compose) sem
benefício enquanto a coleção tem ~25 papers e único consumidor.
Reavaliar quando o RAG crescer para 500+ papers ou múltiplos serviços
quiserem ler.

### D. LiteLLM em vez de native Anthropic provider

Rejeitado: LiteLLM adiciona camada de abstração sem benefício no
contexto (só usamos Anthropic). Native provider tem callbacks de
tokens nativos para Langfuse e mensagens de erro mais claras.

### E. Citations no Synthesizer (sem Citation Agent dedicado)

Rejeitado: separação de responsabilidades garante que toda DOI passou
por validação RAG. Synthesizer focado em redação, Citation Agent
focado em fundamentação — 2 LLM calls especializados em vez de 1
generalista.

## Notas de operação

### Subir o sistema completo

```bash
# Terminal 1: gateway FastAPI (Fase 4)
cd api && .venv/Scripts/uvicorn src.main:app --reload

# Terminal 2: agentes (CLI ad-hoc)
cd agents && .venv/Scripts/python -m src.cli "Como BR vs FIN em gasto educacional 2020?"
```

### Rodar testes

```bash
# Mock (default, $0)
cd agents && .venv/Scripts/python -m pytest -q
# 119 passed, 2 skipped (live)

# Live opt-in (~$0.20 estimado)
cd agents && .venv/Scripts/python -m pytest -m live tests/e2e -v
```

### Substituir LLM por Opus 4.7 quando estiver pronto

Editar `agents/src/config.py`:

```python
llm_smart_model: str = Field(default="claude-opus-4-7", ...)
```

## Referências

- [`CLAUDE.md`](../../CLAUDE.md) §"Sistema de agentes" — regra crítica.
- [`docs/phases/fase-5-analise.md`](../phases/fase-5-analise.md) — plano original e riscos.
- [`docs/phases/fase-5-sprint-5.0-progresso.md`](../phases/fase-5-sprint-5.0-progresso.md)
  até [`fase-5-sprint-5.6-progresso.md`](../phases/fase-5-sprint-5.6-progresso.md)
  — narrativa por sprint.
- ADR 0001 (Bootstrap Fase 0) — estrutura de venvs por serviço.
- ADR 0002 (Schema canônico Silver) — fundamento dos `IndicatorId`/`SourceTag`
  reaproveitados no `agents/schemas.py`.
