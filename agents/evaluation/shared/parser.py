"""Extracao de numeros da resposta markdown do Synthesizer.

Logica espelhada de `src.crews._helpers._extract_numbers` (que e
privada). Mantemos copia para evitar acoplamento ao modulo de
guardrails, e para permitir variantes (`best_match_for_expected`).
"""

from __future__ import annotations

import re


_NUM_RE = re.compile(r"(?<![\w])(-?\d{1,5}(?:[.,]\d{1,4})?)(?![\w])")


def extract_numbers(markdown: str) -> list[float]:
    """Extrai numeros do markdown, EXCLUINDO anos (1900-2099 sem decimal).

    - Aceita virgula ou ponto como decimal (pt-BR / en-US).
    - Excluir anos evita falsos numericos em comparacoes "PISA 2022".
    """
    numbers: list[float] = []
    for raw in _NUM_RE.findall(markdown):
        # Padrao pt-BR: 4,5 e 1.234,5. Aceitamos ambos.
        normalized = raw.replace(".", "").replace(",", ".") if "," in raw else raw
        try:
            value = float(normalized)
        except ValueError:
            continue
        # Filtra anos (1900-2099 inteiros)
        if value.is_integer() and 1900 <= value <= 2099:
            continue
        numbers.append(value)
    return numbers


def best_match(
    numbers: list[float],
    expected: float,
    *,
    tolerance_pct: float = 5.0,
) -> float | None:
    """Retorna o numero MAIS PROXIMO de `expected`, dentro da tolerancia.

    Estrategia honesta:
    1. Calcula erro relativo de cada `numbers[i]` contra `expected`.
    2. Pega o de menor erro.
    3. Se o menor erro ainda excede `tolerance_pct`, retorna None
       (a metrica `within_tolerance` reportara False).

    Por que escolhe o mais proximo em vez do primeiro? Porque o
    markdown pode incluir multiplos numeros (resposta + comparacao
    com OCDE + variacao etc.) e queremos creditar o sistema que
    incluiu o valor correto, mesmo que nao tenha sido o primeiro.

    Variantes `x/100` e `x*100` (%, proporcao) sao testadas como
    no fact-check determinístico — entao "73%" bate com 0.73.
    """
    if not numbers or expected == 0:
        # expected=0: caso degenerado, retornamos o numero absolutamente menor
        if expected == 0 and numbers:
            return min(numbers, key=abs)
        return None

    tol = tolerance_pct / 100.0
    candidates: list[tuple[float, float]] = []  # (err, value)
    for n in numbers:
        for variant in (n, n * 100, n / 100):
            err = abs(variant - expected) / abs(expected)
            candidates.append((err, n))  # devolvemos o `n` original, nao variante
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0])
    best_err, best_value = candidates[0]
    if best_err > tol:
        return None
    return best_value


def first_non_year_number(markdown: str) -> float | None:
    """Heuristica simples: primeiro numero nao-ano do markdown.

    Util quando o item tem `expected_value` mas o item adversarial
    nao tem (e o sistema gerou um numero qualquer que queremos
    capturar para diagnostico). Tambem usado em pre-extracao.
    """
    nums = extract_numbers(markdown)
    return nums[0] if nums else None
