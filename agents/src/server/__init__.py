"""Mini FastAPI server do servico de agentes.

Expoe `POST /api/chat/stream` em :8001 (default) que executa
`run_master` em background e emite Server-Sent Events com progresso por
agente + FinalAnswer estruturado no fim.

Por que separar do `api/` (que serve dados em :8000)?
  - `api/` venv tem ~200 MB; instalar CrewAI + Anthropic + ChromaDB
    nele subiria para ~1.9 GB.
  - Separacao fisica respeita a fronteira logica entre dados (Gold)
    e raciocinio (LLM).
  - Caddy reverse proxy em producao roteia `/api/chat/*` -> :8001
    para single origin no frontend.
"""

from src.server.main import app

__all__ = ["app"]
