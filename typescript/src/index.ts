/**
 * Official TypeScript/JavaScript SDK for the api.airforce AI gateway.
 *
 * @packageDocumentation
 */

export { Airforce, type ClientOptions } from "./client";
export { Airforce as default } from "./client";

export { VERSION, DEFAULT_BASE_URL } from "./core/transport";
export type { RequestConfig } from "./resources/resource";

export {
  AirforceError,
  BadRequestError,
  AuthenticationError,
  InsufficientBalanceError,
  PermissionDeniedError,
  NotFoundError,
  ConflictError,
  UnprocessableEntityError,
  RateLimitError,
  InternalServerError,
  AirforceConnectionError,
  AirforceTimeoutError,
  MissingCredentialError,
  type ApiErrorBody,
} from "./core/errors";

export { Stream } from "./core/streaming";
export type { ServerSentEvent } from "./core/streaming";

export * from "./resources/chat";
export * from "./resources/messages";
export * from "./resources/responses";
export * from "./resources/gemini";
export * from "./resources/models";
export * from "./resources/images";
export * from "./resources/audio";
export * from "./resources/video";
export * from "./resources/voices";
export * from "./resources/account";
export * from "./resources/keys";
export * from "./resources/billing";
export * from "./resources/twofa";
export * from "./resources/auth";
export * from "./resources/oauth";
