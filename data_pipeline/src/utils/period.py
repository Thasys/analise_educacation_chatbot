"""Parsing canonico de strings de periodo dos coletores.

Centraliza a logica que estava duplicada em 5 coletores (oecd, unesco,
cepalstat, ipea, eurostat) como `_period_bounds` / `_period_filter`.

Formatos aceitos:
  - None              → (None, None)
  - "all" / vazio     → (None, None)
  - "2023"            → (2023, 2023)
  - 2023 (int)        → (2023, 2023)
  - "2010-2023"       → (2010, 2023)

Funcoes auxiliares `format_*` adaptam o resultado para os dialetos
especificos de OData (IPEA) e Eurostat (sinceTimePeriod / untilTimePeriod).
"""

from __future__ import annotations


PeriodBounds = tuple[int | None, int | None]


def parse_period(period: str | int | None) -> PeriodBounds:
    """Converte um valor de periodo em (start, end) inclusivos.

    None / "" / "all" → (None, None).
    "YYYY" / int → (YYYY, YYYY).
    "YYYY-YYYY" → (start, end).

    Levanta ValueError para formato invalido (strings nao-numericas).
    """
    if period is None:
        return None, None
    text = str(period).strip()
    if not text or text.lower() == "all":
        return None, None
    if "-" in text:
        left, right = text.split("-", 1)
        return int(left), int(right)
    year = int(text)
    return year, year


def format_eurostat_period_params(
    bounds: PeriodBounds,
) -> list[tuple[str, int]]:
    """Formata bounds como pares (key, value) para Eurostat REST.

    Eurostat usa `time=YYYY` para ponto unico e
    `sinceTimePeriod=YYYY` + `untilTimePeriod=YYYY` para range.
    """
    start, end = bounds
    if start is None and end is None:
        return []
    if start is not None and end is not None and start != end:
        return [
            ("sinceTimePeriod", start),
            ("untilTimePeriod", end),
        ]
    # Ponto unico (start == end) ou apenas uma das bordas.
    year = start if start is not None else end
    return [("time", year)] if year is not None else []


def format_odata_period_filter(
    bounds: PeriodBounds,
    *,
    field: str = "VALDATA",
) -> str | None:
    """Formata bounds como expressao `$filter` OData v4.

    Default `field='VALDATA'` casa com o schema do IPEA. Retorna None
    quando nao ha filtro a aplicar.
    """
    start, end = bounds
    if start is None and end is None:
        return None
    if start is not None and end is not None and start != end:
        return f"year({field}) ge {start} and year({field}) le {end}"
    year = start if start is not None else end
    if year is None:
        return None
    return f"year({field}) eq {year}"
