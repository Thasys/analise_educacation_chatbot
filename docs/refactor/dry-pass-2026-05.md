# Análise de Duplicação de Código (DRY) — analise_educacation_chatbot

> Relatório gerado a partir de uma varredura nas camadas `agents/`, `api/`,
> `data_pipeline/` e `frontend/`. Foram identificados **10 padrões de
> duplicação significativos**, cada um com sugestão de refatoração concreta
> (componente reutilizável, hook ou função utilitária).
>
> Nenhuma alteração de código foi feita — este documento é apenas a base de
> discussão para um eventual sprint de "DRY pass".
>
> **Atualização 2026-05-14**: revisado à luz do
> [quality-assessment-2026-05-14.md](quality-assessment-2026-05-14.md). Vários
> quick wins (QW1, QW3, QW4) e itens de médio prazo (MP2, MP3, MP4) propostos
> naquele relatório dependem ou aceleram-se com as refatorações listadas aqui
> — o mapeamento explícito está na **seção 11** ao final. Como consequência,
> a ordem de execução recomendada (seção final) foi reordenada para colocar
> primeiro o que destrava guardrails de qualidade.

---

## Sumário (priorizado por impacto/esforço)

A coluna **QA** referencia os quick wins (QW) / médios prazos (MP) /
longos prazos (LP) do [quality-assessment-2026-05-14.md](quality-assessment-2026-05-14.md)
que se apoiam diretamente neste padrão. Detalhes na seção 11.

| #  | Padrão duplicado                                                   | Camada           | Arquivos afetados                                                                                   | Esforço | Impacto | QA            |
|----|---------------------------------------------------------------------|------------------|------------------------------------------------------------------------------------------------------|---------|---------|---------------|
| 1  | `build_*` Agent CrewAI (boilerplate de criação de Agent)           | `agents/`        | `agents/src/agents/*.py` (8 arquivos)                                                               | Baixo   | Médio   | MP4, LP1, LP3 |
| 2  | `_run` das tools de dados (3 tools quase idênticas)                | `agents/`        | `agents/src/tools/data_tools.py`                                                                    | Baixo   | Médio   | MP3           |
| 3  | `run()` que captura `ValueError` e devolve JSON de erro            | `agents/`        | `data_tools.py`, `rag_tools.py`, `stats_tools.py`, `viz_tools.py`                                  | Baixo   | Alto    | QW1, QW3, QW4 |
| 4  | `_client_override: ClassVar` + factory `build_*_tools(client=...)` | `agents/`        | `data_tools.py`, `rag_tools.py`, `stats_tools.py`                                                  | Baixo   | Médio   | —             |
| 5  | `_run_<etapa>()` da Analysis Crew (4 etapas idênticas em forma)    | `agents/`        | `agents/src/crews/analysis_crew.py` + `core_crew.py`                                               | Médio   | Alto    | QW3, MP4      |
| 6  | Endpoints FastAPI: medição de tempo + montagem de `DataResponse`   | `api/`           | `api/src/routers/data.py` (3 endpoints)                                                            | Baixo   | Médio   | MP3           |
| 7  | Coletores HTTP: `httpx.Client + try/finally + log + parse`         | `data_pipeline/` | `worldbank/`, `unesco/`, `ibge/`, `ipea/`, `eurostat/`, `oecd/`, `cepalstat/` (7 arquivos)        | Médio   | **Alto**| —             |
| 8  | `_period_bounds` / `_period_filter` (parsing "YYYY" e "YYYY-YYYY") | `data_pipeline/` | `oecd/`, `unesco/`, `cepalstat/`, `ipea/`, `eurostat/` (5 implementações quase idênticas)         | Baixo   | Alto    | —             |
| 9  | Layout 3 colunas das páginas Next.js + render de DOI               | `frontend/`      | `app/compare/page.tsx`, `app/explorer/page.tsx`, `app/library/page.tsx`; `CitationCard` + `ContextPanel` | Baixo   | Médio   | —             |
| 10 | Geradores de figura Plotly (`make_plotly_bar_*`, `make_plotly_line_multi`) | `agents/`  | `agents/src/tools/viz_tools.py`                                                                     | Baixo   | **Alto**| QW1, MP2, LP3 |

---

## 1. Builders de Agente CrewAI (`build_orchestrator`, `build_profiler`, …)

**Local:** [agents/src/agents/](../agents/src/agents/) — 8 arquivos
(`orchestrator.py`, `profiler.py`, `retriever.py`, `statistician.py`,
`comparativist.py`, `citation.py`, `visualizer.py`, `synthesizer.py`).

### Onde está

Cada arquivo declara uma função `build_X()` que retorna `Agent(...)` com
exatamente os mesmos campos repetidos:

```python
# agents/src/agents/profiler.py:15
return Agent(
    role="...",
    goal="...",
    backstory=load_prompt("profiler_system"),
    llm=make_llm("fast"),
    allow_delegation=False,
    verbose=False,
    max_iter=2,
)
```

A única coisa que varia entre os 8 arquivos é:

- `role`, `goal`
- nome do prompt passado a `load_prompt(...)`
- variante de LLM (`"fast"` vs `"smart"`)
- lista de `tools` (vazia para alguns, populada para outros)
- valor de `max_iter` (2 a 5)

Os campos `allow_delegation=False` e `verbose=False` aparecem **8 vezes
idênticos**.

### Sugestão de refatoração

Criar um helper em `agents/src/agents/_builder.py`:

```python
def make_agent(
    *,
    role: str,
    goal: str,
    prompt_name: str,
    llm_kind: Literal["fast", "smart"] = "fast",
    tools: list[BaseTool] | None = None,
    max_iter: int = 3,
) -> Agent:
    return Agent(
        role=role,
        goal=goal,
        backstory=load_prompt(prompt_name),
        llm=make_llm(llm_kind),
        allow_delegation=False,    # invariante do projeto
        verbose=False,             # invariante do projeto
        max_iter=max_iter,
        tools=tools or [],
    )
```

Cada builder passa a ter ~10 linhas em vez de ~20. A regra arquitetural
"agentes nunca delegam" e "agentes não são verbose" fica centralizada e
documentada num único lugar — se um dia precisar mudar, é uma edição.

---

## 2. Tools de dados quase idênticas (`DataTimeseriesTool`, `DataCompareTool`, `DataRankingTool`)

**Local:** [agents/src/tools/data_tools.py:124-199](../agents/src/tools/data_tools.py#L124-L199)

### Onde está

As três classes têm `_run` idêntico exceto pelo nome do endpoint e pela
classe `args_schema`:

```python
# DataTimeseriesTool._run
def _run(self, **kwargs):
    args = TimeseriesArgs(**kwargs)
    client = _client_for_tool(type(self))
    resp = client.safe_call("timeseries", args, request_payload=args.model_dump(exclude_none=True))
    return _serialize_response(resp)

# DataCompareTool._run — idêntico, só muda "compare" e CompareArgs
# DataRankingTool._run — idêntico, só muda "ranking" e RankingArgs
```

### Sugestão de refatoração

Introduzir uma classe base `_EndpointTool` que captura o endpoint e o
schema como atributos:

```python
class _EndpointTool(_SafeDataTool):
    endpoint: ClassVar[str]
    args_model: ClassVar[type[BaseModel]]
    _client_override: ClassVar[EduGatewayClient | None] = None

    def _run(self, **kwargs: Any) -> str:
        args = self.args_model(**kwargs)
        client = _client_for_tool(type(self))
        resp = client.safe_call(
            self.endpoint, args, request_payload=args.model_dump(exclude_none=True)
        )
        return _serialize_response(resp)


class DataTimeseriesTool(_EndpointTool):
    name = "data_timeseries"
    description = "..."
    endpoint = "timeseries"
    args_model = TimeseriesArgs
    args_schema = TimeseriesArgs

# idem para Compare e Ranking
```

Elimina ~50 linhas e impede que as três se divirjam em manutenção futura.

---

## 3. `run()` que captura `ValueError` (handler de validação CrewAI)

**Local:** copiado em 4 arquivos diferentes:

- [data_tools.py:89-93](../agents/src/tools/data_tools.py#L89-L93) — `_SafeDataTool.run`
- [rag_tools.py:63-69](../agents/src/tools/rag_tools.py#L63-L69) — `RAGSearchTool.run`
- [rag_tools.py:138-144](../agents/src/tools/rag_tools.py#L138-L144) — `CiteResolveTool.run`
- [stats_tools.py:148-156](../agents/src/tools/stats_tools.py#L148-L156) — `ComputeStatsTool.run`
- [viz_tools.py:239-245](../agents/src/tools/viz_tools.py#L239-L245) — `MakePlotlySpecTool.run`

### Onde está

Em todos os 5 lugares o corpo é literalmente:

```python
def run(self, *args, **kwargs):
    try:
        return super().run(*args, **kwargs)
    except ValueError as exc:
        return json.dumps({"ok": False, "error": {"error_type": "validation", "message": str(exc)}})
```

O comentário em `stats_tools.py:149-150` admite explicitamente: *"Override
para capturar ValueError da validacao (mesmo padrão de _SafeDataTool)"*.

### Sugestão de refatoração

Promover `_SafeDataTool` (atualmente em `data_tools.py`) para um módulo
compartilhado `agents/src/tools/_base.py` como `SafeTool` ou
`ValidatingTool`. Todas as tools herdam dele. Inclusive `_validation_error_payload`
(`data_tools.py:68`) deve viver lá, pois é referenciado pela classe-base.

Resultado: 5 cópias do mesmo handler viram 1, e tools novas ganham
automaticamente o comportamento de "validação não quebra o loop CrewAI".

---

## 4. `_client_override: ClassVar` + factory `build_*_tools(client=...)`

**Local:**

- [data_tools.py:207-226](../agents/src/tools/data_tools.py#L207-L226) — `build_data_tools(client=...)`
- [rag_tools.py:186-191](../agents/src/tools/rag_tools.py#L186-L191) — `build_rag_tools(client=...)`

### Onde está

O padrão "injetar um cliente compartilhado em ClassVars antes de
instanciar as tools" é repetido:

```python
# data_tools.py
def build_data_tools(client=None):
    if client is not None:
        DataCatalogTool._client_override = client
        DataTimeseriesTool._client_override = client
        DataCompareTool._client_override = client
        DataRankingTool._client_override = client
    return [DataCatalogTool(), DataTimeseriesTool(), ...]

# rag_tools.py  — mesma estrutura, outras classes
def build_rag_tools(client=None):
    if client is not None:
        RAGSearchTool._client_override = client
        CiteResolveTool._client_override = client
    return [RAGSearchTool(), CiteResolveTool()]
```

Toda nova tool exige (a) declarar o `ClassVar`, (b) atualizar a factory.
É fácil esquecer um dos dois passos.

### Sugestão de refatoração

Helper genérico que recebe a lista de classes e o cliente:

```python
T = TypeVar("T", bound=BaseTool)

def instantiate_with_shared_client(
    tool_classes: Sequence[type[T]],
    client: object | None,
) -> list[T]:
    if client is not None:
        for cls in tool_classes:
            cls._client_override = client
    return [cls() for cls in tool_classes]
```

E `build_data_tools(client) = instantiate_with_shared_client([DataCatalogTool, ...], client)`.

---

## 5. Funções `_run_<etapa>()` da Analysis Crew

**Local:** [agents/src/crews/analysis_crew.py:71-180](../agents/src/crews/analysis_crew.py#L71-L180)
e funções `_coerce_*` duplicadas em
[core_crew.py:80-97](../agents/src/crews/core_crew.py#L80-L97).

### Onde está

`_run_retriever`, `_run_statistician`, `_run_comparativist`, `_run_citation`
têm a mesma forma — só mudam o builder, a Task description e o
`output_pydantic`:

```python
def _run_X(core, ...):
    agent = build_X(...)
    payload = json.dumps({...}, ensure_ascii=False)
    task = Task(
        description=f"... {payload}",
        expected_output="JSON X",
        output_pydantic=X,
        agent=agent,
    )
    raw = _kickoff_single(agent, task)
    return _coerce(X, raw)
```

Além disso, `_coerce(model_cls, raw)` definida em `analysis_crew.py:45-52`
existe **duas vezes mais** em `core_crew.py:80-97` como `_coerce_intent`
e `_coerce_entities` — três implementações da mesma rotina.

### Sugestão de refatoração

**5.1** — Mover `_coerce(model_cls, raw)` para um helper compartilhado em
`agents/src/crews/_helpers.py`. Usar em `core_crew.py` no lugar dos dois
`_coerce_*`.

**5.2** — Extrair um `run_single_agent_task(...)` que recebe agent,
descrição, output schema e payload-dict:

```python
def run_single_agent_task(
    agent: Agent,
    *,
    description: str,
    output_schema: type[BaseModel],
    payload: dict,
) -> BaseModel:
    body = json.dumps(payload, ensure_ascii=False)
    task = Task(
        description=f"{description}\n\nCONTEXTO:\n{body}",
        expected_output=f"JSON {output_schema.__name__}",
        output_pydantic=output_schema,
        agent=agent,
    )
    raw = _kickoff_single(agent, task)
    return _coerce(output_schema, raw)
```

Cada `_run_X` cai para 5–8 linhas, mantendo a descrição específica como
única responsabilidade da função.

---

## 6. Endpoints FastAPI: cronometragem + montagem da resposta

**Local:** [api/src/routers/data.py](../api/src/routers/data.py) — 3 endpoints
(`/timeseries`, `/compare`, `/ranking`).

### Onde está

Em todos os três endpoints:

```python
started = time.perf_counter()
rows, ... = service(...)
elapsed_ms = (time.perf_counter() - started) * 1000.0
return DataResponse(
    data=rows,
    meta=ResponseMeta(total_rows=len(rows), query_ms=round(elapsed_ms, 2), ...),
)
```

E em todos: bloco "se `not rows` adiciona uma nota explicativa em
português". 3 cópias quase idênticas.

### Sugestão de refatoração

**6.1** — Decorator/contextmanager para tempo de query:

```python
@contextmanager
def measure_query_ms() -> Iterator[Callable[[], float]]:
    started = time.perf_counter()
    yield lambda: (time.perf_counter() - started) * 1000.0
```

Uso:

```python
with measure_query_ms() as elapsed:
    rows, stats = compare_service.compare_countries(conn, ...)
return DataResponse(
    data=rows,
    meta=ResponseMeta(total_rows=len(rows), query_ms=round(elapsed(), 2), ...),
)
```

**6.2** — Função `build_data_response(rows, *, query_ms, sources=None,
extra=None, empty_note=None)` que monta o `DataResponse` consistente para
todos os endpoints. Padroniza a regra "se vazio, adiciona uma nota".

---

## 7. Coletores HTTP: `httpx.Client + try/finally + log antes/depois + parse`

**Local:** [data_pipeline/src/collectors/](../data_pipeline/src/collectors/)
— 7 coletores REST:

- `worldbank/api_client.py`
- `unesco/uis_rest_client.py`
- `ibge/sidra_educacao.py`
- `ipea/odata_client.py`
- `eurostat/jsonstat_client.py`
- `oecd/sdmx_client.py`
- `cepalstat/api_client.py`

### Onde está

Todos repetem o mesmo esqueleto de `fetch()`:

```python
def fetch(self, *, reference_period, **kwargs) -> tuple[pd.DataFrame, str]:
    url = self.build_url(reference_period)
    client = self._http_client or httpx.Client(timeout=settings.http_timeout_seconds)
    try:
        log.info("<source>.fetch", url=url, ...)
        response = client.get(url, headers={"Accept": "application/json"})
        response.raise_for_status()
        payload = response.json()
    finally:
        if self._http_client is None:
            client.close()

    df = self._parse_payload(payload)
    log.info("<source>.fetch.parsed", url=url, rows=len(df), columns=len(df.columns))
    return df, url
```

Variações pequenas:

- `Accept` é `application/vnd.sdmx.data+json;version=2.0.0` no OECD,
  `application/json` nos demais.
- IBGE não tem `try/finally` em torno do log inicial (sutil).
- `WorldBank` e `IPEA` envolvem isto em um loop de paginação.

### Sugestão de refatoração

Promover essa estrutura para um *mixin* em `collectors/base.py` ou um
método protegido `BaseCollector._http_fetch_json(url, *, accept=None)`
que devolve `payload` e gerencia o ciclo de vida do client. Cada
subclasse precisa apenas implementar `build_url`, `parse_payload`, e
chamar `self._http_fetch_json(url)`.

Para os dois casos com paginação (`WorldBank`, `IPEA`), oferecer um
helper paralelo `_http_fetch_paginated(first_url, *, next_link_fn)` que
recebe a função de extração do próximo link.

Benefícios:

- Define um único ponto para configurar timeouts/retry/headers padrão.
- Reduz risco de bugs de leak de `httpx.Client` (3 dos 7 dependem do
  `try/finally` correto).
- Padroniza convenção de logging (`<source>.fetch` / `<source>.fetch.parsed`).

---

## 8. `_period_bounds` / `_period_filter` (parsing "YYYY" e "YYYY-YYYY")

**Local:** literalmente a mesma função em 5 coletores:

- [oecd/sdmx_client.py:102-113](../data_pipeline/src/collectors/oecd/sdmx_client.py#L102-L113)
- [unesco/uis_rest_client.py:105-116](../data_pipeline/src/collectors/unesco/uis_rest_client.py#L105-L116)
- [cepalstat/api_client.py:124-135](../data_pipeline/src/collectors/cepalstat/api_client.py#L124-L135)
- [ipea/odata_client.py:109-122](../data_pipeline/src/collectors/ipea/odata_client.py#L109-L122) (variante: gera filtro OData)
- [eurostat/jsonstat_client.py:120-134](../data_pipeline/src/collectors/eurostat/jsonstat_client.py#L120-L134) (variante: gera pares `since/until`)

### Onde está

Versão "canônica" repetida sem mudança nenhuma:

```python
@staticmethod
def _period_bounds(period: str | int | None) -> tuple[int | None, int | None]:
    if period is None:
        return None, None
    text = str(period).strip()
    if not text or text.lower() == "all":
        return None, None
    if "-" in text:
        start, end = text.split("-", 1)
        return int(start), int(end)
    year = int(text)
    return year, year
```

Aparece 3x idêntica + 2 variantes que apenas serializam o resultado
diferente.

### Sugestão de refatoração

Função utilitária pura em
`data_pipeline/src/utils/period.py`:

```python
def parse_period(period: str | int | None) -> tuple[int | None, int | None]:
    """Converte 'YYYY' / 'YYYY-YYYY' / None / 'all' em (start, end) inclusivos."""
    ...
```

Cada coletor importa e usa. Os dois casos "variantes" (OData / Eurostat)
viram funções `format_*` que aceitam o tuple e produzem o formato
específico:

```python
def format_eurostat_period_params(bounds): ...
def format_odata_period_filter(bounds): ...
```

Aumenta testabilidade (uma função pura, 1 arquivo de testes) e impede a
divergência sutil que já está acontecendo (no IPEA o "all" não é tratado
explicitamente — só None).

---

## 9. Frontend: layout das páginas + render de citação DOI

### 9.1 — Layout 3 colunas

**Local:**
- [app/compare/page.tsx](../frontend/app/compare/page.tsx)
- [app/explorer/page.tsx](../frontend/app/explorer/page.tsx)
- [app/library/page.tsx](../frontend/app/library/page.tsx)

Cada página repete:

```tsx
<div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
  <Sidebar />
  <Workspace>{...}</Workspace>
  <ContextPanel />
</div>
```

A diferença entre as três é só o filho de `<Workspace>`.

**Sugestão:** mover o shell para `frontend/app/layout.tsx` (ou criar um
sub-layout em `app/(workspace)/layout.tsx` com a estrutura compartilhada)
e deixar cada `page.tsx` retornar apenas o conteúdo do workspace.

Isso também resolve o problema sutil de o `ContextPanel` da página
`/library` mostrar fontes da última conversa do `/compare` — fica óbvio
que ele vive no layout pai, não em cada página.

### 9.2 — Render do link DOI

**Local:**
- [components/citations/CitationCard.tsx:34-44](../frontend/components/citations/CitationCard.tsx#L34-L44)
- [components/layout/ContextPanel.tsx:68-77](../frontend/components/layout/ContextPanel.tsx#L68-L77)

Os dois componentes renderizam o mesmo bloco para abrir um DOI:

```tsx
<a
  href={`https://doi.org/${citation.doi}`}
  target="_blank"
  rel="noopener noreferrer"
  className="..."
>
  ...
</a>
```

**Sugestão:** componente `<DoiLink doi="..." variant="icon" | "text" />`
em `components/citations/DoiLink.tsx`. Centraliza `target="_blank"
rel="noopener noreferrer"` e a base `https://doi.org/`, e ajuda futura
adição de fallback (ex.: badge "DOI inválido" se a regex falhar — hoje
ambos componentes confiam cegamente).

### 9.3 — Bloco "metadata da citação" (título + autores + ano + jornal)

A formatação `authors / (year). journal` aparece em duas formas
diferentes:

- `CitationCard.tsx:25-30` — formato completo.
- `ContextPanel.tsx:64-66` — versão resumida ("Autor et al. (year)").

Pode-se extrair um util `formatCitationMeta(citation, *, mode: 'full' | 'short')`
em `lib/utils/citation.ts`, evitando que os formatos divirjam.

---

## 10. Geradores de figura Plotly (`make_plotly_bar_horizontal`, `make_plotly_bar_vertical`, `make_plotly_line_multi`)

**Local:** [agents/src/tools/viz_tools.py:50-174](../agents/src/tools/viz_tools.py#L50-L174)

> Padrão acrescentado após cruzar com o
> [quality-assessment-2026-05-14.md](quality-assessment-2026-05-14.md): a
> ação **MP2** ("Plotly figure dict via template paramétrico — LLM não toca
> em arrays de números") depende justamente de consolidar esses três
> templates num builder paramétrico único, fortalecendo a função pura que
> recebe rows e devolve um figure dict garantidamente válido.

### Onde está

`make_plotly_bar_horizontal` e `make_plotly_bar_vertical` são ~90%
idênticas:

```python
def make_plotly_bar_horizontal(rows, *, value_field, label_field, title, x_axis_title, sort_descending=True):
    if not rows:
        return _empty_figure(title or "Sem dados")
    items = [r for r in rows if r.get(value_field) is not None]
    items.sort(key=lambda r: r[value_field], reverse=sort_descending)
    labels = [str(r.get(label_field, "?")) for r in items]
    values = [float(r[value_field]) for r in items]
    colors = [_color_for(label) for label in labels]
    return {"data": [{"type": "bar", "orientation": "h", "x": values, "y": labels, ...}], "layout": {...}}

def make_plotly_bar_vertical(rows, *, value_field, label_field, title, y_axis_title):
    # mesmas 6 linhas iniciais (sem o sort)
    # depois retorna: {"data": [{"type": "bar", "x": labels, "y": values, ...}], "layout": {...}}
```

`make_plotly_line_multi` repete o mesmo `if not rows / filter not-None / float
cast` antes de seu loop de séries.

### Sugestão de refatoração

**10.1** — Extrair um helper privado `_extract_xy(rows, *, value_field,
label_field, sort_descending=False)` que devolve `(labels, values, colors)`
já filtrados. Cada `make_plotly_*` passa a ter ~10 linhas.

**10.2** — Como `bar_horizontal` e `bar_vertical` diferem só por
orientação, unificar em `make_plotly_bar(orientation: Literal["h","v"])`.

**10.3** — Validação de tipos no ponto de saída (resolve QW1 do quality
assessment): adicionar a função `_validate_figure(fig: dict) -> dict` que
percorre `fig["data"]` e:

- garante que `x` e `y` são `list[number | str]` (não string serializada);
- garante `marker.color` é hex ou paleta válida;
- em falha, retorna `_empty_figure("Erro de validação")` com log de
  estrutura — não devolve o dict quebrado para o frontend.

Hoje o agente pode emitir `"x": "['BRA','MEX','CHL']"` (string) e o
frontend simplesmente não renderiza (caso real observado no QA
2026-05-14, seção 2.1). Centralizar a validação aqui fecha essa porta sem
precisar mexer no Synthesizer, no schema Pydantic ou no frontend.

### Por que importa fora do DRY

Esta é a refatoração de **maior alavancagem para qualidade**, e não só
para limpeza:

- Hoje, **0%** dos `plotly_figure` emitidos no teste de referência são
  renderizáveis (QA 2026-05-14, seção 5). A causa raiz é o LLM emitir
  arrays como strings, e nenhum agente downstream detectar.
- Com o builder paramétrico, o LLM só decide `chart_type`, `value_field`,
  `label_field`; arrays vêm dos dados reais. Alucinação numérica em viz
  fica estruturalmente impossível.

---

## Outras observações menores (não detalhadas)

- **`compute_summary_stats` em `tools/stats_tools.py:29-62`** duplica
  parcialmente a lógica que `compare_service.py:62-68` faz com
  `statistics.fmean/median/min/max`. Não é uma duplicação direta (uma é
  helper agnóstico, outra é inline na service), mas mantê-las em sincronia
  no longo prazo exige cuidado — vale promover `compute_summary_stats`
  para um `shared/stats.py` e ambos usarem dali.

- **Validações de período (`_period_filter` em IPEA, `_period_params` em
  Eurostat)** poderiam compartilhar a função canônica acima depois de
  parsear o tuple — ver item 8.

- **`InlineChart.tsx` e `MartCard.tsx`** repetem o padrão de "header
  pequeno + corpo + footer pequeno" com as mesmas classes Tailwind
  (`rounded-md border border-border bg-card/40 p-3 text-xs`). Não é
  duplicação de lógica, mas se for surgir um terceiro card desse
  estilo, talvez valha um `<ContentCard>` base sobre `<Card>`.

- **`agents/src/agents/__init__.py`** (não inspecionado em detalhe)
  provavelmente reexporta cada `build_*` — manter coerência ao introduzir
  o `make_agent` helper.

---

## 11. Conexões com o quality-assessment 2026-05-14

O [quality-assessment](quality-assessment-2026-05-14.md) catalogou problemas
de **conteúdo** gerados pelos LLMs locais (gráficos quebrados, números
alucinados, DOIs inventados). Os itens dele e os padrões DRY listados aqui
não competem — eles se reforçam: vários guardrails só ficam viáveis (ou
ficam consistentes em vez de pontuais) se as duplicações estiverem
resolvidas.

| Item QA | Descrição                                                                | DRY que destrava / acelera                                                                                                                                                          |
|---------|--------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| QW1     | Validar `plotly_figure.data[*].x/y` no Visualizer antes de emitir        | **#10** (`_validate_figure` no builder paramétrico) + **#3** (SafeTool base já tem o protocolo "validação devolve JSON de erro estruturado" — só herdar).                          |
| QW3     | Pós-validação regex de números no markdown vs `primary_data`             | **#3** (SafeTool base se torna `SafeOrValidatedTool`, aceita um `output_validator` opcional) + **#5** (extrair `run_single_agent_task` permite encaixar a validação num único ponto). |
| QW4     | Citation: se RAG vazio, devolver `Citations(items=[], notes=[...])`      | **#3** (mesma extensão do SafeTool — `RAGSearchTool` herda do mesmo base e ganha o fallback uniforme).                                                                              |
| MP2     | Plotly via template paramétrico — LLM não toca em arrays                 | **#10** explicitamente — é o trabalho. Sem consolidar `make_plotly_*` antes, MP2 vira reescrita; com #10 feito, MP2 é um delta de ~20 linhas.                                       |
| MP3     | Tool `data_describe(indicator, year, country)` que retorna texto pronto  | **#2** (`_EndpointTool` base) — adicionar a 4ª tool com endpoint próprio fica trivial. **#6** (helpers `build_data_response` no FastAPI) — o endpoint correspondente reusa pattern. |
| MP4     | Fact-checker agent leve (Haiku ou qwen 7B) sobre `markdown` + `data`     | **#1** (`make_agent` helper) — adicionar um 9º agente sem replicar boilerplate. **#5** (`run_single_agent_task`) — orquestrar este agente entre Synthesis e final.                  |
| LP1     | Provider Anthropic opcional para Synthesizer                              | **#1** indiretamente — todos os builders já passam por `make_llm(...)`, então a troca é uma flag. **#1** apenas reforça que essa centralização não pode ser quebrada nas próximas tools/agents. |
| LP3     | JSON Schema strict output (Ollama 0.4+ `format: <schema>`)                | **#1** (`make_agent` é o ponto único onde plugar `format=<schema>`) + **#10** (define o schema do `plotly_figure` que o LLM tem que emitir — sem builder paramétrico, é difícil escrever o schema). |

**Itens DRY que não conectam ao quality-assessment** (#4, #7, #8, #9):
são puramente higiene de código. Ficam relevantes só na medida em que
reduzem o custo de adicionar novos coletores/endpoints/páginas.

---

## Recomendação de ordem de execução

> Reordenada após cruzar com o quality-assessment. A nova prioridade
> **coloca primeiro o que destrava guardrails de qualidade** (QW1–QW4,
> MP2, MP3), e só depois a higiene pura.

### Fase A — desbloqueia QA fixes (5–6 h)

Esta fase deve preceder qualquer trabalho do quality plan, exceto QW2
(que é só edição de prompt — independente).

1. **#3** (SafeTool base) — 30 min. Reaproveitado por **QW1**, **QW3**,
   **QW4**.
2. **#10.1 + 10.2** (consolidar `make_plotly_*` em um único builder
   paramétrico + helper `_extract_xy`) — 1 h. Pré-requisito de **MP2**.
3. **#10.3** (`_validate_figure` no ponto de saída) — 30 min. Implementa
   **QW1** já como parte do DRY.
4. **#1** (`make_agent` helper) — 1 h. Pré-requisito de **MP4** e da
   troca de provider em **LP1** sem regressão.
5. **#2** (`_EndpointTool` base) — 1 h. Pré-requisito de **MP3**
   (`data_describe` tool fica trivial).
6. **#5** (`run_single_agent_task` + `_coerce` compartilhado) — 1–2 h.
   Pré-requisito de **QW3** (validador no ponto único) e **MP4**.

Ao fim da Fase A, executar **QW1, QW2, QW3, QW4** do quality plan. Esse
combo elimina alucinação de gráfico e DOI sem mudar de modelo.

### Fase B — higiene de código (3–4 h)

Pode rodar em paralelo com a Fase 4.2 do quality plan (MP1–MP4) ou
depois. Não há dependência cruzada.

7. **#8** (parse_period utilitário) — 30 min.
8. **#6** (helpers de endpoint FastAPI) — 1 h. Bom companheiro de
   **MP3** (novo endpoint `/api/data/describe` reusa o pattern).
9. **#9.1** (layout shared em `app/(workspace)/layout.tsx`) — 30 min.
10. **#9.2 + 9.3** (DoiLink + formatCitationMeta) — 1 h.
11. **#4** (`instantiate_with_shared_client`) — 30 min. Depende de #3
    pronto.

### Fase C — refator pesado (2–3 h)

12. **#7** (HTTP fetch boilerplate em `BaseCollector`) — 2–3 h. Requer
    re-rodar testes de cada coletor; nenhum benefício direto para o
    quality plan, então fica por último.

### Resumo

| Fase | Conteúdo                                       | Esforço | Conecta a                |
|------|------------------------------------------------|---------|--------------------------|
| A    | DRY que destrava qualidade (#3, #10, #1, #2, #5) | 5–6 h   | QW1, QW3, QW4, MP2, MP3, MP4 |
| B    | Higiene de código (#8, #6, #9, #4)             | 3–4 h   | MP3 (#6 indireto)        |
| C    | Refator pesado (#7)                            | 2–3 h   | — (puramente DRY)        |

Total estimado: **~10–13 horas de refatoração** + testes existentes
revalidados, sem alteração funcional do sistema. A diferença em relação
à ordem original é que agora a Fase A entrega, além de código mais
limpo, a infraestrutura que permite implementar os quick wins QW1–QW4
de forma uniforme em vez de uma série de fixes pontuais.
