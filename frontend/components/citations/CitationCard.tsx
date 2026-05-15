'use client';

import type { Citation } from '@/types/domain';
import { DoiLink } from '@/components/citations/DoiLink';
import { formatCitationMeta } from '@/lib/utils/citation';

interface CitationCardProps {
  citation: Citation;
}

/**
 * Cartao individual de uma referencia bibliografica.
 *
 * Se DOI presente, link clicavel para doi.org abre em nova aba (via
 * `DoiLink`). Snippet do RAG aparece como blockquote curto (max 200
 * chars conforme regra do Citation Agent na Fase 5).
 */
export function CitationCard({ citation }: CitationCardProps) {
  const meta = formatCitationMeta(citation, { mode: 'full' });

  return (
    <article className="space-y-1.5 rounded-md border border-border bg-card/40 p-3 text-xs">
      <header className="flex items-start justify-between gap-2">
        <div className="space-y-0.5">
          <p className="font-medium leading-snug text-foreground">{citation.title}</p>
          <p className="text-[11px] text-muted-foreground">{meta}</p>
        </div>
        {citation.doi ? <DoiLink doi={citation.doi} variant="icon" /> : null}
      </header>

      {citation.snippet ? (
        <blockquote className="border-l-2 border-primary/40 pl-2 text-[11px] italic text-muted-foreground">
          {citation.snippet}
        </blockquote>
      ) : null}

      {citation.source || citation.relevance_score !== null ? (
        <div className="flex items-center gap-2 text-[10px] font-mono text-muted-foreground">
          {citation.source ? <span>{citation.source}</span> : null}
          {citation.relevance_score !== null && citation.relevance_score !== undefined ? (
            <span>· relevância {(citation.relevance_score * 100).toFixed(0)}%</span>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
