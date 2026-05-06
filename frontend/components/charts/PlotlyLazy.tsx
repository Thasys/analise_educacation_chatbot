'use client';

import { useEffect, useRef, useState, type ComponentType } from 'react';

/**
 * Wrapper que carrega `plotly.js-basic-dist-min` + `react-plotly.js`
 * lazy via dynamic import.
 *
 * Por que nao `next/dynamic` direto?
 *   - `react-plotly.js` exporta default que precisa receber a instancia
 *     de Plotly via factory. Compoe-los em runtime evita carregar o
 *     plotly.js completo (~3 MB) — ficamos com basic-dist-min (~840 KB)
 *     em chunk separado.
 *   - `next/dynamic` com loader async funciona, mas mantemos controle
 *     explicito para cache + SSR-skip.
 *
 * O componente carregado eh cacheado em modulo (singleton); chamadas
 * subsequentes nao re-baixam o JS.
 */

interface PlotlyData {
  data: unknown[];
  layout: Record<string, unknown>;
}

interface PlotProps {
  data: unknown[];
  layout: Record<string, unknown>;
  config?: Record<string, unknown>;
  style?: React.CSSProperties;
  className?: string;
  useResizeHandler?: boolean;
}

interface PlotlyLazyProps {
  figure: PlotlyData;
  config?: Record<string, unknown>;
  style?: React.CSSProperties;
  className?: string;
}

let cachedComponent: ComponentType<PlotProps> | null = null;
let loadPromise: Promise<ComponentType<PlotProps>> | null = null;

async function loadPlotComponent(): Promise<ComponentType<PlotProps>> {
  if (cachedComponent) return cachedComponent;
  if (loadPromise) return loadPromise;
  loadPromise = (async () => {
    // @ts-expect-error - plotly.js-basic-dist-min nao tem tipos oficiais
    const Plotly = (await import('plotly.js-basic-dist-min')).default;
    const createPlotComponent = (await import('react-plotly.js/factory')).default;
    const Component = createPlotComponent(Plotly) as ComponentType<PlotProps>;
    cachedComponent = Component;
    return Component;
  })();
  return loadPromise;
}

export function PlotlyLazy(props: PlotlyLazyProps) {
  const { figure, config, style, className } = props;
  const [Component, setComponent] = useState<ComponentType<PlotProps> | null>(cachedComponent);
  const [loadError, setLoadError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    if (!Component) {
      loadPlotComponent()
        .then((C) => {
          if (mountedRef.current) setComponent(() => C);
        })
        .catch((err: unknown) => {
          if (mountedRef.current) {
            setLoadError(err instanceof Error ? err.message : String(err));
          }
        });
    }
    return () => {
      mountedRef.current = false;
    };
  }, [Component]);

  if (loadError) {
    return (
      <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
        Falha ao carregar Plotly: {loadError}
      </div>
    );
  }

  if (!Component) {
    return (
      <div
        className="flex h-64 items-center justify-center rounded-md border border-dashed border-border bg-card/30 text-xs text-muted-foreground"
        role="status"
        aria-label="Carregando gráfico"
      >
        Carregando gráfico…
      </div>
    );
  }

  return (
    <Component
      data={figure.data}
      layout={{
        // Defaults sobreponiveis pelo `figure.layout` espelhando paleta dark
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: '#cbd5e1', size: 12 },
        ...figure.layout,
      }}
      config={{
        responsive: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d'],
        ...config,
      }}
      useResizeHandler
      className={className}
      style={{ width: '100%', height: '320px', ...style }}
    />
  );
}
