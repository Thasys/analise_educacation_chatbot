import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MartCard } from '@/components/explorer/MartCard';
import type { MartCatalogItem } from '@/lib/hooks/useCatalog';

const SAMPLE: MartCatalogItem = {
  name: 'mart_br_vs_ocde__gasto_educacao_timeseries',
  description: 'Gasto público em educação (% PIB) para Brasil + 38 países OCDE.',
  schema_name: 'main_marts',
  row_count: 491,
  column_count: 18,
  tags: ['gold', 'gasto'],
};

describe('MartCard', () => {
  it('shows truncated name (without mart_ prefix)', () => {
    render(<MartCard mart={SAMPLE} />);
    expect(screen.getByText('br_vs_ocde__gasto_educacao_timeseries')).toBeInTheDocument();
  });

  it('shows description truncated', () => {
    render(<MartCard mart={SAMPLE} />);
    expect(screen.getByText(/Gasto público em educação/)).toBeInTheDocument();
  });

  it('shows row count formatted in pt-BR', () => {
    render(<MartCard mart={SAMPLE} />);
    expect(screen.getByText(/491 linhas/)).toBeInTheDocument();
  });

  it('renders all tags', () => {
    render(<MartCard mart={SAMPLE} />);
    expect(screen.getByText('gold')).toBeInTheDocument();
    expect(screen.getByText('gasto')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<MartCard mart={SAMPLE} onClick={onClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('reflects selected state via aria-pressed', () => {
    const { rerender } = render(<MartCard mart={SAMPLE} selected={false} />);
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'false');
    rerender(<MartCard mart={SAMPLE} selected={true} />);
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'true');
  });
});
