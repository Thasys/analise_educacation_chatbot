'use client';

import { Database, Table2 } from 'lucide-react';
import { cn } from '@/lib/utils/cn';
import type { MartCatalogItem } from '@/lib/hooks/useCatalog';

interface MartCardProps {
  mart: MartCatalogItem;
  selected?: boolean;
  onClick?: () => void;
}

/**
 * Card clicavel de um mart Gold.
 *
 * Mostra nome (curto), descricao truncada, contagens e tags. Quando
 * `selected`, recebe estilo destacado (borda primary). Sem preview de
 * dados nesta sprint — o painel principal mostra detalhes ao clicar.
 */
export function MartCard({ mart, selected = false, onClick }: MartCardProps) {
  const shortName = mart.name.startsWith('mart_') ? mart.name.slice(5) : mart.name;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn(
        'flex w-full flex-col gap-2 rounded-md border bg-card/40 p-3 text-left transition-colors',
        selected
          ? 'border-primary bg-accent/30'
          : 'border-border hover:border-primary/50 hover:bg-accent/20',
      )}
    >
      <header className="flex items-start gap-2">
        <Database
          className={cn('mt-0.5 h-4 w-4 shrink-0', selected ? 'text-primary' : 'text-muted-foreground')}
          aria-hidden
        />
        <div className="min-w-0 flex-1">
          <p className="truncate font-mono text-xs font-medium text-foreground">{shortName}</p>
          {mart.description ? (
            <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
              {mart.description}
            </p>
          ) : null}
        </div>
      </header>

      <footer className="flex items-center gap-3 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1">
          <Table2 className="h-3 w-3" aria-hidden />
          {mart.row_count.toLocaleString('pt-BR')} linhas
        </span>
        <span>·</span>
        <span>{mart.column_count} cols</span>
        {mart.tags && mart.tags.length > 0 ? (
          <>
            <span>·</span>
            <span className="flex flex-wrap gap-1">
              {mart.tags.map((t) => (
                <span
                  key={t}
                  className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                >
                  {t}
                </span>
              ))}
            </span>
          </>
        ) : null}
      </footer>
    </button>
  );
}
