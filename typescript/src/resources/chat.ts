/**
 * Chat completions — `POST /v1/chat/completions`.
 *
 * OpenAI-compatible, plus the airforce-specific `models` fallback array, `skill`
 * / `skills`, and `transforms`. Supports streaming and non-streaming.
 */

import type { Stream } from "../core/streaming";
import { APIResource, type RequestConfig } from "./resource";

export type ChatRole = "system" | "user" | "assistant" | "tool";

export interface ChatContentPartText {
  type: "text";
  text: string;
}
export interface ChatContentPartImage {
  type: "image_url";
  image_url: { url: string; detail?: "auto" | "low" | "high" };
}
export type ChatContentPart = ChatContentPartText | ChatContentPartImage;

export interface ChatMessage {
  role: ChatRole;
  content: string | ChatContentPart[] | null;
  /** Speaker name (optional, OpenAI semantics). */
  name?: string;
  /** Present on `assistant` messages that called tools. */
  tool_calls?: ToolCall[];
  /** Required on `tool` messages — the id of the call being answered. */
  tool_call_id?: string;
}

export interface FunctionDefinition {
  name: string;
  description?: string;
  parameters?: Record<string, unknown>;
}

export interface Tool {
  type: "function";
  function: FunctionDefinition;
}

export type ToolChoice =
  | "auto"
  | "none"
  | "required"
  | { type: "function"; function: { name: string } };

export interface ToolCall {
  index?: number;
  id: string;
  type: "function";
  function: { name: string; arguments: string };
}

export type ThinkingParam =
  | "on"
  | "off"
  | "auto"
  | { type: "enabled"; budget_tokens?: number };

export interface ChatCompletionCreateParamsBase {
  /** Public model name, e.g. `claude-opus-4.8`. */
  model: string;
  messages: ChatMessage[];
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  stop?: string | string[];
  tools?: Tool[];
  tool_choice?: ToolChoice;
  response_format?: { type: "text" | "json_object" };
  reasoning_effort?: "low" | "medium" | "high";
  thinking?: ThinkingParam;
  thinking_budget?: number;
  /** airforce: up to 3 fallback model names tried in order. */
  models?: string[];
  /** airforce: a single server-side skill to inject. */
  skill?: string;
  /** airforce: skill candidates (server applies up to 3). */
  skills?: string[];
  /** airforce: e.g. `["middle-out"]` to compress on context overflow. */
  transforms?: string[];
  /** airforce: ignore the user's saved per-model defaults. */
  ignore_defaults?: boolean;
  /** Pass-through for any field not modeled above. */
  [key: string]: unknown;
}

export interface ChatCompletionCreateParamsNonStreaming
  extends ChatCompletionCreateParamsBase {
  stream?: false;
}
export interface ChatCompletionCreateParamsStreaming
  extends ChatCompletionCreateParamsBase {
  stream: true;
}
export type ChatCompletionCreateParams =
  | ChatCompletionCreateParamsNonStreaming
  | ChatCompletionCreateParamsStreaming;

export interface CompletionUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  prompt_tokens_details?: { cached_tokens?: number };
  completion_tokens_details?: { reasoning_tokens?: number };
  cache_creation_input_tokens?: number;
  cache_creation?: {
    ephemeral_5m_input_tokens?: number;
    ephemeral_1h_input_tokens?: number;
  };
  /** airforce: request cost in credits (USD). */
  cost?: number;
}

export interface ChatCompletionChoice {
  index: number;
  message: {
    role: "assistant";
    content: string | null;
    reasoning?: string | null;
    tool_calls?: ToolCall[];
  };
  finish_reason: string | null;
}

export interface ChatCompletion {
  id: string;
  object: "chat.completion";
  created: number;
  model: string;
  choices: ChatCompletionChoice[];
  usage?: CompletionUsage;
}

export interface ChatCompletionChunkChoice {
  index: number;
  delta: {
    role?: "assistant";
    content?: string | null;
    reasoning?: string | null;
    tool_calls?: ToolCall[];
  };
  finish_reason: string | null;
}

export interface ChatCompletionChunk {
  id: string;
  object: "chat.completion.chunk";
  created: number;
  model: string;
  choices: ChatCompletionChunkChoice[];
  usage?: CompletionUsage;
}

export class Chat extends APIResource {
  /** Create a non-streaming chat completion. */
  create(
    params: ChatCompletionCreateParamsNonStreaming,
    options?: RequestConfig,
  ): Promise<ChatCompletion>;
  /** Create a streaming chat completion. */
  create(
    params: ChatCompletionCreateParamsStreaming,
    options?: RequestConfig,
  ): Promise<Stream<ChatCompletionChunk>>;
  create(
    params: ChatCompletionCreateParams,
    options: RequestConfig = {},
  ): Promise<ChatCompletion | Stream<ChatCompletionChunk>> {
    if (params.stream) {
      return this.transport.stream<ChatCompletionChunk>({
        method: "POST",
        path: "/v1/chat/completions",
        body: params,
        ...options,
      });
    }
    return this.transport.request<ChatCompletion>({
      method: "POST",
      path: "/v1/chat/completions",
      body: params,
      ...options,
    });
  }
}
