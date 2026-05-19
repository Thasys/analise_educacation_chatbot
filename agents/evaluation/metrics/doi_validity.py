"""Validade de DOIs citados nas respostas.

Duas camadas:

1. **Sintatica** (`is_doi_syntactically_valid`): regex padrao DOI
   (10.NNNN/qualquer-coisa). Pura, sem rede.
2. **Resolvivel** (`is_doi_resolvable`): faz HEAD em `doi.org/<doi>`.
   USA REDE — chamar apenas sob flag explicita; em loops grandes,
   passar por cache externo.
"""

from __future__ import annotations

import re

# Padrao registry-prefix/suffix do DOI handle system (RFC ANSI/NISO Z39.84).
# Prefix: 10.NNNN (4+ digitos); suffix: ASCII com `-._;()/:` permitidos.
DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)


def is_doi_syntactically_valid(doi: str | None) -> bool:
    """Valida sintaxe do DOI conforme registro Handle.

    Returns:
        True se a string segue `10.NNNN/SUFFIX`, False caso contrario.
        `None`, vazio ou apenas whitespace -> False.
    """
    if not doi:
        return False
    return bool(DOI_RE.match(doi.strip()))


def is_doi_resolvable(doi: str, *, timeout: float = 5.0) -> bool:
    """Verifica se o DOI resolve via `doi.org` (consulta HEAD).

    USA REDE. Devolve `False` em qualquer erro de rede ou status >= 400.
    Para sintaxe invalida, sequer chama a rede.

    Esta funcao tem custo de I/O. Em loops grandes, envolva em cache
    externo (lru_cache + persistencia, por exemplo).
    """
    if not is_doi_syntactically_valid(doi):
        return False
    try:
        # Import local: httpx so eh exigido se esta funcao for chamada.
        import httpx

        resp = httpx.head(
            f"https://doi.org/{doi}",
            timeout=timeout,
            follow_redirects=True,
        )
        return resp.status_code < 400
    except Exception:  # noqa: BLE001 — qualquer falha de rede = nao resolvivel
        return False


def compute_doi_recall(
    cited: list[str],
    expected: list[str],
) -> float:
    """Recall de DOIs reais citados pela resposta.

    Conta DOIs em `expected` que aparecem em `cited` (case-insensitive)
    e estao sintaticamente validos.

    Returns:
        Recall em [0, 1]. Se `expected` esta vazio, retorna 1.0 (nada a
        recuperar = recall trivial).
    """
    if not expected:
        return 1.0
    cited_norm = {c.strip().lower() for c in cited if is_doi_syntactically_valid(c)}
    expected_norm = {e.strip().lower() for e in expected if is_doi_syntactically_valid(e)}
    if not expected_norm:
        return 1.0
    matched = cited_norm & expected_norm
    return len(matched) / len(expected_norm)
