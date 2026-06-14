/**
 * Google Gemini-compatible generation — `POST /v1beta/models/{model}:{method}`.
 * Translated server-side to chat completions.
 */

import type { Stream } from "../core/streaming";
import { APIResource, type RequestConfig } from "./resource";

export interface GeminiContent {
  role?: "user" | "model";
  parts: Array<Record<string, unknown>>;
}

export interface GeminiGenerateParams {
  contents: GeminiContent[];
  systemInstruction?: Record<string, unknown> | string;
  tools?: Array<Record<string, unknown>>;
  toolConfig?: Record<string, unknown>;
  generationConfig?: {
    temperature?: number;
    maxOutputTokens?: number;
    topP?: number;
    stopSequences?: string[];
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface GeminiResponse {
  candidates: Array<Record<string, unknown>>;
  usageMetadata?: Record<string, unknown>;
  modelVersion?: string;
}

export type GeminiStreamChunk = GeminiResponse;

export class Gemini extends APIResource {
  /** Non-streaming `generateContent`. */
  generateContent(
    model: string,
    params: GeminiGenerateParams,
    options: RequestConfig = {},
  ): Promise<GeminiResponse> {
    return this.transport.request<GeminiResponse>({
      method: "POST",
      path: `/v1beta/models/${encodeURIComponent(model)}:generateContent`,
      body: params,
      ...options,
    });
  }

  /** Streaming `streamGenerateContent`. */
  streamGenerateContent(
    model: string,
    params: GeminiGenerateParams,
    options: RequestConfig = {},
  ): Promise<Stream<GeminiStreamChunk>> {
    return this.transport.stream<GeminiStreamChunk>({
      method: "POST",
      path: `/v1beta/models/${encodeURIComponent(model)}:streamGenerateContent`,
      body: params,
      ...options,
    });
  }
}
