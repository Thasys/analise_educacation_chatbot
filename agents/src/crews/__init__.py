"""Crews CrewAI do sistema de analise comparada.

- `core_crew` — Orchestrator + Profile & Intent (sempre roda).
- `analysis_crew` — Retriever + Statistician + Comparativist + Citation (Sprint 5.2-5.3).
- `synthesis_crew` — Visualizer + Synthesizer (Sprint 5.4).
"""

from src.crews.analysis_crew import run_analysis_flow
from src.crews.core_crew import build_core_crew, run_core_flow
from src.crews.master_flow import run_master
from src.crews.synthesis_crew import build_synthesis_crew, run_synthesis_flow

__all__ = [
    "build_core_crew",
    "build_synthesis_crew",
    "run_analysis_flow",
    "run_core_flow",
    "run_master",
    "run_synthesis_flow",
]
