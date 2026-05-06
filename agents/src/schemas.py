"""Schemas Pydantic compartilhados pelos agentes e tools.

Espelha o subset relevante do contrato OpenAPI exposto pelo gateway
(api/) para que tools possam tipar inputs/outputs sem dependencia
direta do pacote `api`. Ver documentacao em
[/api/data/](http://localhost:8000/docs).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator


# ----------------------------------------------------------------------
# Tipos canonicos (mesmos do api/src/schemas/common.py)
# ----------------------------------------------------------------------

IndicatorId = Literal["GASTO_EDU_PIB", "LITERACY_15M"]

CountryISO3 = Annotated[
    str,
    Field(
        ...,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
        description="Codigo ISO-3166 alpha-3 (3 letras maiusculas).",
    ),
]

GroupingTag = Literal[
    "oecd", "oecd_g7", "latam_oecd", "latam",
    "brics", "asia", "africa_mena", "europe_other",
]

SourceTag = Literal["worldbank", "unesco", "oecd", "eurostat", "ipea", "cepalstat"]


# ----------------------------------------------------------------------
# Inputs das tools (validados ANTES do POST ao gateway)
# ----------------------------------------------------------------------


class TimeseriesArgs(BaseModel):
    """Argumentos da tool data_timeseries."""

    indicator: IndicatorId
    country_iso3: CountryISO3
    year_start: int = Field(default=2000, ge=1990, le=2030)
    year_end: int = Field(default=2024, ge=1990, le=2030)
    sources: list[SourceTag] | None = None

    @field_validator("year_end")
    @classmethod
    def end_after_start(cls, v: int, info: Any) -> int:
        start = info.data.get("year_start")
        if start is not None and v < start:
            raise ValueError("year_end deve ser >= year_start")
        return v


class CompareArgs(BaseModel):
    """Argumentos da tool data_compare."""

    indicator: IndicatorId
    countries: list[CountryISO3] = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=1990, le=2030)
    source: SourceTag = "worldbank"


class RankingArgs(BaseModel):
    """Argumentos da tool data_ranking."""

    indicator: IndicatorId
    year: int | None = Field(default=None, ge=1990, le=2030)
    grouping: GroupingTag | None = None
    source: SourceTag = "worldbank"
    limit: int = Field(default=20, ge=1, le=200)


# ----------------------------------------------------------------------
# Envelope de resposta (mesmo do api/src/schemas/common.py)
# ----------------------------------------------------------------------


class ResponseMeta(BaseModel):
    total_rows: int
    query_ms: float | None = None
    sources: list[str] | None = None
    notes: list[str] | None = None
    extra: dict[str, Any] | None = None


class DataResponse(BaseModel):
    """Envelope padrao retornado por todos os endpoints /api/data/*."""

    data: list[dict[str, Any]]
    meta: ResponseMeta


class CatalogItem(BaseModel):
    name: str
    description: str | None = None
    schema_name: str
    row_count: int
    column_count: int
    tags: list[str] | None = None


# ----------------------------------------------------------------------
# Erros que tools propagam para os agentes (estruturados, nao excecoes)
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# Saidas estruturadas dos agentes (output_pydantic das Tasks)
# ----------------------------------------------------------------------


FlowKind = Literal["simple", "data", "deep"]
"""Os 3 fluxos definidos no CLAUDE.md secao 'Tres fluxos de execucao'.

- simple: pergunta conceitual, sem dados numericos. Path curto: Profiler -> Comparativist -> Synthesizer.
- data: pergunta com dados (default). Path completo via Analysis Crew.
- deep: analise causal/multifator + RAG extensivo. Multiplas iteracoes.
"""

ProfileKind = Literal["researcher", "policy", "student"]
"""Os 3 perfis do usuario detectados a partir do estilo da pergunta."""


class IntentDecision(BaseModel):
    """Saida do Orchestrator Agent — decisao de roteamento."""

    flow: FlowKind = Field(..., description="Fluxo escolhido para a pergunta.")
    profile: ProfileKind = Field(
        ..., description="Perfil detectado (researcher / policy / student)."
    )
    reasoning: str = Field(
        ...,
        max_length=500,
        description="Justificativa breve da escolha (max 2 frases).",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confianca na decisao (0-1). <0.5 sugere fallback.",
    )


class EntityExtraction(BaseModel):
    """Saida do Profile & Intent Agent — entidades extraidas da pergunta.

    Todos os campos sao opcionais porque a pergunta pode nao mencionar
    todas. O Retriever Agent (Sprint 5.2) usa estas entidades para
    montar argumentos das tools de dados.
    """

    indicator: IndicatorId | None = Field(
        default=None,
        description="Indicador canonico mencionado, se identificavel.",
    )
    countries: list[str] = Field(
        default_factory=list,
        description="Codigos ISO-3 dos paises mencionados (ex: ['BRA','FIN']).",
    )
    grouping: GroupingTag | None = Field(
        default=None,
        description="Grupo analitico mencionado (oecd, latam, etc).",
    )
    year: int | None = Field(
        default=None,
        ge=1990,
        le=2030,
        description="Ano especifico mencionado, se houver.",
    )
    year_start: int | None = Field(
        default=None,
        ge=1990,
        le=2030,
        description="Inicio de janela temporal mencionada.",
    )
    year_end: int | None = Field(
        default=None,
        ge=1990,
        le=2030,
        description="Fim de janela temporal mencionada.",
    )
    reasoning: str = Field(
        default="",
        max_length=500,
        description="Como as entidades foram inferidas (max 2 frases).",
    )


class CoreFlowOutput(BaseModel):
    """Saida combinada da Core Crew — alimenta as crews subsequentes."""

    intent: IntentDecision
    entities: EntityExtraction
    question: str = Field(..., description="Pergunta original do usuario.")


class ToolCallRecord(BaseModel):
    """Registro de uma invocacao de tool pelo Retriever."""

    tool: str = Field(..., description="Nome da tool chamada (data_catalog, ...).")
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: Literal["ok", "validation", "not_found", "rate_limited", "network", "unknown"]
    rows_returned: int = 0
    sources: list[str] = Field(default_factory=list)
    error_message: str | None = None


class RetrievedData(BaseModel):
    """Saida do Data Retrieval Agent — alimenta Statistician/Comparativist."""

    summary: str = Field(
        ...,
        max_length=400,
        description="1-2 frases descrevendo o que foi recuperado.",
    )
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    primary_data: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Linhas de dados da tool principal (dataset analisavel).",
    )
    primary_meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Meta da tool principal (sources, query_ms, comparison_stats, etc).",
    )
    warnings: list[str] = Field(default_factory=list)


# ----------------------------------------------------------------------
# Saidas dos agentes analiticos (Sprint 5.3)
# ----------------------------------------------------------------------


class CountryPosition(BaseModel):
    """Posicao de um pais nas estatisticas comparativas."""

    country_iso3: str = Field(..., min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    value: float
    zscore: float | None = Field(default=None, description="(valor - media) / desvio.")
    percentile: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Percentil no conjunto (0=baixo, 1=alto).",
    )
    gap_to_mean: float | None = Field(
        default=None, description="Diferenca absoluta vs media."
    )
    rank: int | None = Field(default=None, ge=1, description="Posicao 1=melhor.")


class StatAnalysis(BaseModel):
    """Saida do Statistical Analyst Agent.

    REGRA METODOLOGICA: este schema e adequado para INDICADORES AGREGADOS
    (% PIB, % alfabetizacao, taxas). NAO usar para microdados PISA/TIMSS/
    PIRLS, que exigem Plausible Values + BRR/Jackknife — nesse caso o
    `method` deve ser 'plausible_values_pending' e o agente deve recusar.
    """

    method: Literal["agregados", "plausible_values_pending"] = Field(
        default="agregados",
        description=(
            "agregados: indicadores oficiais ja agregados (gasto % PIB, "
            "alfab %). plausible_values_pending: o usuario pediu PISA/TIMSS "
            "mas a metodologia ainda nao esta implementada."
        ),
    )
    indicator: str | None = None
    period: str | None = Field(
        default=None,
        description="Periodo coberto (ex.: '2022' ou '2018-2022').",
    )
    sample_size: int = Field(..., ge=0, description="Numero de paises/observacoes.")
    key_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="mean, median, stddev, min, max, cv (coef variacao).",
    )
    focus_country_position: CountryPosition | None = Field(
        default=None,
        description="Posicao do pais foco (tipicamente BRA).",
    )
    other_positions: list[CountryPosition] = Field(
        default_factory=list,
        description="Demais paises ranqueados/posicionados.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Ressalvas metodologicas, dados faltantes, comparacoes invalidas.",
    )
    confidence_note: str = Field(
        default="",
        max_length=400,
        description="1-2 frases sobre o que esta analise mostra/nao mostra.",
    )


class ComparativeContext(BaseModel):
    """Saida do Comparative Education Agent — narrativa BR × Internacional."""

    narrative: str = Field(
        ...,
        max_length=3000,
        description="2-4 paragrafos contextualizando o resultado.",
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Bullet points dos achados principais (3-6 items).",
    )
    historical_context: str | None = Field(
        default=None,
        max_length=1000,
        description="Referencias ao PNE, evolucao historica, contexto de politica publica.",
    )
    methodological_caveats: list[str] = Field(
        default_factory=list,
        description="Limitacoes e ressalvas (cobertura temporal, fontes divergentes, ...).",
    )
    country_groups_compared: list[str] = Field(
        default_factory=list,
        description="Quais grupos/paises foram comparados (ex.: ['BRA','OECD','LATAM']).",
    )


# ----------------------------------------------------------------------
# Saidas dos agentes de sintese (Sprint 5.4)
# ----------------------------------------------------------------------


ChartType = Literal[
    "bar_horizontal",  # ranking de N paises em UM indicador
    "bar_vertical",    # comparacao discreta com poucos paises
    "line_multi",      # serie temporal (1 pais multi-fonte ou multi-pais 1 fonte)
    "scatter",         # cruzamento (gasto x alfab) — Sprint 5+
    "none",            # nenhuma viz aplicavel (fluxo simple)
]


class VizSpec(BaseModel):
    """Saida do Visualization Agent — especificacao de grafico Plotly.

    `plotly_figure` deve ser um dict valido para Plotly.js:
    `{data: [...traces], layout: {...}}`. O frontend (Fase 6) renderiza
    via `react-plotly.js` sem transformacao adicional.
    """

    chart_type: ChartType = Field(..., description="Tipo de grafico.")
    title: str = Field(..., max_length=200)
    plotly_figure: dict[str, Any] = Field(
        ...,
        description="Figure dict valido para Plotly.js (data + layout).",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Fontes dos dados (ex.: ['worldbank']).",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Notas de rodape (cobertura, ano, ressalvas).",
    )


# ----------------------------------------------------------------------
# RAG / Citations (Sprint 5.5)
# ----------------------------------------------------------------------


class Citation(BaseModel):
    """Uma referencia bibliografica retornada pelo Citation Agent."""

    doi: str | None = Field(default=None, description="DOI quando disponivel.")
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = Field(default=None, ge=1900, le=2030)
    journal: str | None = None
    snippet: str | None = Field(
        default=None,
        max_length=500,
        description="Trecho relevante (max 200 chars sem aspas).",
    )
    relevance_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Similaridade da query (1.0 = perfeita).",
    )
    source: str | None = Field(
        default=None, description="Origem do registro (scielo, oecd, ...)."
    )


class Citations(BaseModel):
    """Saida do Citation & Evidence Agent."""

    items: list[Citation] = Field(default_factory=list)
    query_used: str = Field(..., description="Query final aplicada ao RAG.")
    notes: list[str] = Field(default_factory=list)


class FinalAnswer(BaseModel):
    """Saida do Response Synthesizer — resposta final adaptada ao perfil."""

    markdown: str = Field(
        ...,
        max_length=8000,
        description="Resposta completa em markdown adaptada ao perfil.",
    )
    profile_used: ProfileKind = Field(
        ..., description="Perfil detectado e usado para estilo da resposta."
    )
    flow_used: FlowKind = Field(..., description="Fluxo executado.")
    sources_cited: list[str] = Field(
        default_factory=list,
        description="Fontes de dados citadas (worldbank, unesco, ...).",
    )
    visualizations: list[VizSpec] = Field(
        default_factory=list,
        description="Specs de viz embutidas. Frontend renderiza via Plotly.js.",
    )
    citations: list[Citation] = Field(
        default_factory=list,
        description="Referencias academicas com DOIs (do Citation Agent).",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Avisos ao usuario (ex.: 'PISA pendente', 'cobertura limitada').",
    )
    follow_up_suggestions: list[str] = Field(
        default_factory=list,
        description="2-3 sugestoes de perguntas relacionadas para o usuario.",
    )


class GatewayError(BaseModel):
    """Erro estruturado retornado por uma tool quando o gateway falha.

    Tools devem capturar erros HTTP e devolver este modelo serializado em
    vez de levantar excecao - assim o agente pode decidir o proximo
    passo (ex.: tentar outro ano, outro indicador).
    """

    error_type: Literal["validation", "not_found", "rate_limited", "network", "unknown"]
    status_code: int | None = None
    message: str
    suggestion: str | None = None
    request_payload: dict[str, Any] | None = None
