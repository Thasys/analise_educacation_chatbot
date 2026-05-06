'use client';

import { ExternalLink } from 'lucide-react';
import type { Citation } from '@/types/domain';

interface CitationCardProps {
  citation: Citation;
}

/**
 * Cartao individual de uma referencia bibliografica.
 *
 * Se DOI presente, link clicavel para doi.org abre em nova aba.
 * Snippet do RAG aparece como blockquote curto (max 200 chars
 * conforme regra do Citation Agent na Fase 5).
 */
export function CitationCard({ citation }: CitationCardProps) {
  const authorsText = formatAuthors(citation.authors);
  const yearText = citation.year ? ` (${citation.year})` : '';
  const journalText = citation.journal ? `. ${citation.journal}` : '';

  return (
    <article className="space-y-1.5 rounded-md border border-border bg-card/40 p-3 text-xs">
      <header className="flex items-start justify-between gap-2">
        <div className="space-y-0.5">
          <p className="font-medium leading-snug text-foreground">{citation.title}</p>
          <p className="text-[11px] text-muted-foreground">
            {authorsText}
            {yearText}
            {journalText}
          </p>
        </div>
        {citation.doi ? (
          <a
            href={`https://doi.org/${citation.doi}`}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded p-1 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            aria-label={`Abrir DOI ${citation.doi} em nova aba`}
            title={`doi.org/${citation.doi}`}
          >
            <ExternalLink className="h-3.5 w-3.5" aria-hidden />
          </a>
        ) : null}
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

function formatAuthors(authors: string[]): string {
  if (authors.length === 0) return 'Autor(es) não informado(s)';
  if (authors.length === 1) return authors[0] ?? '';
  if (authors.length === 2) return `${authors[0]} & ${authors[1]}`;
  return `${authors[0]} et al.`;
}
