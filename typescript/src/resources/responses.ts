/**
 * OpenAI Responses-API-compatible endpoint — `POST /v1/responses`.
 * Translated server-side to chat completions. No `models` fallback support.
 */

import type { Stream } from "../core/streaming";
import { APIResource, type RequestConfig } from "./resource";
import type { Tool, ToolChoice } from "./chat";

export interface ResponseCreateParamsBase {
  model: string;
  input: string | Array<Record<string, unknown>>;
  instructions?: string;
  tools?: Tool[];
  tool_choice?: ToolChoice;
  max_output_tokens?: number;
  temperature?: number;
  top_p?: number;
  reasoning?: { effort?: "low" | "medium" | "high" };
  [key: string]: unknown;
}

export interface ResponseCreateParamsNonStreaming
  extends ResponseCreateParamsBase {
  stream?: false;
}
export interface ResponseCreateParamsStreaming extends ResponseCreateParamsBase {
  stream: true;
}
export type ResponseCreateParams =
  | ResponseCreateParamsNonStreaming
  | ResponseCreateParamsStreaming;

export interface ResponsesUsage {
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  input_tokens_details?: { cached_tokens?: number };
  output_tokens_details?: { reasoning_tokens?: number };
}

export interface OpenAIResponse {
  id: string;
  object: "response";
  created_at: number;
  status: "completed" | "incomplete" | string;
  output: Array<Record<string, unknown>>;
  usage?: ResponsesUsage;
  [key: string]: unknown;
}

/** A streaming Responses event (`response.output_text.delta`, …). */
export interface ResponseStreamEvent {
  type: string;
  sequence_number?: number;
  [key: string]: unknown;
}

export class Responses extends APIResource {
  create(
    params: ResponseCreateParamsNonStreaming,
    options?: RequestConfig,
  ): Promise<OpenAIResponse>;
  create(
    params: ResponseCreateParamsStreaming,
    options?: RequestConfig,
  ): Promise<Stream<ResponseStreamEvent>>;
  create(
    params: ResponseCreateParams,
    options: RequestConfig = {},
  ): Promise<OpenAIResponse | Stream<ResponseStreamEvent>> {
    if (params.stream) {
      return this.transport.stream<ResponseStreamEvent>({
        method: "POST",
        path: "/v1/responses",
        body: params,
        ...options,
      });
    }
    return this.transport.request<OpenAIResponse>({
      method: "POST",
      path: "/v1/responses",
      body: params,
      ...options,
    });
  }
}
