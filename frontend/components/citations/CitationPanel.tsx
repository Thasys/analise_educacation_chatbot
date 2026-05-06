'use client';

import { BookMarked } from 'lucide-react';
import type { Citation } from '@/types/domain';
import { CitationCard } from '@/components/citations/CitationCard';

interface CitationPanelProps {
  citations: Citation[];
  /** Titulo opcional (default "Referências"). */
  title?: string;
}

export function CitationPanel({ citations, title = 'Referências' }: CitationPanelProps) {
  if (citations.length === 0) return null;

  return (
    <section className="space-y-2 rounded-md border border-border bg-card/30 p-3">
      <header className="flex items-center gap-2 text-xs">
        <BookMarked className="h-3.5 w-3.5 text-primary" aria-hidden />
        <span className="font-mono uppercase tracking-wide text-muted-foreground">
          {title} ({citations.length})
        </span>
      </header>
      <ul className="space-y-2">
        {citations.map((c, i) => (
          <li key={c.doi ?? `${c.title}-${i}`}>
            <CitationCard citation={c} />
          </li>
        ))}
      </ul>
    </section>
  );
}
