package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

/** Chat completions — {@code POST /v1/chat/completions}. */
public final class ChatResource extends Resource {

  ChatResource(Transport transport) {
    super(transport);
  }

  /**
   * Create a non-streaming chat completion. {@code params} must include {@code model} and
   * {@code messages}; optional keys: max_tokens, temperature, top_p, stop, tools,
   * tool_choice, response_format, reasoning_effort, thinking, reasoning, {@code models}
   * (fallback), skill, skills, transforms.
   *
   * <p>{@code reasoning} ({@code {format?: 'separate'|'inline', exclude?: bool}}) shapes
   * how reasoning appears in the response; it is consumed server-side and never forwarded
   * upstream. {@code 'separate'} moves reasoning into {@code message.reasoning} /
   * {@code delta.reasoning} and strips it from {@code content}; {@code exclude: true}
   * drops reasoning entirely; absent or {@code 'inline'} keeps it wrapped in
   * {@code <think>...</think>} inside {@code content}.
   */
  public JsonNode create(Map<String, Object> params) {
    return transport.post("/v1/chat/completions", "api_key", with(params, "stream", false));
  }

  /** Create a streaming chat completion. */
  public Stream createStream(Map<String, Object> params) {
    return transport.postStream("/v1/chat/completions", "api_key", with(params, "stream", true));
  }
}
