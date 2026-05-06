import { create } from 'zustand';
import type { ProfileKind } from '@/types/domain';

interface ProfileState {
  /** Perfil detectado pelo Orchestrator (Fase 5) ou escolhido manualmente. */
  profile: ProfileKind;
  /** True se o perfil foi setado manualmente (override do detectado). */
  manualOverride: boolean;
  setProfile: (profile: ProfileKind, manual?: boolean) => void;
  reset: () => void;
}

const DEFAULT_PROFILE: ProfileKind = 'researcher';

export const useProfileStore = create<ProfileState>((set) => ({
  profile: DEFAULT_PROFILE,
  manualOverride: false,
  setProfile: (profile, manual = false) =>
    set((state) => {
      // Se ja teve override manual, nao sobrescrever via deteccao automatica
      if (state.manualOverride && !manual) return state;
      return { profile, manualOverride: manual || state.manualOverride };
    }),
  reset: () => set({ profile: DEFAULT_PROFILE, manualOverride: false }),
}));
