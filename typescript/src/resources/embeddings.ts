/**
 * Embeddings — `POST /v1/embeddings`.
 *
 * OpenAI-compatible embeddings with smart routing + provider fallback. Billed
 * on input tokens only (embeddings produce no completion); no streaming.
 */

import { APIResource, type RequestConfig } from "./resource";

/** A single string, a batch of strings, or pre-tokenized input. */
export type EmbeddingInput = string | string[] | number[] | number[][];

export interface EmbeddingCreateParams {
  /** Public model name. */
  model: string;
  /** Text(s) or token array(s) to embed. Must be non-empty (400 otherwise). */
  input: EmbeddingInput;
  /** `float` (default) returns number arrays; `base64` returns encoded strings. */
  encoding_format?: "float" | "base64";
  /** Reduce the output dimensionality (models that support it). */
  dimensions?: number;
  /** End-user identifier passed through to the provider. */
  user?: string;
  /** Pass-through for any field not modeled above. */
  [key: string]: unknown;
}

export interface Embedding {
  object: "embedding";
  index: number;
  /** Number array (`float`) or base64-encoded string (`base64`). */
  embedding: number[] | string;
}

export interface EmbeddingsResponse {
  object: "list";
  data: Embedding[];
  model: string;
  usage: { prompt_tokens: number; total_tokens: number };
}

export class Embeddings extends APIResource {
  /**
   * Create embeddings for the given input. Returns the upstream OpenAI shape
   * verbatim. `503` (`api_error`) when the model is temporarily unavailable,
   * `404` for unknown models, `400` on empty input.
   */
  create(
    params: EmbeddingCreateParams,
    options: RequestConfig = {},
  ): Promise<EmbeddingsResponse> {
    return this.transport.request({
      method: "POST",
      path: "/v1/embeddings",
      body: params,
      ...options,
    });
  }
}
