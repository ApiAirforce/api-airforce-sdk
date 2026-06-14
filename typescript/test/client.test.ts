import { describe, expect, it } from "vitest";
import { Airforce } from "../src/client";
import { MissingCredentialError } from "../src/core/errors";
import { Stream } from "../src/core/streaming";
import type { ChatCompletion, ChatCompletionChunk } from "../src/resources/chat";

interface RecordedCall {
  url: string;
  init: RequestInit;
}

function makeFetch(responses: Response[]): {
  fetch: typeof fetch;
  calls: RecordedCall[];
} {
  const queue = [...responses];
  const calls: RecordedCall[] = [];
  const fetch = (async (url: string | URL | Request, init?: RequestInit) => {
    calls.push({ url: String(url), init: init ?? {} });
    const res = queue.shift();
    if (!res) throw new Error("no more mock responses");
    return res;
  }) as unknown as typeof fetch;
  return { fetch, calls };
}

function json(status: number, body: unknown, headers?: Record<string, string>): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

function sse(chunks: string[]): Response {
  const enc = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const c of chunks) controller.enqueue(enc.encode(c));
      controller.close();
    },
  });
  return new Response(body, {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
}

const completion: ChatCompletion = {
  id: "cmpl_1",
  object: "chat.completion",
  created: 0,
  model: "claude-opus-4.8",
  choices: [
    { index: 0, message: { role: "assistant", content: "hi" }, finish_reason: "stop" },
  ],
};

describe("Airforce client", () => {
  it("sends a Bearer API key and parses the response", async () => {
    const { fetch, calls } = makeFetch([json(200, completion)]);
    const client = new Airforce({ apiKey: "sk-air-test", fetch });

    const res = await client.chat.create({
      model: "claude-opus-4.8",
      messages: [{ role: "user", content: "hello" }],
    });

    expect(res.choices[0]?.message.content).toBe("hi");
    expect(calls[0]?.url).toBe("https://api.airforce/v1/chat/completions");
    const headers = calls[0]?.init.headers as Headers;
    expect(headers.get("authorization")).toBe("Bearer sk-air-test");
    expect(headers.get("content-type")).toBe("application/json");
  });

  it("throws MissingCredentialError when no api key is set", async () => {
    const { fetch } = makeFetch([json(200, completion)]);
    const client = new Airforce({ fetch });
    await expect(
      client.chat.create({ model: "m", messages: [{ role: "user", content: "x" }] }),
    ).rejects.toBeInstanceOf(MissingCredentialError);
  });

  it("does not attach auth to public endpoints", async () => {
    const { fetch, calls } = makeFetch([json(200, { object: "list", data: [] })]);
    const client = new Airforce({ fetch });
    await client.models.list();
    const headers = calls[0]?.init.headers as Headers;
    expect(headers.get("authorization")).toBeNull();
  });

  it("retries on 429 then succeeds", async () => {
    const { fetch, calls } = makeFetch([
      json(429, { error: "slow down" }, { "retry-after": "0" }),
      json(200, completion),
    ]);
    const client = new Airforce({ apiKey: "sk-air-test", fetch });
    const res = await client.chat.create({
      model: "m",
      messages: [{ role: "user", content: "x" }],
    });
    expect(res.id).toBe("cmpl_1");
    expect(calls).toHaveLength(2);
  });

  it("streams chat completion chunks", async () => {
    const { fetch } = makeFetch([
      sse([
        'data: {"id":"c","object":"chat.completion.chunk","created":0,"model":"m","choices":[{"index":0,"delta":{"content":"he"},"finish_reason":null}]}\n\n',
        'data: {"id":"c","object":"chat.completion.chunk","created":0,"model":"m","choices":[{"index":0,"delta":{"content":"llo"},"finish_reason":"stop"}]}\n\n',
        "data: [DONE]\n\n",
      ]),
    ]);
    const client = new Airforce({ apiKey: "sk-air-test", fetch });
    const stream = (await client.chat.create({
      model: "m",
      messages: [{ role: "user", content: "x" }],
      stream: true,
    })) as Stream<ChatCompletionChunk>;

    let text = "";
    for await (const chunk of stream) {
      text += chunk.choices[0]?.delta.content ?? "";
    }
    expect(text).toBe("hello");
  });

  it("requires a session token for session endpoints (no api-key fallback)", async () => {
    const { fetch } = makeFetch([json(200, {})]);
    const client = new Airforce({ apiKey: "sk-air-test", fetch });
    // account.me is a session endpoint; an API key must NOT be substituted.
    await expect(client.account.me()).rejects.toBeInstanceOf(MissingCredentialError);
  });

  it("reads AIRFORCE_API_KEY from the environment", async () => {
    process.env.AIRFORCE_API_KEY = "sk-air-env";
    const { fetch, calls } = makeFetch([json(200, completion)]);
    const client = new Airforce({ fetch });
    await client.chat.create({ model: "m", messages: [{ role: "user", content: "x" }] });
    const headers = calls[0]?.init.headers as Headers;
    expect(headers.get("authorization")).toBe("Bearer sk-air-env");
    delete process.env.AIRFORCE_API_KEY;
  });
});
