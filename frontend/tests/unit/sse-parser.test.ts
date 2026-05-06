import { describe, expect, it } from 'vitest';
import { SseParser, parseSseStream } from '@/lib/sse-parser';

describe('SseParser', () => {
  it('parses single event with event + data', () => {
    const parser = new SseParser();
    const messages = parser.feed('event: foo\ndata: hello\n\n');
    expect(messages).toEqual([{ event: 'foo', data: 'hello' }]);
  });

  it('defaults event type to "message"', () => {
    const parser = new SseParser();
    const messages = parser.feed('data: just data\n\n');
    expect(messages[0]?.event).toBe('message');
  });

  it('joins multiple data lines with newline', () => {
    const parser = new SseParser();
    const messages = parser.feed('event: x\ndata: line 1\ndata: line 2\n\n');
    expect(messages[0]?.data).toBe('line 1\nline 2');
  });

  it('ignores comment lines (starting with :)', () => {
    const parser = new SseParser();
    const messages = parser.feed(': keepalive\nevent: ping\ndata: pong\n\n');
    expect(messages).toHaveLength(1);
    expect(messages[0]?.event).toBe('ping');
  });

  it('strips leading space after colon', () => {
    const parser = new SseParser();
    const messages = parser.feed('event:  spaced\ndata: value\n\n');
    expect(messages[0]?.event).toBe(' spaced'); // apenas o primeiro espaco e removido
  });

  it('handles chunked input across feed calls', () => {
    const parser = new SseParser();
    const m1 = parser.feed('event: foo\nda');
    expect(m1).toEqual([]);
    const m2 = parser.feed('ta: hello\n\nevent: bar\ndata: world\n\n');
    expect(m2).toEqual([
      { event: 'foo', data: 'hello' },
      { event: 'bar', data: 'world' },
    ]);
  });

  it('flush emits trailing event without final \\n\\n', () => {
    const parser = new SseParser();
    parser.feed('event: x\ndata: residual');
    expect(parser.flush()).toEqual([{ event: 'x', data: 'residual' }]);
  });

  it('captures id field', () => {
    const parser = new SseParser();
    const messages = parser.feed('id: 42\nevent: foo\ndata: x\n\n');
    expect(messages[0]?.id).toBe('42');
  });

  it('skips events without data', () => {
    const parser = new SseParser();
    const messages = parser.feed('event: noop\n\n');
    expect(messages).toEqual([]);
  });
});

describe('parseSseStream', () => {
  it('iterates messages from a ReadableStream', async () => {
    const chunks = [
      'event: agent_started\ndata: {"agent":"Core","ts":1}\n\n',
      'event: agent_done\ndata: {"agent":"Core","ts":2}\n\n',
      'event: final_answer\ndata: {"payload":{"flow_used":"data"}}\n\n',
    ];
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        const encoder = new TextEncoder();
        for (const c of chunks) controller.enqueue(encoder.encode(c));
        controller.close();
      },
    });
    const collected: { event: string; data: string }[] = [];
    for await (const msg of parseSseStream(stream)) {
      collected.push({ event: msg.event, data: msg.data });
    }
    expect(collected).toHaveLength(3);
    expect(collected[0]?.event).toBe('agent_started');
    expect(collected[2]?.event).toBe('final_answer');
  });

  it('handles chunks split across SSE boundaries', async () => {
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        const encoder = new TextEncoder();
        controller.enqueue(encoder.encode('event: foo\nda'));
        controller.enqueue(encoder.encode('ta: hi\n\nevent: bar\nda'));
        controller.enqueue(encoder.encode('ta: bye\n\n'));
        controller.close();
      },
    });
    const collected = [];
    for await (const msg of parseSseStream(stream)) collected.push(msg);
    expect(collected).toEqual([
      { event: 'foo', data: 'hi' },
      { event: 'bar', data: 'bye' },
    ]);
  });
});
