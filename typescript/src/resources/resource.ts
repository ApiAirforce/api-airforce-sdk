import type { Transport } from "../core/transport";

/** Per-call overrides accepted by every resource method. */
export interface RequestConfig {
  /** Override the client timeout for this call (ms). */
  timeout?: number;
  /** Override the client retry count for this call. */
  maxRetries?: number;
  /** Abort signal to cancel the request (and any stream it opens). */
  signal?: AbortSignal;
  /** Extra headers merged onto this request. */
  headers?: Record<string, string>;
}

/** Base class wiring a resource to the shared {@link Transport}. */
export abstract class APIResource {
  constructor(protected readonly transport: Transport) {}
}
