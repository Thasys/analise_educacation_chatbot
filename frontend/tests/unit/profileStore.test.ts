import { beforeEach, describe, expect, it } from 'vitest';
import { useProfileStore } from '@/lib/stores/profileStore';

describe('profileStore', () => {
  beforeEach(() => {
    useProfileStore.getState().reset();
  });

  it('starts with researcher as default', () => {
    expect(useProfileStore.getState().profile).toBe('researcher');
    expect(useProfileStore.getState().manualOverride).toBe(false);
  });

  it('detects automatically when no manual override', () => {
    useProfileStore.getState().setProfile('policy');
    expect(useProfileStore.getState().profile).toBe('policy');
    expect(useProfileStore.getState().manualOverride).toBe(false);
  });

  it('locks after manual override', () => {
    useProfileStore.getState().setProfile('student', true);
    expect(useProfileStore.getState().profile).toBe('student');
    expect(useProfileStore.getState().manualOverride).toBe(true);
    // Auto-detect tenta mudar -> ignorado
    useProfileStore.getState().setProfile('policy');
    expect(useProfileStore.getState().profile).toBe('student');
  });

  it('reset clears manual override', () => {
    useProfileStore.getState().setProfile('policy', true);
    useProfileStore.getState().reset();
    expect(useProfileStore.getState().profile).toBe('researcher');
    expect(useProfileStore.getState().manualOverride).toBe(false);
  });
});
