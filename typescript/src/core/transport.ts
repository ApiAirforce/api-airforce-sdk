/**
 * The low-level HTTP transport: header/auth assembly, retries with backoff,
 * JSON and multipart requests, binary responses, and SSE streaming.
 *
 * Depends only on the global `fetch` (Node >= 18, browsers, edge runtimes); a
 * custom `fetch` can be injected for testing or non-standard runtimes.
 */

import {
  AirforceConnectionError,
  AirforceError,
  AirforceTimeoutError,
  MissingCredentialError,
} from "./errors";
import { Stream } from "./streaming";

export const VERSION = "0.0.1";
export const DEFAULT_BASE_URL = "https://api.airforce";

/** Which credential a given endpoint expects. */
export type AuthMode = "api_key" | "session" | "none";

export type QueryValue = string | number | boolean | undefined | null;

export interface RequestOptions {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  /** Which credential to attach. Defaults to `api_key`. */
  auth?: AuthMode;
  query?: Record<string, QueryValue>;
  /** JSON body. Mutually exclusive with `form` / `urlencoded`. */
  body?: unknown;
  /** Multipart form body. Mutually exclusive with `body` / `urlencoded`. */
  form?: FormData;
  /** `application/x-www-form-urlencoded` body (OAuth token/revoke). */
  urlencoded?: Record<string, string | undefined>;
  headers?: Record<string, string>;
  /** Per-request timeout override (ms). */
  timeout?: number;
  /** Per-request retry override. */
  maxRetries?: number;
  /** Caller-supplied abort signal. */
  signal?: AbortSignal;
}

export interface TransportConfig {
  apiKey?: string;
  sessionToken?: string;
  baseURL: string;
  timeout: number;
  maxRetries: number;
  defaultHeaders: Record<string, string>;
  fetch: typeof fetch;
}

// 409 is intentionally excluded: it is a terminal business conflict (e.g. "already
// subscribed" on checkout), not a transient error worth retrying.
const RETRYABLE_STATUS = new Set([408, 429, 500, 502, 503, 504]);

interface FetchResponseOutcome {
  kind: "response";
  response: Response;
}
interface FetchErrorOutcome {
  kind: "error";
  error: unknown;
  timedOut: boolean;
}
type FetchOutcome = FetchResponseOutcome | FetchErrorOutcome;

function describeError(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string") return error;
  try {
    return JSON.stringify(error) ?? "unknown error";
  } catch {
    return "unknown error";
  }
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(new AirforceError("Aborted"));
    const t = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(t);
        reject(new AirforceError("Aborted"));
      },
      { once: true },
    );
  });
}

export class Transport {
  constructor(private readonly config: TransportConfig) {}

  /** Update the session token (e.g. after `auth.login()`). */
  setSessionToken(token: string | undefined): void {
    this.config.sessionToken = token;
  }

  /** Update the API key. */
  setApiKey(key: string | undefined): void {
    this.config.apiKey = key;
  }

  /** Perform a request and decode the JSON response into `T`. */
  async request<T>(options: RequestOptions): Promise<T> {
    return (await this.requestDetailed<T>(options)).data;
  }

  /** Like {@link request} but also returns the response headers. */
  async requestDetailed<T>(
    options: RequestOptions,
  ): Promise<{ data: T; headers: Headers }> {
    const res = await this.send(options, false);
    const headers = res.headers;
    if (res.status === 204) return { data: undefined as T, headers };
    const text = await res.text();
    if (!text) return { data: undefined as T, headers };
    try {
      return { data: JSON.parse(text) as T, headers };
    } catch {
      // Some endpoints return a bare string body.
      return { data: text as unknown as T, headers };
    }
  }

  /** Perform a request and return the raw binary body (audio, etc.). */
  async requestBinary(options: RequestOptions): Promise<ArrayBuffer> {
    const res = await this.send(options, false);
    return res.arrayBuffer();
  }

  /** Perform a streaming request and return a typed SSE {@link Stream}. */
  async stream<T>(options: RequestOptions): Promise<Stream<T>> {
    const controller = new AbortController();
    if (options.signal) {
      options.signal.addEventListener("abort", () => controller.abort(), {
        once: true,
      });
    }
    const res = await this.send(
      { ...options, signal: controller.signal },
      true,
    );
    if (!res.body) {
      throw new AirforceError("Streaming response had no body");
    }
    return Stream.fromSSE<T>(res.body, controller);
  }

  // --- internals -----------------------------------------------------------

  private resolveToken(auth: AuthMode): string | undefined {
    if (auth === "none") return undefined;
    // Session endpoints require a session JWT — never silently substitute an API
    // key (that would send the wrong credential and mask MissingCredentialError).
    if (auth === "session") return this.config.sessionToken;
    return this.config.apiKey ?? this.config.sessionToken;
  }

  private buildURL(path: string, query?: Record<string, QueryValue>): string {
    const url = new URL(
      path.startsWith("/") ? path.slice(1) : path,
      this.config.baseURL.endsWith("/")
        ? this.config.baseURL
        : this.config.baseURL + "/",
    );
    if (query) {
      for (const [k, v] of Object.entries(query)) {
        if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
      }
    }
    return url.toString();
  }

  private buildHeaders(
    options: RequestOptions,
    streaming: boolean,
  ): Headers {
    const headers = new Headers(this.config.defaultHeaders);
    headers.set("user-agent", `airforce-sdk-js/${VERSION}`);
    headers.set("x-airforce-sdk", `js/${VERSION}`);
    headers.set("accept", streaming ? "text/event-stream" : "application/json");

    const auth: AuthMode = options.auth ?? "api_key";
    const token = this.resolveToken(auth);
    if (auth !== "none") {
      if (!token) {
        throw new MissingCredentialError(
          auth === "session"
            ? "This endpoint requires a session token (set `sessionToken`, e.g. from auth.login())."
            : "This endpoint requires an API key (set `apiKey`).",
          { code: "missing_credential" },
        );
      }
      headers.set("authorization", `Bearer ${token}`);
    }

    if (options.urlencoded) {
      headers.set("content-type", "application/x-www-form-urlencoded");
    } else if (options.body !== undefined && !options.form) {
      headers.set("content-type", "application/json");
    }
    if (options.headers) {
      for (const [k, v] of Object.entries(options.headers)) headers.set(k, v);
    }
    return headers;
  }

  private buildRequestInit(
    options: RequestOptions,
    streaming: boolean,
  ): RequestInit {
    const init: RequestInit = {
      method: options.method,
      headers: this.buildHeaders(options, streaming),
    };
    if (options.form) {
      init.body = options.form; // fetch sets the multipart boundary
    } else if (options.urlencoded) {
      const params = new URLSearchParams();
      for (const [k, v] of Object.entries(options.urlencoded)) {
        if (v !== undefined) params.set(k, v);
      }
      init.body = params;
    } else if (options.body !== undefined) {
      init.body = JSON.stringify(options.body);
    }
    return init;
  }

  /** Run a single attempt under a timeout, classifying the outcome. */
  private async attemptFetch(
    url: string,
    init: RequestInit,
    timeout: number,
    signal: AbortSignal | undefined,
  ): Promise<FetchOutcome> {
    const timeoutController = new AbortController();
    const timer = setTimeout(() => timeoutController.abort(), timeout);
    const signals = signal
      ? [timeoutController.signal, signal]
      : [timeoutController.signal];
    try {
      const response = await this.config.fetch(url, {
        ...init,
        signal: anySignal(signals),
      });
      return { kind: "response", response };
    } catch (error) {
      return { kind: "error", error, timedOut: timeoutController.signal.aborted };
    } finally {
      clearTimeout(timer);
    }
  }

  private async send(
    options: RequestOptions,
    streaming: boolean,
  ): Promise<Response> {
    const url = this.buildURL(options.path, options.query);
    const init = this.buildRequestInit(options, streaming);
    const maxRetries = options.maxRetries ?? this.config.maxRetries;
    const timeout = options.timeout ?? this.config.timeout;

    for (let attempt = 0; ; attempt++) {
      const canRetry = attempt < maxRetries;
      const outcome = await this.attemptFetch(url, init, timeout, options.signal);
      const res =
        outcome.kind === "response"
          ? await this.handleResponse(outcome.response, attempt, canRetry, options.signal)
          : await this.handleError(outcome, options, url, timeout, attempt, canRetry);
      if (res) return res;
      // res === null means a retry was scheduled — loop again.
    }
  }

  /** Resolve a successful attempt: return the Response, retry, or throw. */
  private async handleResponse(
    res: Response,
    attempt: number,
    canRetry: boolean,
    signal: AbortSignal | undefined,
  ): Promise<Response | null> {
    if (res.ok) return res;
    if (RETRYABLE_STATUS.has(res.status) && canRetry) {
      await this.backoff(attempt, parseRetryAfter(res.headers), signal);
      return null;
    }
    throw AirforceError.fromResponse(res.status, await safeJson(res), res.headers);
  }

  /** Resolve a failed attempt: retry (return null) or throw a typed error. */
  private async handleError(
    outcome: FetchErrorOutcome,
    options: RequestOptions,
    url: string,
    timeout: number,
    attempt: number,
    canRetry: boolean,
  ): Promise<null> {
    if (options.signal?.aborted) {
      throw new AirforceError("Aborted", { cause: outcome.error });
    }
    // A network/timeout error leaves the outcome of a POST unknown — retrying could
    // double-charge a billable request. Only retry transport errors for idempotent
    // methods. (Retryable *status codes* are still retried for all methods, since the
    // server responded and a 4xx/5xx POST is not charged.)
    if (canRetry && options.method !== "POST") {
      await this.backoff(attempt, undefined, options.signal);
      return null;
    }
    throw outcome.timedOut
      ? new AirforceTimeoutError(
          `Request to ${options.path} timed out after ${timeout}ms`,
          outcome.error,
        )
      : new AirforceConnectionError(
          `Failed to reach ${url}: ${describeError(outcome.error)}`,
          outcome.error,
        );
  }

  private async backoff(
    attempt: number,
    retryAfterSecs: number | undefined,
    signal?: AbortSignal,
  ): Promise<void> {
    const base =
      retryAfterSecs !== undefined
        ? retryAfterSecs * 1000
        : Math.min(1000 * 2 ** attempt, 8000);
    const jitter = base * 0.25 * Math.random();
    await sleep(base + jitter, signal);
  }
}

function parseRetryAfter(headers: Headers): number | undefined {
  const v = headers.get("retry-after");
  if (!v) return undefined;
  const secs = Number(v);
  return Number.isFinite(secs) ? secs : undefined;
}

async function safeJson(res: Response): Promise<unknown> {
  const text = await res.text().catch(() => "");
  if (!text) return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/** Combine multiple abort signals into one (AbortSignal.any polyfill). */
function anySignal(signals: AbortSignal[]): AbortSignal {
  if (signals.length === 1) return signals[0]!;
  const anyFn = (AbortSignal as unknown as { any?: (s: AbortSignal[]) => AbortSignal }).any;
  if (typeof anyFn === "function") return anyFn(signals);
  const controller = new AbortController();
  for (const s of signals) {
    if (s.aborted) {
      controller.abort();
      break;
    }
    s.addEventListener("abort", () => controller.abort(), { once: true });
  }
  return controller.signal;
}
