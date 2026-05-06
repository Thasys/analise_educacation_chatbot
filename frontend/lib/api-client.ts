/**
 * Cliente HTTP do frontend para o gateway FastAPI.
 *
 * Sprint 6.0: helpers para `fetch` com base URL e tratamento de erros.
 * Sprint 6.1 adiciona o parser SSE para `/api/chat/stream`.
 */

const DEFAULT_BASE_URL = 'http://localhost:8000';

export function getApiBaseUrl(): string {
  if (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }
  return DEFAULT_BASE_URL;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
    message?: string,
  ) {
    super(message ?? `API error ${status}`);
    this.name = 'ApiError';
  }
}

/**
 * Wrapper de fetch que normaliza erros HTTP em ApiError.
 */
export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${path.startsWith('/') ? path : `/${path}`}`;
  const response = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(init.headers ?? {}),
    },
  });
  if (!response.ok) {
    // Body so pode ser lido uma vez. Lemos como texto e tentamos parsear
    // como JSON; se falhar, repassamos a string crua.
    const raw = await response.text();
    let detail: unknown = raw;
    try {
      detail = JSON.parse(raw);
    } catch {
      // mantem string raw em `detail`
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

/** GET helper. */
export function apiGet<T = unknown>(path: string): Promise<T> {
  return apiFetch<T>(path, { method: 'GET' });
}

/** POST JSON helper. */
export function apiPost<T = unknown>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}
