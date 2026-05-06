"""Tools CrewAI do sistema de analise comparada.

- `data_tools` — 4 tools que chamam o gateway HTTP (Sprint 5.2).
- `stats_tools` — Sprint 5.3.
- `rag_tools` — Sprint 5.5.
- `viz_tools` — Sprint 5.4.

A regra critica do CLAUDE.md ("agentes NAO escrevem SQL livre") e
arquiteturalmente honrada por todas as tools: nenhuma fala com DuckDB
direto, todas passam pelo `EduGatewayClient`.
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
    "compute_position",
    "compute_summary_stats",
    "make_plotly_bar_horizontal",
    "make_plotly_bar_vertical",
    "make_plotly_line_multi",
]
