'use client';

import { QueryClient } from '@tanstack/react-query';

/**
 * QueryClient compartilhado pela app.
 *
 * Defaults pensados para o cenario academico (poucas consultas
 * concorrentes, dados Gold mudam raramente):
 *   - staleTime 5 min — catalog/preview podem ser cacheados.
 *   - retry 1 — fallback para erros transitorios.
 */
export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        gcTime: 30 * 60 * 1000,
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}
