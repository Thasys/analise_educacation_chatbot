"""Acuracia numerica para itens factuais e comparativos.

Compara um valor `actual` (extraido da resposta do sistema) contra um
`expected` (gabarito do golden) com tolerancia relativa configuravel.

Nenhuma dependencia de LLM. Pura logica numerica.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NumericResult:
    """Resultado de uma comparacao numerica unitaria.

    Attributes:
        expected: valor de referencia (gabarito).
        actual: valor extraido da resposta do sistema; `None` se a
            resposta nao continha numero parseavel.
        tolerance_pct: tolerancia relativa em pontos percentuais.
            Default 5%.
    """

    expected: float
    actual: float | None
    tolerance_pct: float = 5.0

    @property
    def within_tolerance(self) -> bool:
        """True se `actual` esta dentro de `tolerance_pct`% de `expected`.

        Regras de borda:
        - `actual is None`  -> False (resposta sem numero falha).
        - `expected == 0`   -> compara modulo de `actual` contra
                               `tolerance_pct/100` (absoluto).
        """
        if self.actual is None:
            return False
        if self.expected == 0:
            return abs(self.actual) <= self.tolerance_pct / 100
        rel_err = abs(self.actual - self.expected) / abs(self.expected)
        return rel_err <= self.tolerance_pct / 100

    @property
    def relative_error(self) -> float | None:
        """Erro relativo `|actual - expected| / |expected|`.

        `None` se `actual` ausente ou `expected == 0` (indefinido).
        """
        if self.actual is None or self.expected == 0:
            return None
        return abs(self.actual - self.expected) / abs(self.expected)


def aggregate_accuracy(results: list[NumericResult]) -> dict[str, float]:
    """Agrega uma lista de `NumericResult` em metricas resumo.

    Returns:
        dict com chaves:
            n: int             — total de itens
            n_correct: int     — itens dentro da tolerancia
            accuracy: float    — n_correct / n
            mean_rel_err: float — media dos erros relativos (ignora None)
    """
    n = len(results)
    if n == 0:
        return {"n": 0, "n_correct": 0, "accuracy": 0.0, "mean_rel_err": 0.0}
    n_correct = sum(1 for r in results if r.within_tolerance)
    rel_errs = [r.relative_error for r in results if r.relative_error is not None]
    mean_rel_err = sum(rel_errs) / len(rel_errs) if rel_errs else 0.0
    return {
        "n": n,
        "n_correct": n_correct,
        "accuracy": n_correct / n,
        "mean_rel_err": mean_rel_err,
    }
