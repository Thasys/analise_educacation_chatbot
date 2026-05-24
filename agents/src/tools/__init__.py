"""Tools CrewAI do sistema de analise comparada.

- `data_tools` — 4 tools que chamam o gateway HTTP (catalog, timeseries,
  compare, ranking).
- `stats_tools` — calculo deterministico de estatisticas descritivas.
- `rag_tools` — busca semantica no ChromaDB + resolucao de DOI.
- `viz_tools` — geracao de figure dicts Plotly parametricos.

Regra arquitetural: nenhuma tool fala com DuckDB direto; todas passam
pelo `EduGatewayClient`. Ver `docs/architecture/agents.md` para detalhes.
"""

from src.tools.data_tools import (
    DataCatalogTool,
    DataCompareTool,
    DataRankingTool,
    DataTimeseriesTool,
    build_data_tools,
)
from src.tools.stats_tools import (
    ComputeStatsTool,
    compute_divergence,
    compute_position,
    compute_summary_stats,
)
from src.tools.rag_tools import CiteResolveTool, RAGSearchTool, build_rag_tools
from src.tools.viz_tools import (
    MakePlotlySpecTool,
    make_plotly_bar_horizontal,
    make_plotly_bar_vertical,
    make_plotly_line_multi,
)

__all__ = [
    "CiteResolveTool",
    "ComputeStatsTool",
    "DataCatalogTool",
    "DataCompareTool",
    "DataRankingTool",
    "DataTimeseriesTool",
    "MakePlotlySpecTool",
    "RAGSearchTool",
    "build_data_tools",
    "build_rag_tools",
    "compute_divergence",
    "compute_position",
    "compute_summary_stats",
    "make_plotly_bar_horizontal",
    "make_plotly_bar_vertical",
    "make_plotly_line_multi",
]
