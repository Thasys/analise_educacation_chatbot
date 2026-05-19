"""Cobertura de fontes — recall sobre `sources_required`.

Para cada item do golden, ha uma lista `sources_required` (ex.: ["IBGE",
"OECD"]). A funcao mede que fracao dessas fontes aparecem na resposta
gerada pelo sistema.

Implementacao tolera variacao de capitalizacao e aliases comuns (ex.:
"OCDE" -> "OECD", "Banco Mundial" -> "World Bank").
"""

from __future__ import annotations

# Aliases canonicos. Chave = forma canonica (interna); valor = lista de
# strings que devem mapear para a forma canonica.
_SOURCE_ALIASES: dict[str, list[str]] = {
    "OECD": ["oecd", "ocde", "organisation for economic"],
    "IBGE": ["ibge", "instituto brasileiro de geografia"],
    "INEP": ["inep", "instituto nacional de estudos"],
    "UNESCO": ["unesco", "uis", "instituto de estatistica da unesco"],
    "World Bank": ["world bank", "banco mundial", "edstats", "se.xpd"],
    "Eurostat": ["eurostat"],
    "IPEA": ["ipea", "instituto de pesquisa economica aplicada"],
    "CEPAL": ["cepal", "cepalstat", "economic commission for latin america"],
    "PISA": ["pisa"],
    "TIMSS": ["timss"],
    "PIRLS": ["pirls"],
}


def _canonicalize(source: str) -> str | None:
    """Mapeia uma string solta para a forma canonica, ou None se nao bater."""
    s = source.strip().lower()
    if not s:
        return None
    for canon, aliases in _SOURCE_ALIASES.items():
        if canon.lower() == s:
            return canon
        for alias in aliases:
            if alias in s:
                return canon
    return None


def extract_sources(text: str) -> set[str]:
    """Extrai o conjunto de fontes canonicas mencionadas em `text`.

    Match e por substring case-insensitive. Para uma deteccao mais
    robusta usar NER, mas aqui priorizamos determinismo e zero deps.
    """
    found: set[str] = set()
    lower = text.lower()
    for canon, aliases in _SOURCE_ALIASES.items():
        if canon.lower() in lower:
            found.add(canon)
            continue
        for alias in aliases:
            if alias in lower:
                found.add(canon)
                break
    return found


def compute_source_recall(
    response_text: str,
    sources_required: list[str],
) -> float:
    """Recall sobre `sources_required`.

    Returns:
        Fracao em [0, 1] das fontes requeridas que aparecem no texto.
        Se `sources_required` esta vazio, retorna 1.0 (trivial).
    """
    if not sources_required:
        return 1.0
    required_canon = {c for s in sources_required if (c := _canonicalize(s))}
    if not required_canon:
        return 1.0
    found = extract_sources(response_text)
    matched = required_canon & found
    return len(matched) / len(required_canon)
