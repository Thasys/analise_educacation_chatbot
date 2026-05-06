/**
 * Parser SSE para streams iniciados via `fetch` + `ReadableStream`.
 *
 * Por que nao usar `EventSource`?
 *   - `EventSource` so suporta GET; nosso endpoint e POST com body JSON.
 *   - `EventSource` nao permite headers customizados.
 *
 * Implementacao manual segue a spec W3C: cada bloco e separado por
 * "\n\n"; cada linha e `field: value`. Ignoramos comentarios (linhas
 * que comecam com ":") e mantemos um buffer entre chunks parciais.
 */

export interface SseMessage {
  /** Valor de `event: <type>`. Default 'message' se nao especificado. */
  event: string;
  /** Texto bruto da(s) linha(s) `data: ...`. Linhas multiplas sao concatenadas com \n. */
  data: string;
  /** Valor de `id: <...>` se presente. */
  id?: string;
}

/**
 * Parser stateful — acumula buffer entre chunks.
 *
 * Uso:
 *   const parser = new SseParser();
 *   for await (const chunk of stream) {
 *     for (const msg of parser.feed(chunk)) {
 *       handle(msg);
 *     }
 *   }
 *   // Drena buffer final (caso ultimo evento nao termine com \n\n)
 *   for (const msg of parser.flush()) handle(msg);
 */
export class SseParser {
  private buffer = '';

  feed(chunk: string): SseMessage[] {
    this.buffer += chunk;
    const messages: SseMessage[] = [];
    let separatorIndex: number;
    while ((separatorIndex = this.buffer.indexOf('\n\n')) !== -1) {
      const block = this.buffer.slice(0, separatorIndex);
      this.buffer = this.buffer.slice(separatorIndex + 2);
      const parsed = parseBlock(block);
      if (parsed) messages.push(parsed);
    }
    return messages;
  }

  /**
   * Drena qualquer evento residual no buffer (ultimo chunk pode nao
   * terminar com \n\n).
   */
  flush(): SseMessage[] {
    if (!this.buffer.trim()) return [];
    const block = this.buffer;
    this.buffer = '';
    const parsed = parseBlock(block);
    return parsed ? [parsed] : [];
  }
}

function parseBlock(block: string): SseMessage | null {
  const lines = block.split('\n');
  let event = 'message';
  let id: string | undefined;
  const dataLines: string[] = [];

  for (const line of lines) {
    if (!line || line.startsWith(':')) continue; // comentario ou vazia
    const colonIdx = line.indexOf(':');
    const field = colonIdx === -1 ? line : line.slice(0, colonIdx);
    // Spec: se houver um espaco apos `:` ele e ignorado.
    let value = colonIdx === -1 ? '' : line.slice(colonIdx + 1);
    if (value.startsWith(' ')) value = value.slice(1);
    switch (field) {
      case 'event':
        event = value;
        break;
      case 'data':
        dataLines.push(value);
        break;
      case 'id':
        id = value;
        break;
      // 'retry' ignorado nesta sprint.
    }
  }

  if (dataLines.length === 0) return null;
  const result: SseMessage = { event, data: dataLines.join('\n') };
  if (id !== undefined) result.id = id;
  return result;
}

/**
 * Decodificador async-iterable de uma `ReadableStream<Uint8Array>` para
 * mensagens SSE parseadas.
 */
export async function* parseSseStream(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<SseMessage, void, void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder('utf-8');
  const parser = new SseParser();
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      for (const msg of parser.feed(chunk)) yield msg;
    }
    for (const msg of parser.flush()) yield msg;
  } finally {
    reader.releaseLock();
  }
}
