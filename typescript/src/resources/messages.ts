/**
 * Anthropic-compatible Messages — `POST /v1/messages` and
 * `POST /v1/messages/count_tokens`.
 */

import type { Stream } from "../core/streaming";
import { APIResource, type RequestConfig } from "./resource";

export type AnthropicRole = "user" | "assistant";

export interface CacheControl {
  type: "ephemeral";
  ttl?: "5m" | "1h";
}

export interface TextBlock {
  type: "text";
  text: string;
  cache_control?: CacheControl;
}
export interface ImageBlock {
  type: "image";
  source:
    | { type: "base64"; media_type: string; data: string }
    | { type: "url"; url: string };
  cache_control?: CacheControl;
}
export interface ThinkingBlock {
  type: "thinking";
  thinking: string;
  signature?: string;
}
export interface ToolUseBlock {
  type: "tool_use";
  id: string;
  name: string;
  input: Record<string, unknown>;
}
export interface ToolResultBlock {
  type: "tool_result";
  tool_use_id: string;
  content: string | Array<TextBlock | ImageBlock>;
  is_error?: boolean;
  cache_control?: CacheControl;
}
export type ContentBlock =
  | TextBlock
  | ImageBlock
  | ThinkingBlock
  | ToolUseBlock
  | ToolResultBlock;

export interface AnthropicMessage {
  role: AnthropicRole;
  content: string | ContentBlock[];
}

export interface AnthropicTool {
  name: string;
  description?: string;
  input_schema: Record<string, unknown>;
  cache_control?: CacheControl;
}

export type AnthropicToolChoice =
  | { type: "auto" }
  | { type: "any" }
  | { type: "tool"; name: string };

export interface MessageCreateParamsBase {
  model: string;
  messages: AnthropicMessage[];
  max_tokens: number;
  system?: string | TextBlock[];
  temperature?: number;
  top_p?: number;
  top_k?: number;
  stop_sequences?: string[];
  tools?: AnthropicTool[];
  tool_choice?: AnthropicToolChoice;
  thinking?: { type: "enabled"; budget_tokens: number };
  /** airforce: fallback models (Anthropic form). */
  fallbacks?: Array<{ model: string }>;
  /** airforce: fallback models (plain form), up to 3. */
  models?: string[];
  [key: string]: unknown;
}

export interface MessageCreateParamsNonStreaming
  extends MessageCreateParamsBase {
  stream?: false;
}
export interface MessageCreateParamsStreaming extends MessageCreateParamsBase {
  stream: true;
}
export type MessageCreateParams =
  | MessageCreateParamsNonStreaming
  | MessageCreateParamsStreaming;

export interface AnthropicUsage {
  input_tokens: number;
  output_tokens: number;
  cache_read_input_tokens?: number;
  cache_creation_input_tokens?: number;
  cache_creation?: {
    ephemeral_5m_input_tokens?: number;
    ephemeral_1h_input_tokens?: number;
  };
  /** airforce: request cost in credits (USD). */
  cost?: number;
}

export interface Message {
  id: string;
  type: "message";
  role: "assistant";
  content: Array<TextBlock | ThinkingBlock | ToolUseBlock>;
  model: string;
  stop_reason: string | null;
  stop_sequence: string | null;
  usage: AnthropicUsage;
}

/** A streaming Messages event (`message_start`, `content_block_delta`, …). */
export interface MessageStreamEvent {
  type: string;
  [key: string]: unknown;
}

export interface CountTokensParams {
  model?: string;
  messages: AnthropicMessage[];
  system?: string | TextBlock[];
  tools?: AnthropicTool[];
}

export class Messages extends APIResource {
  /** Create a non-streaming message. */
  create(
    params: MessageCreateParamsNonStreaming,
    options?: RequestConfig,
  ): Promise<Message>;
  /** Create a streaming message. */
  create(
    params: MessageCreateParamsStreaming,
    options?: RequestConfig,
  ): Promise<Stream<MessageStreamEvent>>;
  create(
    params: MessageCreateParams,
    options: RequestConfig = {},
  ): Promise<Message | Stream<MessageStreamEvent>> {
    if (params.stream) {
      return this.transport.stream<MessageStreamEvent>({
        method: "POST",
        path: "/v1/messages",
        body: params,
        ...options,
      });
    }
    return this.transport.request<Message>({
      method: "POST",
      path: "/v1/messages",
      body: params,
      ...options,
    });
  }

  /** Estimate the token count of a prompt without calling upstream. */
  countTokens(
    params: CountTokensParams,
    options: RequestConfig = {},
  ): Promise<{ input_tokens: number }> {
    return this.transport.request({
      method: "POST",
      path: "/v1/messages/count_tokens",
      body: params,
      ...options,
    });
  }
}
