/**
 * Rerank — `POST /v1/rerank`.
 *
 * Scores documents against a query and returns them ordered by relevance,
 * typically after a vector search. Billed on input tokens only; no streaming.
 * Rerank models are the `/v1/models` rows with `media_type: "rerank"`.
 */

import { APIResource, type RequestConfig } from "./resource";

/** A plain string, or an object with a `text` field (forwarded unchanged). */
export type RerankDocument = string | { text: string; [key: string]: unknown };

export interface RerankCreateParams {
  /** Public rerank model name. */
  model: string;
  /** The search query the documents are scored against. */
  query: string;
  /** Up to 1,000 documents. */
  documents: RerankDocument[];
  /** Return only the n most relevant documents (all when omitted). */
  top_n?: number;
  /** Include each document in its result, not only its index. */
  return_documents?: boolean;
  /** Split long documents into at most this many chunks (model-specific). */
  max_chunks_per_doc?: number;
  /** Token overlap between chunks (model-specific). */
  overlap_tokens?: number;
  /** End-user identifier passed through to the provider. */
  user?: string;
  /** Pass-through for any field not modeled above. */
  [key: string]: unknown;
}

export interface RerankResult {
  /** Position of the document in the request's `documents` array. */
  index: number;
  relevance_score: number;
  document?: unknown;
  [key: string]: unknown;
}

/**
 * The model provider's body as received. Most models answer with `results`
 * and `usage`; a few name the usage field differently, so extra keys are kept.
 */
export interface RerankResponse {
  results: RerankResult[];
  usage?: Record<string, unknown>;
  [key: string]: unknown;
}

export class Rerank extends APIResource {
  /** Score `documents` against `query`. */
  create(params: RerankCreateParams, options: RequestConfig = {}): Promise<RerankResponse> {
    return this.transport.request({
      method: "POST",
      path: "/v1/rerank",
      body: params,
      ...options,
    });
  }
}
