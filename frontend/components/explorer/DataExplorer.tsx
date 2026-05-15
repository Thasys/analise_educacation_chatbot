'use client';

import { useMemo, useState } from 'react';
import { AlertCircle, Database, Loader2, Search, X } from 'lucide-react';
import { useCatalog, type MartCatalogItem } from '@/lib/hooks/useCatalog';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { MartCard } from '@/components/explorer/MartCard';
import { cn } from '@/lib/utils/cn';

/**
 * Pagina de exploracao dos marts Gold.
 *
 * Layout: lista (esquerda) + detalhe (direita) dentro do Workspace.
 * Funcional com filtro por tag/texto. Preview de linhas
 * (`/api/data/:dataset/preview`) ainda nao implementado no gateway.
 */
export function DataExplorer() {
  const { data, isLoading, isError, error, refetch } = useCatalog();
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [filter, setFilter] = useState('');
  const [tagFilter, setTagFilter] = useState<string | null>(null);

  // Memoizamos `marts` para que o array literal `[]` (caso `data` seja undefined)
  // nao re-disparem `useMemo` de allTags/filtered a cada render.
  const marts = useMemo<MartCatalogItem[]>(() => data?.data ?? [], [data]);
  const allTags = useMemo(() => {
    const set = new Set<string>();
    for (const m of marts) {
      for (const t of m.tags ?? []) set.add(t);
    }
    return Array.from(set).sort();
  }, [marts]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return marts.filter((m) => {
      const matchesText =
        !q ||
        m.name.toLowerCase().includes(q) ||
        (m.description ?? '').toLowerCase().includes(q);
      const matchesTag = !tagFilter || (m.tags ?? []).includes(tagFilter);
      return matchesText && matchesTag;
    });
  }, [marts, filter, tagFilter]);

  const selected = selectedName
    ? marts.find((m) => m.name === selectedName) ?? null
    : null;

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-border px-6 py-4">
        <h1 className="text-lg font-semibold">Explorador de marts Gold</h1>
        <p className="text-xs text-muted-foreground">
          Datasets analíticos publicados pela camada Gold (DuckDB · dbt). Clique para ver detalhes.
        </p>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Lista esquerda */}
        <section
          aria-label="Lista de marts"
          className="flex w-[420px] flex-col gap-3 overflow-y-auto border-r border-border bg-card/20 p-4"
        >
          <FilterBar
            filter={filter}
            onFilterChange={setFilter}
            tags={allTags}
            tagFilter={tagFilter}
            onTagFilterChange={setTagFilter}
          />

          {isLoading ? (
            <LoadingState />
          ) : isError ? (
            <ErrorState
              error={error instanceof Error ? error.message : String(error)}
              onRetry={() => void refetch()}
            />
          ) : filtered.length === 0 ? (
            <EmptyFilterState />
          ) : (
            <ul className="space-y-2">
              {filtered.map((mart) => (
                <li key={mart.name}>
                  <MartCard
                    mart={mart}
                    selected={selectedName === mart.name}
                    onClick={() => setSelectedName(mart.name)}
                  />
                </li>
              ))}
            </ul>
          )}

          {!isLoading && !isError && marts.length > 0 ? (
            <p className="px-1 pt-2 text-[11px] text-muted-foreground">
              {filtered.length} de {marts.length} marts
            </p>
          ) : null}
        </section>

        {/* Detalhe direita */}
        <section
          aria-label="Detalhe do mart selecionado"
          className="flex flex-1 flex-col overflow-y-auto p-6"
        >
          {selected ? <MartDetail mart={selected} /> : <NoSelectionState />}
        </section>
      </div>
    </div>
  );
}

// ----------------------------------------------------------------------
// Subcomponentes
// ----------------------------------------------------------------------

function FilterBar({
  filter,
  onFilterChange,
  tags,
  tagFilter,
  onTagFilterChange,
}: {
  filter: string;
  onFilterChange: (v: string) => void;
  tags: string[];
  tagFilter: string | null;
  onTagFilterChange: (t: string | null) => void;
}) {
  return (
    <div className="space-y-2">
      <div className="relative">
        <Search
          className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground"
          aria-hidden
        />
        <input
          type="search"
          value={filter}
          onChange={(e) => onFilterChange(e.target.value)}
          placeholder="Buscar mart por nome ou descrição..."
          aria-label="Buscar mart"
          className="w-full rounded-md border border-input bg-background py-1.5 pl-7 pr-2 text-xs placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        />
      </div>
      {tags.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => onTagFilterChange(null)}
            className={cn(
              'rounded px-2 py-0.5 font-mono text-[10px] transition-colors',
              tagFilter === null
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground hover:bg-accent',
            )}
          >
            todos
          </button>
          {tags.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => onTagFilterChange(t === tagFilter ? null : t)}
              className={cn(
                'rounded px-2 py-0.5 font-mono text-[10px] transition-colors',
                tagFilter === t
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-accent',
              )}
            >
              {t}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function MartDetail({ mart }: { mart: MartCatalogItem }) {
  return (
    <div className="mx-auto w-full max-w-2xl space-y-4">
      <header>
        <p className="font-mono text-xs text-muted-foreground">{mart.schema_name}</p>
        <h2 className="text-xl font-semibold">{mart.name}</h2>
      </header>

      {mart.description ? (
        <p className="text-sm leading-relaxed text-foreground">{mart.description}</p>
      ) : null}

      <div className="grid grid-cols-3 gap-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] uppercase">Linhas</CardDescription>
            <CardTitle className="text-2xl">
              {mart.row_count.toLocaleString('pt-BR')}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] uppercase">Colunas</CardDescription>
            <CardTitle className="text-2xl">{mart.column_count}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription className="text-[10px] uppercase">Tags</CardDescription>
            <CardContent className="px-0 pb-0 pt-1">
              <div className="flex flex-wrap gap-1">
                {(mart.tags ?? []).map((t) => (
                  <span
                    key={t}
                    className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                  >
                    {t}
                  </span>
                ))}
                {(mart.tags ?? []).length === 0 ? (
                  <span className="text-xs text-muted-foreground">—</span>
                ) : null}
              </div>
            </CardContent>
          </CardHeader>
        </Card>
      </div>

      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-sm">Preview de linhas</CardTitle>
          <CardDescription className="text-xs">
            Endpoint <code className="font-mono">/api/data/{mart.name}/preview</code> ainda não foi
            implementado no gateway. Adicionar endpoint de amostra de 100 linhas e ligar aqui.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}

function NoSelectionState() {
  return (
    <div className="flex flex-1 items-center justify-center">
      <Card className="max-w-md border-dashed">
        <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
          <Database className="h-8 w-8 text-muted-foreground" aria-hidden />
          <p className="text-sm text-muted-foreground">
            Selecione um mart à esquerda para ver detalhes (descrição, contagens, tags).
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function LoadingState() {
  return (
    <div
      className="flex items-center justify-center rounded-md border border-dashed border-border p-8 text-xs text-muted-foreground"
      role="status"
      aria-label="Carregando catálogo"
    >
      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden />
      Carregando catálogo…
    </div>
  );
}

function ErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="flex-1">
        <p className="font-medium">Falha ao carregar o catálogo</p>
        <p className="mt-1 font-mono text-[11px]">{error}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded border border-destructive/40 px-2 py-1 text-[11px] hover:bg-destructive/20"
        >
          Tentar novamente
        </button>
      </div>
    </div>
  );
}

function EmptyFilterState() {
  return (
    <p className="rounded-md border border-dashed border-border p-4 text-xs text-muted-foreground">
      Nenhum mart bate com o filtro. <X className="inline h-3 w-3" /> limpe os filtros acima.
    </p>
  );
}
