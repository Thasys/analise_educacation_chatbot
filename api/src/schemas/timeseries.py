"""Schemas do endpoint POST /api/data/timeseries."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from src.schemas.common import CountryISO3, IndicatorId, SourceTag


class TimeseriesRequest(BaseModel):
    """Request para serie temporal de um indicador-pais."""

    indicator: IndicatorId
    country_iso3: CountryISO3
    year_start: int = Field(default=2000, ge=1990, le=2030)
    year_end: int = Field(default=2024, ge=1990, le=2030)
    sources: list[SourceTag] | None = Field(
        default=None,
        description="Filtra por fontes (default: todas as disponiveis para o indicador).",
    )

    @field_validator("year_end")
    @classmethod
    def end_after_start(cls, v: int, info: Any) -> int:
        start = info.data.get("year_start")
        if start is not None and v < start:
            raise ValueError("year_end deve ser >= year_start")
        return v


class TimeseriesPoint(BaseModel):
    """Uma observacao na serie."""

    year: int
    source: str
    source_indicator_id: str | None = None
    value: float
