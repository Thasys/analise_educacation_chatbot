'use client';

import { useEffect } from 'react';
import { useProfileStore } from '@/lib/stores/profileStore';

/**
 * Componente client-side que aplica `data-profile="<perfil>"` no <html>
 * para que os tokens CSS de cada perfil tomem efeito (ver globals.css).
 */
export function ProfileTheme() {
  const profile = useProfileStore((s) => s.profile);
  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.dataset.profile = profile;
    }
  }, [profile]);
  return null;
}
