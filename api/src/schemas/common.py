"""Schemas Pydantic compartilhados pelas rotas de dados."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


# ----------------------------------------------------------------------
# Tipos canonicos
# ----------------------------------------------------------------------

# IDs de indicadores publicados na Silver (extensivel via novos
# int_indicadores__*).
IndicatorId = Literal["GASTO_EDU_PIB", "LITERACY_15M"]

# ISO-3166 alpha-3 (3 letras maiusculas). Validacao em runtime via Field.
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

# Agrupamentos analiticos disponiveis na seed iso_3166_paises.
GroupingTag = Literal[
    "oecd", "oecd_g7", "latam_oecd", "latam",
    "brics", "asia", "africa_mena", "europe_other",
]

# Fontes que aparecem na coluna `source` dos intermediates.
SourceTag = Literal["worldbank", "unesco", "oecd", "eurostat", "ipea", "cepalstat"]


# ----------------------------------------------------------------------
# Envelope de resposta
# ----------------------------------------------------------------------


class ResponseMeta(BaseModel):
    """Metadados que acompanham toda resposta de dados.

    Permite que o frontend e os agentes saibam qual foi a abrangencia
    da query sem precisar contar linhas.
    """

    total_rows: int
    query_ms: float | None = None
    sources: list[str] | None = None
    notes: list[str] | None = None
    extra: dict[str, Any] | None = None


class DataResponse(BaseModel):
    """Envelope padrao: {data: [...], meta: {...}}."""

    data: list[dict[str, Any]]
    meta: ResponseMeta
