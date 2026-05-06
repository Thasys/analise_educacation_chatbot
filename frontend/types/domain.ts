/**
 * Tipos de dominio espelhados de `agents/src/schemas.py` (Fase 5).
 *
 * Quando o endpoint /api/chat/stream estabilizar (Sprint 6.1), estes
 * tipos serao gerados automaticamente via `openapi-typescript`. Por
 * enquanto sao manuais — sincronizar com schemas.py em caso de mudanca.
 */

// -- Tipos canonicos --------------------------------------------------

export type IndicatorId = 'GASTO_EDU_PIB' | 'LITERACY_15M';

export type SourceTag =
  | 'worldbank'
  | 'unesco'
  | 'oecd'
  | 'eurostat'
  | 'ipea'
  | 'cepalstat';

export type GroupingTag =
  | 'oecd'
  | 'oecd_g7'
  | 'latam_oecd'
  | 'latam'
  | 'brics'
  | 'asia'
  | 'africa_mena'
  | 'europe_other';

export type FlowKind = 'simple' | 'data' | 'deep';
export type ProfileKind = 'researcher' | 'policy' | 'student';

export type ChartType =
  | 'bar_horizontal'
  | 'bar_vertical'
  | 'line_multi'
  | 'scatter'
  | 'none';

// -- Decisoes da Core Crew --------------------------------------------

export interface IntentDecision {
  flow: FlowKind;
  profile: ProfileKind;
  reasoning: string;
  confidence: number;
}

export interface EntityExtraction {
  indicator: IndicatorId | null;
  countries: string[];
  grouping: GroupingTag | null;
  year: number | null;
  year_start: number | null;
  year_end: number | null;
  reasoning: string;
}

// -- Visualizacoes ----------------------------------------------------

/**
 * Plotly figure dict — passado direto para react-plotly.js.
 * Nao validamos shape porque @types/plotly.js cobre.
 */
export interface PlotlyFigure {
  data: unknown[];
  layout: Record<string, unknown>;
}

export interface VizSpec {
  chart_type: ChartType;
  title: string;
  plotly_figure: PlotlyFigure;
  sources: string[];
  notes: string[];
}

// -- Citations --------------------------------------------------------

export interface Citation {
  doi: string | null;
  title: string;
  authors: string[];
  year: number | null;
  journal: string | null;
  snippet: string | null;
  relevance_score: number | null;
  source: string | null;
}

// -- Resposta final ---------------------------------------------------

export interface FinalAnswer {
  markdown: string;
  profile_used: ProfileKind;
  flow_used: FlowKind;
  sources_cited: string[];
  visualizations: VizSpec[];
  citations: Citation[];
  warnings: string[];
  follow_up_suggestions: string[];
}

// -- Eventos de streaming SSE (Sprint 6.1+) ---------------------------

export type StreamEvent =
  | { type: 'flow_started'; question: string; ts: number }
  | { type: 'agent_started'; agent: string; ts: number }
  | {
      type: 'agent_done';
      agent: string;
      ts: number;
      result?: Record<string, unknown>;
      tool_calls?: number;
      method?: string;
      sample_size?: number;
      items?: number;
      chart_type?: string;
    }
  | { type: 'tool_called'; tool: string; args: Record<string, unknown>; ts: number }
  | { type: 'partial_markdown'; chunk: string; ts: number }
  | { type: 'final_answer'; payload: FinalAnswer }
  | { type: 'error'; error: string; ts: number };
