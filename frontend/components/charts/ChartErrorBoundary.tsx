'use client';

import { Component, type ReactNode, type ErrorInfo } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
  children: ReactNode;
  /** Mensagem fallback opcional (default: "Falha ao renderizar gráfico"). */
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * ErrorBoundary local para isolar falhas do Plotly (layout invalido,
 * data malformatada). Sem ele, um erro de render derruba a bolha
 * inteira do MessageBubble. Com, mostra fallback compacto e o resto
 * da resposta (markdown, citacoes, fontes) continua visivel.
 *
 * React 18 nao oferece error boundaries em hooks; precisa ser classe.
 */
export class ChartErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (typeof console !== 'undefined') {
      console.error('[ChartErrorBoundary]', error, info.componentStack);
    }
  }

  render(): ReactNode {
    if (this.state.hasError) {
      const { fallbackTitle = 'Falha ao renderizar gráfico' } = this.props;
      return (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-300"
        >
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
          <div>
            <p className="font-medium">{fallbackTitle}</p>
            {this.state.error ? (
              <p className="mt-1 font-mono text-[11px] opacity-80">{this.state.error.message}</p>
            ) : null}
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
