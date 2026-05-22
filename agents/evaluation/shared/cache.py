"""Cache sha256(query + mart_version + model) para resultados de
itens executados.

Implementa a Acao #8 das orientacoes_metodologicas
(2026-05-21, Secao 6 + 4.4): "Implementar cache sha256 no runner".

Funcionamento:
- Para cada item, computa hash determinístico de:
  * `query` do golden,
  * versao dos marts (`mart_version` — vem da config ou git hash do
    `dbt_project/models/marts/`),
  * `model` (smart + fast).
- Antes de chamar o pipeline real, consulta `cache/<hash>.json`.
- Se hit, retorna resultado em cache (com flag `_cache_hit: true`).
- Se miss, executa, salva no cache, retorna.

A invalidacao e automatica: qualquer mudanca em query, marts ou
modelo gera um hash novo, ignorando cache antigo. Cache antigos
ficam orfaos no disco — podem ser limpos via `make clean-cache`.

Especialmente eficaz para os 44 itens out_of_scope, que produzem
respostas estaveis ("fora do escopo") toda vez. Re-executar a
bateria entre commits pequenos consulta o cache em vez de gastar
tokens.
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


_CACHE_DIR_NAME = "cache"


def _git_hash_of(path: Path) -> str:
    """Retorna hash curto do git para `path` (HEAD). Fallback `unknown`
    se git nao disponivel ou path nao versionado."""
    try:
        out = subprocess.check_output(
            ["git", "log", "-1", "--format=%h", "--", str(path)],
            cwd=path if path.is_dir() else path.parent,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        ).strip()
        return out or "nogit"
    except Exception:  # noqa: BLE001
        return "nogit"


def mart_version(marts_dir: Path | None = None) -> str:
    """Versao logica dos marts. Hoje = git hash do diretorio dbt models/marts."""
    if marts_dir is None:
        # Default: <repo>/dbt_project/models/marts
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "dbt_project" / "models" / "marts"
            if candidate.exists():
                marts_dir = candidate
                break
    if marts_dir is None or not marts_dir.exists():
        return "noinfo"
    return _git_hash_of(marts_dir)


def cache_key(
    query: str,
    *,
    mode: str,
    model_smart: str,
    model_fast: str,
    marts_version: str | None = None,
) -> str:
    """Computa o hash determinístico que identifica unicamente um item."""
    parts = "|".join(
        [
            (query or "").strip(),
            mode,
            model_smart,
            model_fast,
            marts_version or mart_version(),
        ]
    )
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()[:16]


def cache_path(output_dir: Path, key: str) -> Path:
    return output_dir / _CACHE_DIR_NAME / f"{key}.json"


def get(output_dir: Path, key: str) -> dict | None:
    p = cache_path(output_dir, key)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("cache.get.decode_error", extra={"key": key})
        return None
    data["_cache_hit"] = True
    return data


def put(output_dir: Path, key: str, payload: dict) -> None:
    p = cache_path(output_dir, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload_to_save = {k: v for k, v in payload.items() if k != "_cache_hit"}
    p.write_text(json.dumps(payload_to_save, ensure_ascii=False), encoding="utf-8")
