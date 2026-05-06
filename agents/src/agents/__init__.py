"""Agentes CrewAI do sistema de analise comparada.

Cada modulo expoe uma factory `build_<nome>()` que retorna uma instancia
de `crewai.Agent` ja configurada com role, goal, backstory (carregado de
prompts/) e LLM apropriado.
"""

from src.agents.citation import build_citation
from src.agents.comparativist import build_comparativist
from src.agents.orchestrator import build_orchestrator
from src.agents.profiler import build_profiler
from src.agents.retriever import build_retriever
from src.agents.statistician import build_statistician
from src.agents.synthesizer import build_synthesizer
from src.agents.visualizer import build_visualizer

__all__ = [
    "build_citation",
    "build_comparativist",
    "build_orchestrator",
    "build_profiler",
    "build_retriever",
    "build_statistician",
    "build_synthesizer",
    "build_visualizer",
]
