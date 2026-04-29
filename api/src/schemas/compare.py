"""Schemas do endpoint POST /api/data/compare."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.common import CountryISO3, IndicatorId, SourceTag


class CompareRequest(BaseModel):
    """Comparacao de varios paises em um indicador para um ano."""

    indicator: IndicatorId
    countries: list[CountryISO3] = Field(
        ..., min_length=1, max_length=50,
        description="Lista de codigos ISO-3 a comparar (1 a 50 paises).",
    )
    year: int = Field(..., ge=1990, le=2030)
    source: SourceTag = Field(
        default="worldbank",
        description="Fonte canonica para a comparacao (default: worldbank).",
    )


class ComparePoint(BaseModel):
    """Uma observacao na comparacao."""

    country_iso3: str
    country_name: str | None = None
    grouping: str | None = None
    value: float


class CompareStats(BaseModel):
    """Estatisticas resumidas do conjunto comparado."""

    min: float
    max: float
    mean: float
    median: float
    countries_with_data: int
