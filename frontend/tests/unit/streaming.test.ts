import { afterEach, describe, expect, it, vi } from 'vitest';
import { streamChat } from '@/lib/streaming';
import type { FinalAnswer } from '@/types/domain';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

const FAKE_FINAL: FinalAnswer = {
  markdown: '# x',
  profile_used: 'researcher',
  flow_used: 'data',
  sources_cited: [],
  visualizations: [],
  citations: [],
  warnings: [],
  follow_up_suggestions: [],
};

function makeSseResponse(blocks: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const b of blocks) controller.enqueue(encoder.encode(b));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  });
}

describe('streamChat', () => {
  it('invokes onEvent for each SSE message and onFinal at end', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        makeSseResponse([
          'event: agent_started\ndata: {"agent":"Core","ts":1}\n\n',
          `event: final_answer\ndata: {"payload":${JSON.stringify(FAKE_FINAL)}}\n\n`,
        ]),
      ),
    );

    const events: unknown[] = [];
    let final: FinalAnswer | null = null;
    const result = await streamChat(
      'pergunta',
      {
        onEvent: (e) => events.push(e),
        onFinal: (f) => {
          final = f;
        },
      },
      { baseUrl: 'http://x' },
    );

    expect(events.length).toBeGreaterThanOrEqual(2);
    expect(final).toEqual(FAKE_FINAL);
    expect(result).toEqual(FAKE_FINAL);
  });

  it('throws and calls onError when server returns error event', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        makeSseResponse([
          'event: error\ndata: {"error":"simulated","ts":1}\n\n',
        ]),
      ),
    );
    const onError = vi.fn();
    await expect(
      streamChat('q', { onError }, { baseUrl: 'http://x' }),
    ).rejects.toThrow('simulated');
    expect(onError).toHaveBeenCalledOnce();
  });

  it('throws when response is not 2xx', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: 'bad input' }), {
          status: 422,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
    const onError = vi.fn();
    await expect(
      streamChat('q', { onError }, { baseUrl: 'http://x' }),
    ).rejects.toMatchObject({ name: 'ApiError', status: 422 });
    expect(onError).toHaveBeenCalledOnce();
  });

  it('throws when stream ends without final_answer', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        makeSseResponse([
          'event: agent_started\ndata: {"agent":"Core","ts":1}\n\n',
        ]),
      ),
    );
    await expect(
      streamChat('q', {}, { baseUrl: 'http://x' }),
    ).rejects.toThrow('sem final_answer');
  });
});
