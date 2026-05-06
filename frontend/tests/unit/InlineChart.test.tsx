import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InlineChart } from '@/components/charts/InlineChart';
import type { VizSpec } from '@/types/domain';

// PlotlyLazy faz dynamic import do plotly.js — mock para nao tentar
// carregar o pacote real em happy-dom.
vi.mock('@/components/charts/PlotlyLazy', () => ({
  PlotlyLazy: ({ figure }: { figure: { data: unknown[]; layout: Record<string, unknown> } }) => (
    <div data-testid="plotly-mock" data-points={figure.data.length} />
  ),
}));

const SAMPLE_VIZ: VizSpec = {
  chart_type: 'bar_vertical',
  title: 'Gasto educacional 2020',
  plotly_figure: {
    data: [{ type: 'bar', x: ['BRA', 'FIN'], y: [5.77, 6.68] }],
    layout: { title: { text: 'Gasto 2020' } },
  },
  sources: ['worldbank'],
  notes: ['Cobertura: 2 paises'],
};

describe('InlineChart', () => {
  it('renders title, sources and notes', () => {
    render(<InlineChart spec={SAMPLE_VIZ} />);
    expect(screen.getByText('Gasto educacional 2020')).toBeInTheDocument();
    expect(screen.getByText(/worldbank/)).toBeInTheDocument();
    expect(screen.getByText(/Cobertura: 2 paises/)).toBeInTheDocument();
  });

  it('renders the lazy Plotly component when data is non-empty', () => {
    render(<InlineChart spec={SAMPLE_VIZ} />);
    expect(screen.getByTestId('plotly-mock')).toBeInTheDocument();
  });

  it('returns null when chart_type is "none"', () => {
    const { container } = render(
      <InlineChart
        spec={{
          chart_type: 'none',
          title: 'x',
          plotly_figure: { data: [], layout: {} },
          sources: [],
          notes: [],
        }}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows empty state when figure has no data points', () => {
    render(
      <InlineChart
        spec={{
          chart_type: 'bar_vertical',
          title: 'Vazio',
          plotly_figure: { data: [], layout: {} },
          sources: [],
          notes: [],
        }}
      />,
    );
    expect(screen.getByText(/Sem dados para o gráfico/)).toBeInTheDocument();
  });
});
