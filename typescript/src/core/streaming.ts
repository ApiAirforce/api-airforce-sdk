/**
 * Server-Sent Events parsing and a typed, abortable {@link Stream}.
 *
 * The Airforce streaming endpoints (chat, messages, responses, gemini, video)
 * all emit `text/event-stream`. Each event's JSON `data` payload carries its own
 * discriminant (`object`, `type`, `event`), so a single generic stream that
 * yields the parsed `data` JSON is enough for every compat layer. The terminal
 * `data: [DONE]` sentinel ends the stream.
 */

import { AirforceError } from "./errors";

export interface ServerSentEvent {
  event: string | undefined;
  data: string;
  id: string | undefined;
}

const DONE = "[DONE]";

/** Incremental SSE line decoder. Feed it decoded text chunks; it yields events. */
class SSEDecoder {
  private buffer = "";
  private event: string | undefined;
  private data: string[] = [];
  private id: string | undefined;

  decode(chunk: string): ServerSentEvent[] {
    this.buffer += chunk;
    const out: ServerSentEvent[] = [];
    let idx: number;
    // Normalize CRLF and split on newlines; keep the trailing partial line.
    this.buffer = this.buffer.replace(/\r\n?/g, "\n");
    while ((idx = this.buffer.indexOf("\n")) !== -1) {
      const line = this.buffer.slice(0, idx);
      this.buffer = this.buffer.slice(idx + 1);
      const ev = this.feedLine(line);
      if (ev) out.push(ev);
    }
    return out;
  }

  /** Flush a final event if the stream ended without a trailing blank line. */
  flush(): ServerSentEvent | null {
    if (this.data.length === 0 && this.event === undefined) return null;
    return this.emit();
  }

  private feedLine(line: string): ServerSentEvent | null {
    if (line === "") {
      // Blank line dispatches the buffered event.
      if (this.data.length === 0 && this.event === undefined) return null;
      return this.emit();
    }
    if (line.startsWith(":")) return null; // comment / keep-alive

    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);

    switch (field) {
      case "event":
        this.event = value;
        break;
      case "data":
        this.data.push(value);
        break;
      case "id":
        this.id = value;
        break;
      // "retry" is ignored.
    }
    return null;
  }

  private emit(): ServerSentEvent {
    const ev: ServerSentEvent = {
      event: this.event,
      data: this.data.join("\n"),
      id: this.id,
    };
    this.event = undefined;
    this.data = [];
    this.id = undefined;
    return ev;
  }
}

/** Iterate raw SSE events from a fetch `Response` body. */
export async function* iterServerSentEvents(
  body: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<ServerSentEvent> {
  const reader = body.getReader();
  const decoder = new SSEDecoder();
  const textDecoder = new TextDecoder();
  try {
    for (;;) {
      if (signal?.aborted) break;
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = textDecoder.decode(value, { stream: true });
      for (const ev of decoder.decode(chunk)) yield ev;
    }
    const tail = decoder.flush();
    if (tail) yield tail;
  } finally {
    reader.releaseLock();
  }
}

/**
 * A typed, async-iterable stream of parsed events. Stops at the `[DONE]`
 * sentinel and is cancellable via {@link Stream.controller}.
 */
export class Stream<T> implements AsyncIterable<T> {
  constructor(
    private readonly source: () => AsyncGenerator<T>,
    readonly controller: AbortController,
  ) {}

  static fromSSE<T>(
    body: ReadableStream<Uint8Array>,
    controller: AbortController,
  ): Stream<T> {
    async function* parse(): AsyncGenerator<T> {
      for await (const sse of iterServerSentEvents(body, controller.signal)) {
        const raw = sse.data;
        if (raw === DONE || raw === "") {
          if (raw === DONE) return;
          continue;
        }
        let parsed: T;
        try {
          parsed = JSON.parse(raw) as T;
        } catch (err) {
          throw new AirforceError(
            `Failed to parse streaming event as JSON: ${raw.slice(0, 200)}`,
            { cause: err },
          );
        }
        yield parsed;
      }
    }
    return new Stream<T>(parse, controller);
  }

  [Symbol.asyncIterator](): AsyncIterator<T> {
    return this.source();
  }

  /** Abort the underlying HTTP request and stop iteration. */
  abort(): void {
    this.controller.abort();
  }

  /** Collect every event into an array (convenience for tests / small streams). */
  async toArray(): Promise<T[]> {
    const out: T[] = [];
    for await (const ev of this) out.push(ev);
    return out;
  }
}
