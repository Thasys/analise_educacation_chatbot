/**
 * Cliente alto-nivel do endpoint /api/chat/stream do agents-server.
 *
 * Conecta `fetch` (POST com body JSON) → `ReadableStream` → `SseParser`
 * → callbacks tipados por evento.
 */

import type { FinalAnswer, StreamEvent } from '@/types/domain';
import { ApiError } from '@/lib/api-client';
import { parseSseStream } from '@/lib/sse-parser';

const DEFAULT_AGENTS_BASE_URL = 'http://localhost:8001';

export function getAgentsBaseUrl(): string {
  if (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_AGENTS_BASE_URL) {
    return process.env.NEXT_PUBLIC_AGENTS_BASE_URL;
  }
  return DEFAULT_AGENTS_BASE_URL;
}

export interface StreamChatCallbacks {
  /** Cada evento parseado da stream (tipado conforme StreamEvent). */
  onEvent?: (event: StreamEvent) => void;
  /** Helper: chamado SO quando type=='final_answer'. */
  onFinal?: (final: FinalAnswer) => void;
  /** Erro de transporte ou error event do servidor. */
  onError?: (error: Error) => void;
}

export interface StreamChatOptions {
  /** Sinal de aborto (botao "cancelar" no UI). */
  signal?: AbortSignal;
  /** Override do agents base URL (default: env var ou localhost:8001). */
  baseUrl?: string;
}

/**
 * Mapeia evento SSE bruto -> StreamEvent tipado do dominio.
 *
 * O backend (agents/src/server) emite eventos com fields conforme
 * `agents/src/server/schemas.py::ChatStreamEvent`. Aqui convertemos
 * para a uniao discriminada usada nos componentes React.
 */
function toStreamEvent(rawEvent: string, parsedData: unknown): StreamEvent | null {
  const data = parsedData as Record<string, unknown>;
  const ts = typeof data.ts === 'number' ? data.ts : Date.now() / 1000;
  switch (rawEvent) {
    case 'flow_started':
      return { type: 'flow_started', question: String(data.question ?? ''), ts };
    case 'agent_started':
      return { type: 'agent_started', agent: String(data.agent ?? '?'), ts };
    case 'agent_done': {
      const event: StreamEvent = {
        type: 'agent_done',
        agent: String(data.agent ?? '?'),
        ts,
      };
      // Repassa apenas campos opcionais conhecidos (com tipos validados)
      if (data.result !== undefined) event.result = data.result as Record<string, unknown>;
      if (typeof data.tool_calls === 'number') event.tool_calls = data.tool_calls;
      if (typeof data.method === 'string') event.method = data.method;
      if (typeof data.sample_size === 'number') event.sample_size = data.sample_size;
      if (typeof data.items === 'number') event.items = data.items;
      if (typeof data.chart_type === 'string') event.chart_type = data.chart_type;
      return event;
    }
    case 'final_answer':
      return {
        type: 'final_answer',
        payload: (data.payload as FinalAnswer) ?? null!,
      };
    case 'error':
      return { type: 'error', error: String(data.error ?? 'unknown'), ts };
    default:
      return null;
  }
}

/**
 * Inicia uma sessao de chat streaming. Retorna uma Promise que resolve
 * com o FinalAnswer (ou rejeita se erro/abort).
 */
export async function streamChat(
  question: string,
  callbacks: StreamChatCallbacks = {},
  options: StreamChatOptions = {},
): Promise<FinalAnswer> {
  const baseUrl = (options.baseUrl ?? getAgentsBaseUrl()).replace(/\/$/, '');
  const response = await fetch(`${baseUrl}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify({ question }),
    signal: options.signal,
  });

  if (!response.ok) {
    const text = await response.text();
    let detail: unknown = text;
    try {
      detail = JSON.parse(text);
    } catch {
      // mantem string
    }
    const error = new ApiError(response.status, detail);
    callbacks.onError?.(error);
    throw error;
  }

  if (!response.body) {
    const error = new Error('Resposta SSE sem body');
    callbacks.onError?.(error);
    throw error;
  }

  let final: FinalAnswer | null = null;
  for await (const msg of parseSseStream(response.body)) {
    let parsedData: unknown;
    try {
      parsedData = JSON.parse(msg.data);
    } catch {
      // Evento sem payload JSON valido — ignorar
      continue;
    }
    const streamEvent = toStreamEvent(msg.event, parsedData);
    if (streamEvent === null) continue;
    callbacks.onEvent?.(streamEvent);
    if (streamEvent.type === 'final_answer') {
      final = streamEvent.payload;
      callbacks.onFinal?.(final);
    } else if (streamEvent.type === 'error') {
      const error = new Error(streamEvent.error);
      callbacks.onError?.(error);
      throw error;
    }
  }

  if (final === null) {
    const error = new Error('Stream terminou sem final_answer');
    callbacks.onError?.(error);
    throw error;
  }
  return final;
}
