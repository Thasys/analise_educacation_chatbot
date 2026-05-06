'use client';

import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/api-client';

export interface MartCatalogItem {
  name: string;
  description: string | null;
  schema_name: string;
  row_count: number;
  column_count: number;
  tags: string[] | null;
}

export interface CatalogResponse {
  data: MartCatalogItem[];
  meta: {
    total_rows: number;
    query_ms?: number | null;
    sources?: string[] | null;
    notes?: string[] | null;
  };
}

/**
 * Consulta `/api/data/catalog` (gateway FastAPI da Fase 4).
 *
 * Cache 5 min (configurado globalmente em `makeQueryClient`).
 * Retry 1 vez em erro transitorio.
 */
export function useCatalog() {
  return useQuery<CatalogResponse>({
    queryKey: ['catalog'],
    queryFn: () => apiGet<CatalogResponse>('/api/data/catalog'),
  });
}
