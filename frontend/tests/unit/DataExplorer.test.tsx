import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { DataExplorer } from '@/components/explorer/DataExplorer';
import type { CatalogResponse } from '@/lib/hooks/useCatalog';

const SAMPLE: CatalogResponse = {
  data: [
    {
      name: 'mart_br_vs_ocde__gasto_educacao_timeseries',
      description: 'Gasto público em educação (% PIB) Brasil + OCDE.',
      schema_name: 'main_marts',
      row_count: 491,
      column_count: 18,
      tags: ['gold', 'gasto'],
    },
    {
      name: 'mart_alfabetizacao__latam_2020s',
      description: 'Taxa de alfabetização 15+ Brasil + LATAM.',
      schema_name: 'main_marts',
      row_count: 38,
      column_count: 12,
      tags: ['gold', 'alfabetizacao'],
    },
  ],
  meta: { total_rows: 2 },
};

function makeClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0, staleTime: 0 } },
  });
}

function wrap(ui: ReactNode, client: QueryClient): JSX.Element {
  return <QueryClientProvider client={client}>{ui}</QueryClientProvider>;
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('DataExplorer', () => {
  it('shows loading state initially', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        () =>
          new Promise(() => {
            /* never resolves — keeps loading */
          }),
      ),
    );
    render(wrap(<DataExplorer />, makeClient()));
    expect(screen.getByLabelText('Carregando catálogo')).toBeInTheDocument();
  });

  it('renders mart list after fetch resolves', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify(SAMPLE), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
    render(wrap(<DataExplorer />, makeClient()));
    expect(
      await screen.findByText('br_vs_ocde__gasto_educacao_timeseries'),
    ).toBeInTheDocument();
    expect(screen.getByText('alfabetizacao__latam_2020s')).toBeInTheDocument();
    expect(screen.getByText('2 de 2 marts')).toBeInTheDocument();
  });

  it('filters marts by text input', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify(SAMPLE), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
    render(wrap(<DataExplorer />, makeClient()));
    await screen.findByText('br_vs_ocde__gasto_educacao_timeseries');
    const search = screen.getByLabelText('Buscar mart');
    fireEvent.change(search, { target: { value: 'alfab' } });
    await waitFor(() => {
      expect(
        screen.queryByText('br_vs_ocde__gasto_educacao_timeseries'),
      ).not.toBeInTheDocument();
    });
    expect(screen.getByText('alfabetizacao__latam_2020s')).toBeInTheDocument();
  });

  it('shows mart detail when card clicked', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify(SAMPLE), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
    render(wrap(<DataExplorer />, makeClient()));
    const card = await screen.findByText('br_vs_ocde__gasto_educacao_timeseries');
    fireEvent.click(card);
    // Detalhe mostra nome completo
    expect(
      screen.getByText('mart_br_vs_ocde__gasto_educacao_timeseries'),
    ).toBeInTheDocument();
    // Schema name aparece no detalhe
    expect(screen.getAllByText('main_marts').length).toBeGreaterThan(0);
  });

  it('renders error state on fetch failure with retry button', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: 'down' }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
    render(wrap(<DataExplorer />, makeClient()));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Tentar novamente')).toBeInTheDocument();
  });
});
