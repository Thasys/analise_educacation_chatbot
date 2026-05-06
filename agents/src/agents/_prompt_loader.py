"""Carrega prompts versionados em src/prompts/*.txt."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    """Le `prompts/<name>.txt` (UTF-8). Cacheado por nome."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt nao encontrado: {path}. Verifique src/prompts/."
        )
    return path.read_text(encoding="utf-8").strip()
