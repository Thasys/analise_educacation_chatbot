import { describe, expect, it } from 'vitest';
import { cn } from '@/lib/utils/cn';

describe('cn', () => {
  it('merges simple classes', () => {
    expect(cn('px-2', 'py-1')).toBe('px-2 py-1');
  });

  it('respects conditional classes', () => {
    expect(cn('px-2', false && 'hidden', undefined, 'bg-card')).toBe('px-2 bg-card');
  });

  it('resolves Tailwind conflicts via tailwind-merge', () => {
    // px-2 deve ser substituido por px-4 (mesma utility group)
    expect(cn('px-2', 'px-4')).toBe('px-4');
  });

  it('handles arrays of classes', () => {
    expect(cn(['flex', 'gap-2'], 'items-center')).toBe('flex gap-2 items-center');
  });
});
