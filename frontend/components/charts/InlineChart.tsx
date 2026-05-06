'use client';

import { PlotlyLazy } from '@/components/charts/PlotlyLazy';
import type { VizSpec } from '@/types/domain';

interface InlineChartProps {
  spec: VizSpec;
}

/**
 * Renderiza uma VizSpec vinda do FinalAnswer.
 *
 * Casos especiais:
 *   - `chart_type === 'none'`: retorna null (fluxo simple sem viz).
 *   - `data === []`: mostra estado vazio.
 *
 * O Plotly figure dict eh validado apenas por estrutura minima (data
 * array + layout dict); confiamos no servidor (Visualizer Agent na
 * Fase 5) para producao consistente.
 */
export function InlineChart({ spec }: InlineChartProps) {
  if (spec.chart_type === 'none') return null;

  const figure = spec.plotly_figure;
  const isEmpty =
    !figure ||
    !Array.isArray(figure.data) ||
    figure.data.length === 0;

  return (
    <figure className="space-y-2 rounded-md border border-border bg-card/40 p-3">
      <figcaption className="text-xs">
        <p className="font-medium text-foreground">{spec.title}</p>
        {spec.sources.length > 0 ? (
          <p className="font-mono text-[11px] text-muted-foreground">
            Fonte: {spec.sources.join(', ')}
          </p>
        ) : null}
      </figcaption>

      {isEmpty ? (
        <div className="flex h-48 items-center justify-center rounded-md border border-dashed border-border text-xs text-muted-foreground">
          Sem dados para o gráfico.
        </div>
      ) : (
        <PlotlyLazy figure={figure} />
      )}

      {spec.notes.length > 0 ? (
        <ul className="space-y-0.5 text-[11px] text-muted-foreground">
          {spec.notes.map((n, i) => (
            <li key={i}>· {n}</li>
          ))}
        </ul>
      ) : null}
    </figure>
  );
}
