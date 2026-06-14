import { describe, expect, it } from "vitest";
import {
  AirforceError,
  AuthenticationError,
  ConflictError,
  InsufficientBalanceError,
  InternalServerError,
  PermissionDeniedError,
  RateLimitError,
} from "../src/core/errors";

describe("AirforceError.fromResponse", () => {
  it("maps status codes to subclasses", () => {
    expect(AirforceError.fromResponse(401, {})).toBeInstanceOf(AuthenticationError);
    expect(AirforceError.fromResponse(402, {})).toBeInstanceOf(InsufficientBalanceError);
    expect(AirforceError.fromResponse(403, {})).toBeInstanceOf(PermissionDeniedError);
    expect(AirforceError.fromResponse(409, {})).toBeInstanceOf(ConflictError);
    expect(AirforceError.fromResponse(429, {})).toBeInstanceOf(RateLimitError);
    expect(AirforceError.fromResponse(503, {})).toBeInstanceOf(InternalServerError);
  });

  it("extracts the OpenAI-shaped error body", () => {
    const err = AirforceError.fromResponse(403, {
      error: { message: "blocked", code: "free_tier_gated", type: "forbidden" },
    });
    expect(err.message).toBe("blocked");
    expect(err.code).toBe("free_tier_gated");
    expect(err.type).toBe("forbidden");
    expect(err.status).toBe(403);
  });

  it("extracts the flat error body", () => {
    const err = AirforceError.fromResponse(400, { error: "bad thing" });
    expect(err.message).toBe("bad thing");
  });

  it("exposes retryAfter on rate-limit errors", () => {
    const err = AirforceError.fromResponse(429, { retry_after: 12 });
    expect(err).toBeInstanceOf(RateLimitError);
    expect((err as RateLimitError).retryAfter).toBe(12);
  });

  it("reads x-request-id from headers", () => {
    const headers = new Headers({ "x-request-id": "req_abc" });
    const err = AirforceError.fromResponse(500, {}, headers);
    expect(err.requestId).toBe("req_abc");
  });
});
