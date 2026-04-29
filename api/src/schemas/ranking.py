"""Schemas do endpoint POST /api/data/ranking."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.common import GroupingTag, IndicatorId, SourceTag


class RankingRequest(BaseModel):
    """Ranking de paises em um indicador, opcionalmente filtrado por grupo."""

    indicator: IndicatorId
    year: int | None = Field(
        default=None, ge=1990, le=2030,
        description="Ano especifico. None = ano mais recente disponivel.",
    )
    grouping: GroupingTag | None = Field(
        default=None,
        description="Filtra por grupo analitico (oecd, latam, ...). None = global.",
    )
    source: SourceTag = Field(default="worldbank")
    limit: int = Field(default=20, ge=1, le=200)


class RankingItem(BaseModel):
    """Uma posicao no ranking."""

    rank: int
    country_iso3: str
    country_name: str | None = None
    grouping: str | None = None
    value: float
