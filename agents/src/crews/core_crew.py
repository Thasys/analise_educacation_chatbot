"""Core Crew — Orchestrator + Profile & Intent.

Sempre roda no inicio de qualquer pergunta. Saida combinada e a base
para escolher quais crews subsequentes ativar.

Em CrewAI 1.x usamos `Crew(agents, tasks, process=Process.sequential)`.
A primeira Task gera `IntentDecision` (Orchestrator), a segunda gera
`EntityExtraction` (Profiler) recebendo a pergunta original — as tarefas
sao independentes mas executadas em ordem para respeitar latencia.
"""

from __future__ import annotations

import structlog
from crewai import Crew, Process, Task

from src.agents import build_orchestrator, build_profiler
from src.crews._helpers import coerce_output
from src.schemas import (
    CoreFlowOutput,
    EntityExtraction,
    IntentDecision,
)


log = structlog.get_logger(__name__)


def _intent_task(question: str) -> Task:
    return Task(
        description=(
            "Analise a pergunta abaixo e classifique-a em um dos tres fluxos "
            "(simple/data/deep) e detecte o perfil do usuario "
            "(researcher/policy/student). Siga estritamente as regras do seu "
            "system prompt e retorne APENAS o JSON do schema IntentDecision.\n\n"
            f"Pergunta: \"{question}\""
        ),
        expected_output=(
            "Um JSON valido com os campos: flow, profile, reasoning, confidence."
        ),
        output_pydantic=IntentDecision,
        agent=build_orchestrator(),
    )


def _entities_task(question: str) -> Task:
    return Task(
        description=(
            "Extraia as entidades da pergunta abaixo (indicador, paises ISO-3, "
            "grouping, ano, janela temporal). Siga estritamente as regras do "
            "seu system prompt e retorne APENAS o JSON do schema "
            "EntityExtraction.\n\n"
            f"Pergunta: \"{question}\""
        ),
        expected_output=(
            "Um JSON valido com os campos: indicator, countries, grouping, "
            "year, year_start, year_end, reasoning."
        ),
        output_pydantic=EntityExtraction,
        agent=build_profiler(),
    )


def build_core_crew(question: str) -> Crew:
    """Monta a Core Crew para uma pergunta especifica.

    Em CrewAI 1.x, `Task.context` poderia encadear outputs, mas como as
    duas tasks sao independentes (ambas leem a pergunta original),
    `process=sequential` ja basta.
    """
    return Crew(
        agents=[build_orchestrator(), build_profiler()],
        tasks=[_intent_task(question), _entities_task(question)],
        process=Process.sequential,
        verbose=False,
    )


def run_core_flow(question: str) -> CoreFlowOutput:
    """Executa a Core Crew sobre a pergunta e devolve outputs tipados.

    Esta funcao e o ponto de entrada do master flow. Tests
    podem patchear `Crew.kickoff` para devolver respostas determinadas.
    """
    log.info("agents.core_crew.start", question=question[:160])
    crew = build_core_crew(question)
    crew.kickoff()
    intent_raw = crew.tasks[0].output.pydantic or crew.tasks[0].output.raw
    entities_raw = crew.tasks[1].output.pydantic or crew.tasks[1].output.raw
    intent = coerce_output(IntentDecision, intent_raw)
    entities = coerce_output(EntityExtraction, entities_raw)
    log.info(
        "agents.core_crew.done",
        flow=intent.flow,
        profile=intent.profile,
        confidence=intent.confidence,
        countries=entities.countries,
        indicator=entities.indicator,
    )
    return CoreFlowOutput(intent=intent, entities=entities, question=question)
