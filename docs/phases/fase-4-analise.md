# Fase 4 — Análise de Desenvolvimento (FastAPI Gateway)

> **Análise Educacional Comparada Brasil × Internacional**
> Documento analítico sobre o desenvolvimento da **Fase 4 — FastAPI Gateway**.
> Complementa o roadmap em [`CLAUDE.md`](../../CLAUDE.md#fase-4--fastapi-gateway-semanas-1011)
> e parte das conclusões da [`Fase 3`](./fase-3-conclusao.md).
> **Data:** 2026-04-29

---

## Sumário

1. [Contexto e ponto de partida](#1-contexto-e-ponto-de-partida)
2. [Objetivos da Fase 4](#2-objetivos-da-fase-4)
3. [Decisões arquiteturais propostas](#3-decisões-arquiteturais-propostas)
4. [Catálogo de endpoints](#4-catálogo-de-endpoints)
5. [Padrões de código](#5-padrões-de-código)
6. [Estratégia de testes](#6-estratégia-de-testes)
7. [Sequência de implementação](#7-sequência-de-implementação)
8. [Riscos e mitigações](#8-riscos-e-mitigações)
9. [Critérios de aceitação](#9-critérios-de-aceitação)

---

## 1. Contexto e ponto de partida

A Fase 3 entregou 5 marts Gold com 1.180 linhas analíticas em DuckDB
local (3.227.257 obs Bronze, 5.229 Silver). A Fase 4 expõe esses dados
via REST para que o frontend (Fase 6) e os agentes CrewAI (Fase 5)
consumam.

A regra crítica do CLAUDE.md (Seção "Sistema de agentes / Regra crítica")
diz: **agentes NÃO escrevem SQL livre**. Todo acesso aos dados passa
por endpoints pré-validados. Isso mantém:

1. **Segurança** — sem SQL injection possível via prompt.
2. **Qualidade metodológica** — filtros canônicos e dedup já aplicados
   no service layer; agentes não podem subverter (ex.: misturar fontes
   sem distinguir).
3. **Observabilidade** — logs estruturados por endpoint, não por query
   ad-hoc do agente.

### Ponto de partida quantitativo

```
api/ bootstrap (Fase 0) com FastAPI 0.110+, /api/health funcionando
0 endpoints de dados · 0 service layer · 0 schemas Pydantic de dados
DuckDB read-only acessivel via path local · 5 marts queriaveis
```

---

## 2. Objetivos da Fase 4

### 2.1 Objetivos primários

1. **4 endpoints REST funcionais** com validação Pydantic v2:
   `/api/data/catalog`, `/api/data/timeseries`, `/api/data/compare`,
   `/api/data/ranking`.
2. **DuckDB connection pool** read-only no lifespan da aplicação,
   compartilhada via dependency injection.
3. **OpenAPI auto-gerado** legível em `/docs` (Swagger UI) com schemas
   válidos para `openapi-typescript`.
4. **Testes integração** via `TestClient` cobrindo os 4 endpoints com
   pelo menos 2 cenários cada (happy path + erro de validação).
5. **Rate limiting via SlowAPI** com limite default de 60 requisições/min
   por IP (configurável via env).

### 2.2 Objetivos secundários

6. **Logs estruturados** via `structlog` com correlation_id por request.
7. **Error handling padronizado** (HTTPException com código + detail).
8. **Health check estendido** verificando DuckDB acessível.

### 2.3 Não-objetivos (escopo das Fases 5+)

- **LLM calls** (são da Fase 5 — agentes CrewAI).
- **Streaming SSE** `/api/chat/stream` (Fase 5).
- **WebSocket** (somente se necessário em Fase 5+).
- **Authentication** (sistema acadêmico privado — adiável).
- **CDN/cache distribuído** (escala atual não justifica).

---

## 3. Decisões arquiteturais propostas

### 3.1 DuckDB read-only com connection pool por thread

**Por quê**: DuckDB suporta múltiplas conexões read-only simultâneas
sobre o mesmo arquivo `.duckdb`. FastAPI rodando com Uvicorn workers
beneficia de pool por thread.

**Como**:

```python
# dependencies/duckdb.py
import duckdb
from fastapi import Request

def get_duckdb_conn(request: Request) -> duckdb.DuckDBPyConnection:
    """Cada request abre cursor isolado; conexao raiz no app.state."""
    return request.app.state.duckdb_conn.cursor()
```

`app.state.duckdb_conn` é criado no lifespan startup com `read_only=True`.

### 3.2 Service layer com SQL pré-validado

Todo SQL vive em `services/`. Routers só chamam services — **nunca
escrevem SQL inline**. Beneficios:

1. SQL com parâmetros tipados (`pais: str`, `ano_inicio: int`).
2. Testes unitários de services sem TestClient (mais rápidos).
3. Rotas REST e serviços CrewAI (Fase 5) compartilham mesmo código de
   acesso a dados.

### 3.3 Schemas Pydantic v2 estritos

Inputs validados com `pydantic.BaseModel` + `Field` constraints:

```python
class TimeseriesRequest(BaseModel):
    indicator: Literal["GASTO_EDU_PIB", "LITERACY_15M"]
    country_iso3: str = Field(..., min_length=3, max_length=3, pattern="^[A-Z]{3}$")
    year_start: int = Field(default=2000, ge=1990, le=2030)
    year_end: int = Field(default=2024, ge=1990, le=2030)
    sources: list[str] | None = None  # default = todas

    @field_validator("year_end")
    @classmethod
    def end_after_start(cls, v, info):
        if "year_start" in info.data and v < info.data["year_start"]:
            raise ValueError("year_end deve ser >= year_start")
        return v
```

Pydantic v2 gera 422 com erro estruturado automaticamente.

### 3.4 Routers organizados por domínio

```
src/routers/
├── health.py       (Fase 0)
├── data.py         (Fase 4 — 4 endpoints data)
└── catalog.py      (Fase 4 — 1 endpoint catalog, separado por simetria)
```

`/api/chat/`, `/api/rag/`, `/api/viz/`, `/api/profile/` ficam para
Fase 5+.

### 3.5 Rate limiting global + override por rota

SlowAPI no app-level com 60 req/min default. Endpoints específicos
podem ter limites menores (ex.: `/data/compare` que faz 3 queries
seguidas) ou maiores (ex.: `/data/catalog` que é cache-friendly).

### 3.6 Logs estruturados com correlation_id

Middleware adiciona `X-Request-ID` (gerado se ausente) e bind via
`structlog.contextvars`. Cada log entry de service/router carrega o
ID, permitindo rastrear request inteira.

### 3.7 Estrutura de resposta consistente

Todas as respostas de dados retornam:

```json
{
  "data": [...],
  "meta": {
    "total_rows": 491,
    "query_ms": 12.4,
    "sources": ["worldbank", "unesco", "oecd"]
  }
}
```

`meta` documenta a query (quantas linhas, latência, fontes envolvidas)
sem exigir endpoint adicional. Permite que frontend mostre "powered by
3 fontes em 12ms".

---

## 4. Catálogo de endpoints

### 4.1 `GET /api/data/catalog`

**Propósito**: lista os marts Gold disponíveis com descrições e
contagens. Frontend usa para popular dropdown de "que análise rodar?".

**Resposta**:

```json
{
  "data": [
    {
      "name": "mart_br_vs_ocde__gasto_educacao_timeseries",
      "description": "Gasto publico em educacao % PIB BR + OCDE (2010-2023)",
      "row_count": 491,
      "country_count": 39,
      "year_min": 2010,
      "year_max": 2023,
      "tags": ["gold", "gasto"]
    },
    ...
  ],
  "meta": {"total_rows": 5}
}
```

**Implementação**: query a `information_schema` + lê `manifest.json` do
dbt para tags/descrições.

### 4.2 `POST /api/data/timeseries`

**Propósito**: série temporal de um indicador para um país (todos os
sources). Backend de gráfico "evolução BR no tempo".

**Request**:

```json
{
  "indicator": "GASTO_EDU_PIB",
  "country_iso3": "BRA",
  "year_start": 2010,
  "year_end": 2023,
  "sources": ["worldbank", "unesco", "oecd"]
}
```

**Resposta**:

```json
{
  "data": [
    {"year": 2010, "source": "worldbank", "value": 5.85},
    {"year": 2010, "source": "unesco", "value": 5.85},
    {"year": 2010, "source": "oecd", "value": 4.88},
    ...
  ],
  "meta": {
    "indicator": "GASTO_EDU_PIB",
    "country_iso3": "BRA",
    "country_name": "Brasil",
    "total_rows": 42,
    "query_ms": 4.2
  }
}
```

**Backend**: query em `mart_br__evolucao_indicadores`.

### 4.3 `POST /api/data/compare`

**Propósito**: comparação entre vários países em um indicador para um
ano. Backend de gráfico de barras "BR vs FIN vs USA em 2020".

**Request**:

```json
{
  "indicator": "GASTO_EDU_PIB",
  "countries": ["BRA", "FIN", "USA", "MEX"],
  "year": 2020,
  "source": "worldbank"
}
```

**Resposta**:

```json
{
  "data": [
    {"country_iso3": "BRA", "country_name": "Brasil", "value": 5.77},
    {"country_iso3": "FIN", "country_name": "Finlandia", "value": 6.68},
    ...
  ],
  "meta": {
    "indicator": "GASTO_EDU_PIB",
    "year": 2020,
    "source": "worldbank",
    "total_rows": 4,
    "comparison_stats": {
      "min": 4.65,
      "max": 6.68,
      "mean": 5.78
    }
  }
}
```

**Backend**: query em intermediate diretamente (mais flexível) com
filtros canônicos.

### 4.4 `POST /api/data/ranking`

**Propósito**: ranking de países em um indicador no ano mais recente
ou ano específico. Backend de "top-10 OCDE em gasto educação 2022".

**Request**:

```json
{
  "indicator": "GASTO_EDU_PIB",
  "year": 2022,
  "grouping": "oecd",
  "source": "worldbank",
  "limit": 10
}
```

**Resposta**:

```json
{
  "data": [
    {"rank": 1, "country_iso3": "ISL", "country_name": "Islandia", "value": 8.49},
    {"rank": 2, "country_iso3": "NOR", "country_name": "Noruega", "value": 8.20},
    ...
  ],
  "meta": {
    "indicator": "GASTO_EDU_PIB",
    "year": 2022,
    "grouping": "oecd",
    "total_in_grouping": 38,
    "showing": 10
  }
}
```

**Backend**: `mart_indicadores__rankings_recente` com filtros.

---

## 5. Padrões de código

### 5.1 Estrutura proposta

```
api/src/
├── main.py                       (atualizado com lifespan DuckDB)
├── config.py                     (novo — settings via pydantic-settings)
├── dependencies/
│   ├── duckdb.py                 (novo — get_duckdb_conn)
│   └── ratelimit.py              (novo — SlowAPI limiter)
├── schemas/
│   ├── common.py                 (novo — IndicatorId, CountryISO3, ResponseMeta)
│   ├── timeseries.py             (novo)
│   ├── compare.py                (novo)
│   ├── ranking.py                (novo)
│   └── catalog.py                (novo)
├── services/
│   ├── catalog_service.py        (novo)
│   ├── timeseries_service.py     (novo)
│   ├── compare_service.py        (novo)
│   └── ranking_service.py        (novo)
└── routers/
    ├── health.py                 (atualizado — verifica DuckDB)
    └── data.py                   (novo — 4 endpoints)
```

### 5.2 Convenção de SQL no service

```python
# services/timeseries_service.py
from typing import Any
import duckdb

def get_timeseries(
    conn: duckdb.DuckDBPyConnection,
    *,
    indicator: str,
    country_iso3: str,
    year_start: int,
    year_end: int,
    sources: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Backend para POST /api/data/timeseries.

    Usa query parametrizada (DuckDB suporta ? positional) -- nunca
    f-string com input do usuario.
    """
    base_query = """
        SELECT year, source, value_br as value, source_indicator_id
        FROM main_marts.mart_br__evolucao_indicadores
        WHERE indicator_id = ?
          AND year BETWEEN ? AND ?
    """
    params: list[Any] = [indicator, year_start, year_end]
    # country_iso3 e fixo no mart_br -- soh aceita BRA. Para outros paises,
    # query iria em outro mart/intermediate. Validacao no schema:
    if country_iso3 != "BRA":
        # Para nao-BRA, usa mart_br_vs_ocde__gasto_educacao_timeseries
        # ou int_indicadores diretamente. Service decide.
        ...

    if sources:
        placeholders = ",".join("?" for _ in sources)
        base_query += f" AND source IN ({placeholders})"
        params.extend(sources)

    return conn.execute(base_query, params).fetchall()
```

### 5.3 Router fino

Routers só:
1. Recebem request validado pelo Pydantic.
2. Chamam service apropriado com argumentos.
3. Empacotam resposta em formato `{data, meta}`.
4. Tratam exceções específicas (ex.: `IndicatorNotFound`).

```python
@router.post("/timeseries", response_model=TimeseriesResponse)
@limiter.limit("60/minute")
def get_timeseries(
    request: Request,
    body: TimeseriesRequest,
    conn: Annotated[duckdb.DuckDBPyConnection, Depends(get_duckdb_conn)],
) -> TimeseriesResponse:
    rows = timeseries_service.get_timeseries(conn, **body.dict())
    return TimeseriesResponse(data=rows, meta=...)
```

### 5.4 Tipos TypeScript via openapi-typescript

Após implementação, gerar:

```bash
cd frontend
npx openapi-typescript http://localhost:8000/openapi.json \
  --output src/lib/api-types.ts
```

Frontend importa types diretamente. Sincronia automática.

---

## 6. Estratégia de testes

### 6.1 Pirâmide

```
       /\
      /UI\        Frontend usa types gerados (ja Fase 6)
     /----\       
    /  E2E \      Playwright em Fase 6+ (fluxo completo de chat)
   /--------\
  /Integration\   FastAPI TestClient (Fase 4)
 /  (services) \  pytest unit em service functions
/----------------\
```

### 6.2 Testes de service

Unit tests sem TestClient — mais rápidos. Cada `services/*` recebe
conexão DuckDB read-only via fixture e roda queries.

```python
# api/tests/services/test_timeseries_service.py
def test_get_timeseries_bra_returns_3_sources(duckdb_conn):
    rows = timeseries_service.get_timeseries(
        duckdb_conn, indicator="GASTO_EDU_PIB",
        country_iso3="BRA", year_start=2018, year_end=2018,
    )
    sources = {r["source"] for r in rows}
    assert sources == {"worldbank", "unesco", "oecd"}
```

### 6.3 Testes de router (TestClient)

Validam contrato HTTP: status codes, schemas de resposta, validation
errors.

```python
# api/tests/routers/test_data.py
def test_timeseries_happy_path(client):
    r = client.post("/api/data/timeseries", json={
        "indicator": "GASTO_EDU_PIB", "country_iso3": "BRA",
        "year_start": 2018, "year_end": 2020,
    })
    assert r.status_code == 200
    assert "data" in r.json()
    assert len(r.json()["data"]) > 0


def test_timeseries_invalid_indicator_returns_422(client):
    r = client.post("/api/data/timeseries", json={
        "indicator": "INVALID_X",
        "country_iso3": "BRA",
        "year_start": 2018, "year_end": 2020,
    })
    assert r.status_code == 422
```

### 6.4 Pre-requisito: DuckDB populado

Testes precisam que `dbt build` tenha sido executado. Fixture conftest
verifica e faz skip se não:

```python
@pytest.fixture(scope="session")
def duckdb_conn():
    path = REPO_ROOT / "data" / "duckdb" / "education.duckdb"
    if not path.exists():
        pytest.skip("DuckDB nao populado; rode `dbt build` primeiro.")
    yield duckdb.connect(str(path), read_only=True)
```

### 6.5 Cobertura-alvo

- Services: 80%+ (core analítico).
- Routers: 60%+ (contrato HTTP).
- Schemas: skip (Pydantic já valida).

---

## 7. Sequência de implementação

| Sprint | Duração | Entregáveis |
|---|---|---|
| **4.0 — Setup** | 0.5 dia | Venv api/, lifespan DuckDB, dep injection, settings, schemas comuns. |
| **4.1 — Endpoints data** | 2-3 dias | 4 endpoints (catalog/timeseries/compare/ranking) com services + schemas + routers. |
| **4.2 — Rate limiting + middleware** | 0.5 dia | SlowAPI integrado, request_id middleware, structlog. |
| **4.3 — Testes** | 1-1.5 dia | Service tests + router tests (TestClient), pelo menos 2 por endpoint. |
| **4.4 — Docs + ADR** | 0.5 dia | OpenAPI exposto em /docs, sample queries em README, ADR 0003. |
| **4.5 — Conclusão** | 0.5 dia | `fase-4-conclusao.md`. |
| **Total** | **~5-6 dias úteis** | (≈ 1 semana) |

Encaixa na janela "semanas 10-11" do CLAUDE.md.

### 7.1 Ordem dentro de Sprint 4.1

1. `/api/data/catalog` primeiro — mais simples, sem parâmetros, valida pipeline.
2. `/api/data/ranking` segundo — uma fonte (mart_rankings_recente), filtros simples.
3. `/api/data/timeseries` terceiro — duas tabelas (mart_br + intermediate para outros países).
4. `/api/data/compare` por último — agregações + estatísticas comparativas.

---

## 8. Riscos e mitigações

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| **DuckDB lock entre dbt build e API** | Baixa | Médio | API abre `read_only=True`; dbt write lock liberado após build. Documentar não rodar dbt em paralelo com API em produção. |
| **Connection pool insuficiente sob carga** | Baixa | Baixo | Single-user system na Fase 4. Quando passar de 10 req/s, considerar pool externo (DuckLake ou similar). |
| **Schema canônico mudando entre Silver e endpoint** | Média | Alto | Service tests validam contrato antes de cada deploy. Quebra de Silver gera erro 500 com mensagem clara, não NULL silencioso. |
| **OpenAPI gerando types fora do esperado para o frontend** | Média | Baixo | `openapi-typescript --check` no CI do frontend (Fase 6). |
| **Rate limiting bloquear desenvolvimento local** | Alta | Baixo | Default 60/min é generoso. Env `API_RATELIMIT_DISABLED=true` para dev. |
| **Erro de Pydantic v2 não-óbvio (changes vs v1)** | Baixa | Baixo | Já em v2 desde Fase 0; padrão sólido. |

---

## 9. Critérios de aceitação

- [ ] **4 endpoints** funcionando com 200 happy path e 422 em validation errors.
- [ ] **OpenAPI em /docs** legível e gerando JSON válido para `openapi-typescript`.
- [ ] **DuckDB connection pool** no lifespan, sem leak entre requests.
- [ ] **Testes integração**: pelo menos 2 cenários por endpoint (8+ tests).
- [ ] **Service layer separado** dos routers (testabilidade).
- [ ] **Rate limiting** ativo com SlowAPI.
- [ ] **structlog** com correlation_id por request.
- [ ] **`docs/phases/fase-4-conclusao.md`** declarando o trabalho final.
- [ ] **README.md atualizado** com instruções de `uvicorn src.main:app --reload`.

---

*Próximo documento ao fim do desenvolvimento: `fase-4-conclusao.md` —
seguindo o template das fases anteriores.*
