import { describe, expect, it } from "vitest";
import { Airforce } from "../src/client";
import { MissingCredentialError } from "../src/core/errors";
import type { EmbeddingsResponse } from "../src/resources/embeddings";
import type { ThreeDTask } from "../src/resources/threed";

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

describe("embeddings", () => {
  const embeddings: EmbeddingsResponse = {
    object: "list",
    data: [{ object: "embedding", index: 0, embedding: [0.1, -0.2, 0.3] }],
    model: "text-embedding-3-small",
    usage: { prompt_tokens: 3, total_tokens: 3 },
  };

  it("creates embeddings with an API key", async () => {
    const { fetch, calls } = makeFetch([json(200, embeddings)]);
    const client = new Airforce({ apiKey: "sk-air-test", fetch });

    const res = await client.embeddings.create({
      model: "text-embedding-3-small",
      input: ["hello world"],
    });

    expect(res.data[0]?.embedding).toEqual([0.1, -0.2, 0.3]);
    expect(res.usage.total_tokens).toBe(3);
    expect(calls[0]?.url).toBe("https://api.airforce/v1/embeddings");
    expect(calls[0]?.init.method).toBe("POST");
    const headers = calls[0]?.init.headers as Headers;
    expect(headers.get("authorization")).toBe("Bearer sk-air-test");
    const body = JSON.parse(String(calls[0]?.init.body));
    expect(body).toEqual({
      model: "text-embedding-3-small",
      input: ["hello world"],
    });
  });

  it("requires an API key", async () => {
    const { fetch } = makeFetch([json(200, embeddings)]);
    const client = new Airforce({ fetch });
    await expect(
      client.embeddings.create({ model: "m", input: "x" }),
    ).rejects.toBeInstanceOf(MissingCredentialError);
  });
});

describe("org", () => {
  it("fetches the caller's org and role with a session token", async () => {
    const { fetch, calls } = makeFetch([
      json(200, {
        org: {
          id: "org_1",
          name: "Acme",
          created_at: "2026-01-01T00:00:00Z",
          member_count: 3,
          settings: { sso: null },
        },
        role: "owner",
      }),
    ]);
    const client = new Airforce({ sessionToken: "jwt", fetch });

    const res = await client.org.get();

    expect(res.org.name).toBe("Acme");
    expect(res.role).toBe("owner");
    expect(calls[0]?.url).toBe("https://api.airforce/api/org");
    const headers = calls[0]?.init.headers as Headers;
    expect(headers.get("authorization")).toBe("Bearer jwt");
  });

  it("lists members and unwraps the envelope", async () => {
    const members = [
      {
        user_id: "u1",
        email: "owner@example.com",
        role: "owner",
        status: "active",
        joined_at: "2026-01-01T00:00:00Z",
      },
      {
        user_id: "u2",
        role: "member",
        status: "suspended",
        joined_at: "2026-02-01T00:00:00Z",
      },
    ];
    const { fetch, calls } = makeFetch([json(200, { members })]);
    const client = new Airforce({ sessionToken: "jwt", fetch });

    const res = await client.org.listMembers();

    expect(res).toHaveLength(2);
    expect(res[1]?.status).toBe("suspended");
    expect(calls[0]?.url).toBe("https://api.airforce/api/org/members");
  });

  it("creates an org key and unwraps the item (full key once)", async () => {
    const { fetch, calls } = makeFetch([
      json(201, {
        item: {
          id: "okey_1",
          org_id: "org_1",
          member_user_id: "u2",
          key: "sk-air-full-secret",
          label: "ci",
        },
      }),
    ]);
    const client = new Airforce({ sessionToken: "jwt", fetch });

    const key = await client.org.createKey({ member_user_id: "u2", label: "ci" });

    expect(key.id).toBe("okey_1");
    expect(key.key).toBe("sk-air-full-secret");
    expect(calls[0]?.init.method).toBe("POST");
    const body = JSON.parse(String(calls[0]?.init.body));
    expect(body).toEqual({ member_user_id: "u2", label: "ci" });
  });

  it("passes usage filters as query parameters", async () => {
    const { fetch, calls } = makeFetch([
      json(200, {
        total: { requests: 1, tokens_in: 2, tokens_out: 3, cost_cents: 4 },
        per_member: [],
        per_key: [],
        timeseries: [],
        attribution_since: "2026-06-01T00:00:00Z",
      }),
    ]);
    const client = new Airforce({ sessionToken: "jwt", fetch });

    await client.org.usage({ from: 100, to: 200, member_user_id: "u2" });

    const url = new URL(calls[0]!.url);
    expect(url.pathname).toBe("/api/org/usage");
    expect(url.searchParams.get("from")).toBe("100");
    expect(url.searchParams.get("to")).toBe("200");
    expect(url.searchParams.get("member_user_id")).toBe("u2");
    expect(url.searchParams.get("key_id")).toBeNull();
  });

  it("requires a session token", async () => {
    const { fetch } = makeFetch([json(200, {})]);
    const client = new Airforce({ apiKey: "sk-air-test", fetch });
    await expect(client.org.get()).rejects.toBeInstanceOf(MissingCredentialError);
  });
});

describe("notifications", () => {
  it("lists the feed with limit/before cursor params", async () => {
    const { fetch, calls } = makeFetch([
      json(200, {
        items: [
          {
            id: "n1",
            event_id: "e1",
            kind: "price_drop",
            params_json: "{}",
            created_at: "2026-07-01T00:00:00Z",
          },
        ],
        unread: 5,
      }),
    ]);
    const client = new Airforce({ sessionToken: "jwt", fetch });

    const res = await client.notifications.list({
      limit: 10,
      before: "2026-07-02T00:00:00Z",
    });

    expect(res.items[0]?.kind).toBe("price_drop");
    expect(res.unread).toBe(5);
    const url = new URL(calls[0]!.url);
    expect(url.pathname).toBe("/api/me/notifications");
    expect(url.searchParams.get("limit")).toBe("10");
    expect(url.searchParams.get("before")).toBe("2026-07-02T00:00:00Z");
  });

  it("marks items read", async () => {
    const { fetch, calls } = makeFetch([json(200, { updated: 2, unread: 0 })]);
    const client = new Airforce({ sessionToken: "jwt", fetch });

    const res = await client.notifications.markRead({ ids: ["n1", "n2"] });

    expect(res.updated).toBe(2);
    expect(calls[0]?.url).toBe("https://api.airforce/api/me/notifications/read");
    const body = JSON.parse(String(calls[0]?.init.body));
    expect(body).toEqual({ ids: ["n1", "n2"] });
  });

  it("patches partial prefs and returns the updated document", async () => {
    const prefs = {
      routing: { price_drop: ["email"] },
      price_drop: {
        enabled: true,
        scope: "watchlist_only",
        threshold_pct: 10,
        min_absolute_drop_cents_per_1m: 5,
      },
      new_model: { enabled: false, providers: [], modalities: [] },
      watchlist: {},
      digest_frequency: "daily",
      quiet_hours: null,
      unsubscribed_all: false,
      strong_model_categories: [],
    };
    const { fetch, calls } = makeFetch([json(200, prefs)]);
    const client = new Airforce({ sessionToken: "jwt", fetch });

    const res = await client.notifications.updatePrefs({
      digest_frequency: "daily",
      quiet_hours: null,
    });

    expect(res.digest_frequency).toBe("daily");
    expect(calls[0]?.init.method).toBe("PATCH");
    const body = JSON.parse(String(calls[0]?.init.body));
    expect(body).toEqual({ digest_frequency: "daily", quiet_hours: null });
  });

  it("unlinks a channel via its path segment", async () => {
    const { fetch, calls } = makeFetch([
      json(200, { status: "revoked", channel: "telegram" }),
    ]);
    const client = new Airforce({ sessionToken: "jwt", fetch });

    const res = await client.notifications.unlinkChannel("telegram");

    expect(res.status).toBe("revoked");
    expect(calls[0]?.url).toBe("https://api.airforce/api/me/channels/telegram");
    expect(calls[0]?.init.method).toBe("DELETE");
  });
});

describe("account closure", () => {
  it("soft-closes the account with re-auth in the body", async () => {
    const { fetch, calls } = makeFetch([json(200, { closed: true })]);
    const client = new Airforce({ sessionToken: "jwt", fetch });

    const res = await client.account.closeAccount({
      password: "hunter2",
      forfeit_balance_ack: true,
    });

    expect(res.closed).toBe(true);
    expect(calls[0]?.url).toBe("https://api.airforce/api/me/account");
    expect(calls[0]?.init.method).toBe("DELETE");
    const body = JSON.parse(String(calls[0]?.init.body));
    expect(body).toEqual({ password: "hunter2", forfeit_balance_ack: true });
  });

  it("reactivates without any credential", async () => {
    const { fetch, calls } = makeFetch([
      json(200, {
        reactivated: true,
        email_restored: true,
        username_restored: false,
      }),
    ]);
    const client = new Airforce({ fetch });

    const res = await client.auth.reactivate({
      email: "old@example.com",
      password: "hunter2",
    });

    expect(res.reactivated).toBe(true);
    expect(res.username_restored).toBe(false);
    expect(calls[0]?.url).toBe("https://api.airforce/auth/reactivate");
    const headers = calls[0]?.init.headers as Headers;
    expect(headers.get("authorization")).toBeNull();
  });
});

describe("3d generation", () => {
  const task = (status: ThreeDTask["status"], extra: Partial<ThreeDTask> = {}): ThreeDTask => ({
    task_id: "t3d_1",
    status,
    model: "shape-1",
    created: 0,
    expires_at: 86_400,
    has_result: status === "completed",
    ...extra,
  });

  it("submits a task and polls it to completion", async () => {
    const { fetch, calls } = makeFetch([
      json(200, task("queued")),
      json(200, task("processing")),
      json(200, task("completed", { format: "glb", cost_cents: 12 })),
    ]);
    const client = new Airforce({ apiKey: "sk-air-test", fetch });

    const done = await client.threed.generateAndWait(
      { model: "shape-1", image_urls: ["https://example.com/a.png"] },
      { pollIntervalMs: 1 },
    );

    expect(done.status).toBe("completed");
    expect(done.format).toBe("glb");
    expect(calls[0]?.url).toBe("https://api.airforce/v1/3d/generations");
    expect(calls[1]?.url).toBe("https://api.airforce/v1/3d/tasks/t3d_1");
  });

  it("throws a typed error when the task fails", async () => {
    const { fetch } = makeFetch([
      json(200, task("failed", { error: "bad input image" })),
    ]);
    const client = new Airforce({ apiKey: "sk-air-test", fetch });

    await expect(client.threed.waitForCompletion("t3d_1")).rejects.toMatchObject({
      code: "failed",
    });
  });

  it("lists tasks and downloads the binary artifact", async () => {
    const bytes = new Uint8Array([0x67, 0x6c, 0x54, 0x46]); // "glTF"
    const { fetch, calls } = makeFetch([
      json(200, { data: [task("completed")] }),
      new Response(bytes, {
        status: 200,
        headers: { "content-type": "model/gltf-binary" },
      }),
    ]);
    const client = new Airforce({ apiKey: "sk-air-test", fetch });

    const tasks = await client.threed.listTasks();
    expect(tasks).toHaveLength(1);

    const buf = await client.threed.downloadContent("t3d_1");
    expect(new Uint8Array(buf)).toEqual(bytes);
    expect(calls[1]?.url).toBe("https://api.airforce/v1/3d/tasks/t3d_1/content");
  });
});

describe("routing preferences", () => {
  it("sets routing-category prefs with an API key", async () => {
    const { fetch, calls } = makeFetch([json(200, { ok: true })]);
    const client = new Airforce({ apiKey: "sk-air-test", fetch });

    const res = await client.account.setRoutingCategoryPrefs({
      "claude-opus-4.8": "cheapest",
    });

    expect(res.ok).toBe(true);
    expect(calls[0]?.url).toBe(
      "https://api.airforce/api/user/routing-category-prefs",
    );
    expect(calls[0]?.init.method).toBe("PUT");
    const body = JSON.parse(String(calls[0]?.init.body));
    expect(body).toEqual({ "claude-opus-4.8": "cheapest" });
  });

  it("resolves routing categories for a model", async () => {
    const { fetch, calls } = makeFetch([json(200, { categories: [] })]);
    const client = new Airforce({ apiKey: "sk-air-test", fetch });

    await client.account.routingCategories("claude-opus-4.8");

    const url = new URL(calls[0]!.url);
    expect(url.pathname).toBe("/api/user/routing-categories");
    expect(url.searchParams.get("model")).toBe("claude-opus-4.8");
  });

  it("creates a custom provider model over the session surface", async () => {
    const { fetch, calls } = makeFetch([new Response(null, { status: 201 })]);
    const client = new Airforce({ sessionToken: "jwt", fetch });

    await client.account.createCustomModel({
      fake_name: "my-model",
      endpoint: "https://my-upstream.example.com/v1/chat/completions",
    });

    expect(calls[0]?.url).toBe("https://api.airforce/api/models");
    expect(calls[0]?.init.method).toBe("POST");
  });
});

describe("chat reasoning parameter", () => {
  it("serializes the reasoning config into the request body", async () => {
    const { fetch, calls } = makeFetch([
      json(200, {
        id: "cmpl_1",
        object: "chat.completion",
        created: 0,
        model: "m",
        choices: [
          {
            index: 0,
            message: { role: "assistant", content: "hi", reasoning: "because" },
            finish_reason: "stop",
          },
        ],
      }),
    ]);
    const client = new Airforce({ apiKey: "sk-air-test", fetch });

    const res = await client.chat.create({
      model: "m",
      messages: [{ role: "user", content: "x" }],
      reasoning: { format: "separate" },
    });

    expect(res.choices[0]?.message.reasoning).toBe("because");
    const body = JSON.parse(String(calls[0]?.init.body));
    expect(body.reasoning).toEqual({ format: "separate" });
  });
});
