"""Coletores UNESCO UIS.

- `UisRestCollector` (preferido, 2026+) — API REST publica
  https://api.uis.unesco.org/api/public/data/indicators
- `UisCollector` (deprecado) — SDMX-JSON 2.0 do antigo endpoint
  https://api.uis.unesco.org/sdmx (fora do ar desde fev/2026)
"""

from src.collectors.unesco.uis_client import UisCollector
from src.collectors.unesco.uis_rest_client import UisRestCollector

__all__ = ["UisCollector", "UisRestCollector"]
