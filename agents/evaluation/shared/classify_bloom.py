"""Classifica cada item factual/comparativo pela Taxonomia de Bloom
revisada (Anderson & Krathwohl, 2001).

Implementa a Acao #6 das orientacoes_metodologicas
(2026-05-21, Secao 2 — Validade de Conteudo).

Niveis utilizados (3 dos 6, suficientes para o conjunto atual):

- **remember**:  recall de fato unico ("Qual a nota PISA BR 2022?")
- **understand**: comparacao direta ou explicacao ("Compare BR e OCDE")
- **analyze**:    decomposicao / identificacao de relacoes / evolucao
                 temporal ("Compare a evolucao 2018 vs 2022")

Os niveis `apply`, `evaluate`, `create` nao aparecem no golden atual
— sao trabalho futuro quando o sistema lidar com perguntas mais
abertas.

Idempotente: detecta campo `bloom_level` ja presente e nao duplica.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


_ID_LINE = re.compile(r"^- id: ([FC]-\d+)\s*$")
_QUERY_LINE = re.compile(r'^\s*query:\s*["\']?(.+?)["\']?\s*$')
_HAS_BLOOM = re.compile(r"^\s*bloom_level:\s*\w+")
_BLANK_LINE = re.compile(r"^\s*$")


def _classify(query: str) -> str:
    """Heuristica simples baseada em palavras-chave da pergunta.

    Conservador: priorizar niveis menores em duvida (remember > understand
    > analyze) porque a maioria das perguntas factuais e simples recall.
    """
    q = query.lower()

    # Sinais de ANALYZE: evolucao, tendencia, multiplos paises/anos.
    if any(s in q for s in (
        "evolucao", "evoluc", "entre 2",
        "2018 e 2022", "2019 e 2022", "2020 e 2022",
        " vs ", "ao longo",
    )):
        return "analyze"

    # Sinais de UNDERSTAND: comparacao direta sem evolucao.
    if any(s in q for s in (
        "compare ", "comparar ", "comparacao", "qual a diferenca",
    )):
        return "understand"

    # Sinais de UNDERSTAND mais sutis: "media" com mais de 1 entidade.
    if "media ocde" in q and ("brasil" in q or "compare" in q):
        return "understand"

    # Default: remember (recall de fato).
    return "remember"


def classify_yaml(yaml_path: Path) -> int:
    """Insere `bloom_level` em cada item que ainda nao tem. Retorna
    quantidade de itens modificados."""
    lines = yaml_path.read_text(encoding="utf-8").splitlines(keepends=True)
    output: list[str] = []
    i = 0
    n_modified = 0
    while i < len(lines):
        m_id = _ID_LINE.match(lines[i])
        if not m_id:
            output.append(lines[i])
            i += 1
            continue
        block_start = i
        i += 1
        while i < len(lines) and not _ID_LINE.match(lines[i]):
            i += 1
        block = lines[block_start:i]
        if any(_HAS_BLOOM.match(b) for b in block):
            output.extend(block)
            continue
        query = ""
        for b in block:
            m = _QUERY_LINE.match(b)
            if m:
                query = m.group(1)
                break
        level = _classify(query)
        # Inserir bloom_level antes da ultima linha em branco do bloco.
        insert_at = len(block)
        for idx in range(len(block) - 1, -1, -1):
            if _BLANK_LINE.match(block[idx]):
                insert_at = idx
                # continua para achar a ultima
        new_block = list(block)
        if insert_at < len(new_block):
            new_block[insert_at:insert_at] = [f"  bloom_level: {level}\n"]
        else:
            new_block.append(f"  bloom_level: {level}\n")
        output.extend(new_block)
        n_modified += 1
    yaml_path.write_text("".join(output), encoding="utf-8")
    return n_modified


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    golden = repo_root / "evaluation" / "golden"
    total = 0
    for fname in ("queries_factuais.yaml", "queries_comparativas.yaml"):
        n = classify_yaml(golden / fname)
        print(f"{fname}: {n} itens classificados por Bloom")
        total += n
    print(f"Total: {total} itens.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
