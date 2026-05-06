import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch, apiGet, getApiBaseUrl } from '@/lib/api-client';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('getApiBaseUrl', () => {
  it('falls back to localhost:8000 when env unset', () => {
    vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '');
    expect(getApiBaseUrl()).toBe('http://localhost:8000');
  });

  it('uses NEXT_PUBLIC_API_BASE_URL when set', () => {
    vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'https://api.example.com');
    expect(getApiBaseUrl()).toBe('https://api.example.com');
  });
});

describe('apiFetch', () => {
  it('returns parsed JSON on 2xx', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ data: [1, 2, 3] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
    const result = await apiGet<{ data: number[] }>('/api/data/catalog');
    expect(result.data).toEqual([1, 2, 3]);
  });

  it('throws ApiError on 4xx with detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: 'invalid input' }), {
          status: 422,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
    await expect(apiFetch('/x')).rejects.toMatchObject({
      name: 'ApiError',
      status: 422,
      detail: { detail: 'invalid input' },
    });
  });

  it('ApiError keeps text body when JSON parse fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response('not json', {
          status: 500,
          headers: { 'Content-Type': 'text/plain' },
        }),
      ),
    );
    try {
      await apiFetch('/x');
      throw new Error('should have thrown');
    } catch (error) {
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(500);
      expect((error as ApiError).detail).toBe('not json');
    }
  });
});
