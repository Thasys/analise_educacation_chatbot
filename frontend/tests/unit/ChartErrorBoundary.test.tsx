import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChartErrorBoundary } from '@/components/charts/ChartErrorBoundary';

function Boom(): never {
  throw new Error('plotly layout invalid');
}

// Silenciar console.error que React emite quando boundary captura.
beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {});
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe('ChartErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(
      <ChartErrorBoundary>
        <p>conteúdo normal</p>
      </ChartErrorBoundary>,
    );
    expect(screen.getByText('conteúdo normal')).toBeInTheDocument();
  });

  it('renders fallback when child throws', () => {
    render(
      <ChartErrorBoundary>
        <Boom />
      </ChartErrorBoundary>,
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Falha ao renderizar gráfico')).toBeInTheDocument();
    expect(screen.getByText(/plotly layout invalid/)).toBeInTheDocument();
  });

  it('uses custom fallback title when provided', () => {
    render(
      <ChartErrorBoundary fallbackTitle="Gráfico indisponível">
        <Boom />
      </ChartErrorBoundary>,
    );
    expect(screen.getByText('Gráfico indisponível')).toBeInTheDocument();
  });
});
