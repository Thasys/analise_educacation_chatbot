"""Data Retrieval Agent — chama tools de dados via FastAPI gateway.

LLM: Haiku 4.5 (decisao de qual tool usar e parsing de args). As tools
executam HTTP, nao raciocinio — entao Haiku basta.

Por construcao, este agente NAO acessa DuckDB diretamente. Ele apenas
seleciona e dispara as 4 tools de `src/tools/data_tools.py`.
"""

from __future__ import annotations

from crewai import Agent

from src.agents._prompt_loader import load_prompt
from src.api_client import EduGatewayClient
from src.llm import make_llm
from src.tools import build_data_tools


def build_retriever(client: EduGatewayClient | None = None) -> Agent:
    """Cria o Data Retrieval Agent com as 4 tools de dados acopladas.

    Args:
        client: EduGatewayClient para uso compartilhado pelas tools.
            Em testes, passe um client com `httpx.MockTransport`. Em
            producao, deixe `None` para usar o default das settings.
    """
    return Agent(
        role="Recuperador de dados educacionais comparados",
        goal=(
            "Selecionar e invocar as tools de dados (catalog, timeseries, "
            "compare, ranking) para recuperar as observacoes necessarias "
            "para responder a pergunta do usuario, sem escrever SQL."
        ),
        backstory=load_prompt("retriever_system"),
        llm=make_llm("fast"),
        tools=build_data_tools(client=client),
        allow_delegation=False,
        verbose=False,
        max_iter=5,
    )
