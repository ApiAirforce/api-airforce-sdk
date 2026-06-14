/**
 * Error types raised by the Airforce SDK.
 *
 * Every HTTP error is mapped to an {@link AirforceError} subclass keyed on the
 * response status. Transport-level problems (no response) raise
 * {@link AirforceConnectionError} or {@link AirforceTimeoutError}.
 */

export interface ApiErrorBody {
  message?: string;
  type?: string;
  code?: string;
  param?: string | null;
}

/** Best-effort extraction of an error message/code from an arbitrary JSON body. */
function parseErrorBody(body: unknown): ApiErrorBody {
  if (typeof body === "string") return { message: body };
  if (body && typeof body === "object") {
    const obj = body as Record<string, unknown>;
    // OpenAI shape: { error: { message, type, code, param } }
    if (obj.error && typeof obj.error === "object") {
      return obj.error as ApiErrorBody;
    }
    // Flat shape: { error: "msg", message?: "..." } or { message, code }
    const message =
      (typeof obj.error === "string" ? obj.error : undefined) ??
      (typeof obj.message === "string" ? obj.message : undefined);
    return {
      message,
      code: typeof obj.code === "string" ? obj.code : undefined,
      type: typeof obj.type === "string" ? obj.type : undefined,
    };
  }
  return {};
}

export class AirforceError extends Error {
  /** HTTP status, or `undefined` for transport-level errors. */
  readonly status: number | undefined;
  /** Machine-readable error code (e.g. `free_tier_gated`), when provided. */
  readonly code: string | undefined;
  /** Error category from the API (e.g. `invalid_request_error`). */
  readonly type: string | undefined;
  /** Offending parameter, when the API reports one. */
  readonly param: string | null | undefined;
  /** `x-request-id` response header, when present. */
  readonly requestId: string | undefined;
  /** The raw, parsed response body. */
  readonly body: unknown;

  constructor(
    message: string,
    opts: {
      status?: number;
      code?: string;
      type?: string;
      param?: string | null;
      requestId?: string;
      body?: unknown;
      cause?: unknown;
    } = {},
  ) {
    super(message, opts.cause !== undefined ? { cause: opts.cause } : undefined);
    this.name = new.target.name;
    this.status = opts.status;
    this.code = opts.code;
    this.type = opts.type;
    this.param = opts.param;
    this.requestId = opts.requestId;
    this.body = opts.body;
  }

  /** Build the right subclass for an HTTP error response. */
  static fromResponse(
    status: number,
    body: unknown,
    headers?: Headers,
  ): AirforceError {
    const parsed = parseErrorBody(body);
    const requestId = headers?.get("x-request-id") ?? undefined;
    const message =
      parsed.message ?? `Airforce API error (HTTP ${status})`;
    const opts = {
      status,
      code: parsed.code,
      type: parsed.type,
      param: parsed.param,
      requestId,
      body,
    };

    switch (status) {
      case 400:
        return new BadRequestError(message, opts);
      case 401:
        return new AuthenticationError(message, opts);
      case 402:
        return new InsufficientBalanceError(message, opts);
      case 403:
        return new PermissionDeniedError(message, opts);
      case 404:
        return new NotFoundError(message, opts);
      case 409:
        return new ConflictError(message, opts);
      case 422:
        return new UnprocessableEntityError(message, opts);
      case 429:
        return new RateLimitError(message, opts);
      default:
        if (status >= 500) return new InternalServerError(message, opts);
        return new AirforceError(message, opts);
    }
  }
}

/** 400 — malformed request. */
export class BadRequestError extends AirforceError {}
/** 401 — missing or invalid credentials. */
export class AuthenticationError extends AirforceError {}
/** 402 — not enough balance/credits to serve the request. */
export class InsufficientBalanceError extends AirforceError {}
/** 403 — authenticated but not allowed (includes `free_tier_gated`). */
export class PermissionDeniedError extends AirforceError {}
/** 404 — resource not found (or not owned by the caller). */
export class NotFoundError extends AirforceError {}
/** 409 — conflict (e.g. already subscribed to a plan). */
export class ConflictError extends AirforceError {}
/** 422 — semantically invalid request. */
export class UnprocessableEntityError extends AirforceError {}
/** 429 — rate limited. Inspect {@link RateLimitError.retryAfter}. */
export class RateLimitError extends AirforceError {
  /** Seconds to wait before retrying, parsed from `Retry-After` / `retry_after`. */
  get retryAfter(): number | undefined {
    const b = this.body as { retry_after?: number } | undefined;
    return typeof b?.retry_after === "number" ? b.retry_after : undefined;
  }
}
/** 5xx — upstream/server failure. */
export class InternalServerError extends AirforceError {}

/** No HTTP response was received (DNS, TCP, TLS, fetch failure). */
export class AirforceConnectionError extends AirforceError {
  constructor(message = "Connection error", cause?: unknown) {
    super(message, { cause });
  }
}

/** The request exceeded the configured timeout. */
export class AirforceTimeoutError extends AirforceError {
  constructor(message = "Request timed out", cause?: unknown) {
    super(message, { cause });
  }
}

/** A required credential was not configured for the requested endpoint. */
export class MissingCredentialError extends AirforceError {}
