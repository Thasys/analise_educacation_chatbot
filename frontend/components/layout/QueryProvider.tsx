'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { makeQueryClient } from '@/lib/query-client';

export function QueryProvider({ children }: { children: ReactNode }) {
  // useState evita criar um novo client em cada render no lado client.
  const [client] = useState(() => makeQueryClient());
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
