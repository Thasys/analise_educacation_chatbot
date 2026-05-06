import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CitationPanel } from '@/components/citations/CitationPanel';
import { CitationCard } from '@/components/citations/CitationCard';
import type { Citation } from '@/types/domain';

const HANUSHEK: Citation = {
  doi: '10.1162/REST_a_00081',
  title: 'The Economics of International Differences in Educational Achievement',
  authors: ['Hanushek, Eric A.', 'Woessmann, Ludger'],
  year: 2011,
  journal: 'Economic Policy',
  snippet: 'Diferenças internacionais em desempenho explicam crescimento de longo prazo.',
  relevance_score: 0.85,
  source: 'nber',
};

const NO_DOI: Citation = {
  doi: null,
  title: 'Paper sem DOI',
  authors: ['Solo Author'],
  year: 2020,
  journal: null,
  snippet: null,
  relevance_score: null,
  source: null,
};

describe('CitationPanel', () => {
  it('returns null when no citations', () => {
    const { container } = render(<CitationPanel citations={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('shows count in header', () => {
    render(<CitationPanel citations={[HANUSHEK]} />);
    expect(screen.getByText(/Referências \(1\)/)).toBeInTheDocument();
  });

  it('renders one card per citation', () => {
    render(<CitationPanel citations={[HANUSHEK, NO_DOI]} />);
    expect(
      screen.getByText('The Economics of International Differences in Educational Achievement'),
    ).toBeInTheDocument();
    expect(screen.getByText('Paper sem DOI')).toBeInTheDocument();
  });

  it('uses custom title when provided', () => {
    render(<CitationPanel citations={[HANUSHEK]} title="Bibliografia" />);
    expect(screen.getByText(/Bibliografia \(1\)/)).toBeInTheDocument();
  });
});

describe('CitationCard', () => {
  it('shows external link to doi.org when DOI present', () => {
    render(<CitationCard citation={HANUSHEK} />);
    const link = screen.getByLabelText(/Abrir DOI/);
    expect(link).toHaveAttribute('href', 'https://doi.org/10.1162/REST_a_00081');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('omits external link when DOI is null', () => {
    render(<CitationCard citation={NO_DOI} />);
    expect(screen.queryByLabelText(/Abrir DOI/)).not.toBeInTheDocument();
  });

  it('formats two authors with &', () => {
    render(<CitationCard citation={HANUSHEK} />);
    expect(screen.getByText(/Hanushek.+&.+Woessmann/)).toBeInTheDocument();
  });

  it('formats single author without "&" or "et al."', () => {
    render(<CitationCard citation={NO_DOI} />);
    // "Solo Author (2020)"
    expect(screen.getByText(/Solo Author/)).toBeInTheDocument();
    expect(screen.queryByText(/et al\./)).not.toBeInTheDocument();
  });

  it('uses "et al." for 3+ authors', () => {
    render(
      <CitationCard
        citation={{
          ...NO_DOI,
          authors: ['First', 'Second', 'Third'],
        }}
      />,
    );
    expect(screen.getByText(/First et al\./)).toBeInTheDocument();
  });

  it('shows snippet when present', () => {
    render(<CitationCard citation={HANUSHEK} />);
    expect(screen.getByText(/Diferenças internacionais/)).toBeInTheDocument();
  });

  it('shows source and relevance percentage when both present', () => {
    render(<CitationCard citation={HANUSHEK} />);
    expect(screen.getByText(/nber/)).toBeInTheDocument();
    expect(screen.getByText(/relevância 85%/)).toBeInTheDocument();
  });
});
