import { describe, expect, it } from "vitest";
import { Stream } from "../src/core/streaming";

function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(enc.encode(c));
      controller.close();
    },
  });
}

describe("Stream.fromSSE", () => {
  it("parses well-formed events and stops at [DONE]", async () => {
    const body = streamOf([
      'data: {"i":1}\n\n',
      'data: {"i":2}\n\n',
      "data: [DONE]\n\n",
      'data: {"i":3}\n\n', // after DONE — must be ignored
    ]);
    const stream = Stream.fromSSE<{ i: number }>(body, new AbortController());
    const events = await stream.toArray();
    expect(events.map((e) => e.i)).toEqual([1, 2]);
  });

  it("reassembles events split across chunk boundaries", async () => {
    const body = streamOf(['data: {"hel', 'lo":"wor', 'ld"}\n\n', "data: [DONE]\n\n"]);
    const stream = Stream.fromSSE<{ hello: string }>(body, new AbortController());
    const events = await stream.toArray();
    expect(events).toEqual([{ hello: "world" }]);
  });

  it("ignores comments/keep-alive lines and handles CRLF", async () => {
    const body = streamOf([
      ": keep-alive\r\n",
      'data: {"ok":true}\r\n\r\n',
      "data: [DONE]\r\n\r\n",
    ]);
    const stream = Stream.fromSSE<{ ok: boolean }>(body, new AbortController());
    expect(await stream.toArray()).toEqual([{ ok: true }]);
  });
});
