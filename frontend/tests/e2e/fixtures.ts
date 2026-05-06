import { test as base, type Route } from '@playwright/test';

/**
 * Fixtures customizadas para mockar os 2 backends:
 *   - api:8000  -> /api/data/catalog (TanStack Query do explorer)
 *   - agents:8001 -> /api/chat/stream (SSE do chat)
 *
 * Cada teste tipicamente declara o cenario chamando os helpers
 * `mockCatalog`, `mockChatStream`, etc, antes de navegar.
 */

export interface MockHelpers {
  mockCatalog: (response: unknown) => Promise<void>;
  mockChatStream: (sseText: string) => Promise<void>;
  mockCatalogError: (status: number) => Promise<void>;
}

export const test = base.extend<{ mocks: MockHelpers }>({
  // eslint-disable-next-line no-empty-pattern
  mocks: async ({ page }, use) => {
    const helpers: MockHelpers = {
      mockCatalog: async (response) => {
        await page.route('**/api/data/catalog', (route: Route) => {
          void route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(response),
          });
        });
      },
      mockCatalogError: async (status) => {
        await page.route('**/api/data/catalog', (route: Route) => {
          void route.fulfill({
            status,
            contentType: 'application/json',
            body: JSON.stringify({ detail: 'simulated error' }),
          });
        });
      },
      mockChatStream: async (sseText) => {
        await page.route('**/api/chat/stream', (route: Route) => {
          void route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            headers: {
              'Cache-Control': 'no-cache',
              'X-Accel-Buffering': 'no',
            },
            body: sseText,
          });
        });
      },
    };
    await use(helpers);
  },
});

export { expect } from '@playwright/test';

// ----------------------------------------------------------------------
// Fixtures de payload reutilizaveis
// ----------------------------------------------------------------------

export const SAMPLE_CATALOG = {
  data: [
    {
      name: 'mart_br_vs_ocde__gasto_educacao_timeseries',
      description: 'Gasto público em educação (% PIB) Brasil + 38 países OCDE.',
      schema_name: 'main_marts',
      row_count: 491,
      column_count: 18,
      tags: ['gold', 'gasto'],
    },
    {
      name: 'mart_alfabetizacao__latam_2020s',
      description: 'Taxa de alfabetização 15+ Brasil + LATAM, 2020-2024.',
      schema_name: 'main_marts',
      row_count: 38,
      column_count: 12,
      tags: ['gold', 'alfabetizacao'],
    },
    {
      name: 'mart_indicadores__rankings_recente',
      description: 'Rankings cross-indicador no ano mais recente.',
      schema_name: 'main_marts',
      row_count: 134,
      column_count: 10,
      tags: ['gold', 'rankings'],
    },
  ],
  meta: { total_rows: 3, query_ms: 27.5 },
};

export const SAMPLE_FINAL_ANSWER = {
  markdown:
    '# Gasto educacional 2020 — BR vs FIN\n\nO Brasil aplicou **5.77% do PIB** em educação (World Bank, 2020), 0.91 pp abaixo da Finlândia (6.68%).',
  profile_used: 'researcher',
  flow_used: 'data',
  sources_cited: ['worldbank'],
  visualizations: [
    {
      chart_type: 'bar_vertical',
      title: 'Gasto educacional 2020',
      plotly_figure: { data: [], layout: { title: { text: 'Gasto 2020' } } },
      sources: ['worldbank'],
      notes: ['Cobertura: BR + FIN'],
    },
  ],
  citations: [
    {
      doi: '10.1162/REST_a_00081',
      title: 'The Economics of International Differences in Educational Achievement',
      authors: ['Hanushek, Eric A.', 'Woessmann, Ludger'],
      year: 2011,
      journal: 'Economic Policy',
      snippet: 'Diferenças internacionais explicam crescimento de longo prazo.',
      relevance_score: 0.85,
      source: 'nber',
    },
  ],
  warnings: [],
  follow_up_suggestions: ['Como evoluiu o gasto BR entre 2010 e 2022?'],
};

export const CHAT_SSE_DATA_FLOW = [
  `event: flow_started\ndata: ${JSON.stringify({ type: 'flow_started', question: 'Como BR vs FIN em gasto educacional 2020?', ts: 1 })}\n\n`,
  `event: agent_started\ndata: ${JSON.stringify({ type: 'agent_started', agent: 'Core (Orchestrator + Profiler)', ts: 2 })}\n\n`,
  `event: agent_done\ndata: ${JSON.stringify({ type: 'agent_done', agent: 'Core (Orchestrator + Profiler)', result: { flow: 'data', profile: 'researcher' }, ts: 3 })}\n\n`,
  `event: agent_started\ndata: ${JSON.stringify({ type: 'agent_started', agent: 'Retriever', ts: 4 })}\n\n`,
  `event: agent_done\ndata: ${JSON.stringify({ type: 'agent_done', agent: 'Retriever', tool_calls: 1, ts: 5 })}\n\n`,
  `event: final_answer\ndata: ${JSON.stringify({ type: 'final_answer', elapsed_s: 5, payload: SAMPLE_FINAL_ANSWER })}\n\n`,
].join('');
