"""Schemas do endpoint /api/data/catalog."""

from __future__ import annotations

from pydantic import BaseModel


class CatalogItem(BaseModel):
    """Descreve um mart Gold publicado."""

    name: str
    description: str | None = None
    schema_name: str
    row_count: int
    column_count: int
    tags: list[str] | None = None
