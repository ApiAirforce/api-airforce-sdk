package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

/** Anthropic-compatible messages — {@code POST /v1/messages}. */
public final class MessagesResource extends Resource {

  MessagesResource(Transport transport) {
    super(transport);
  }

  /** Create a non-streaming message. Requires {@code model}, {@code messages}, {@code max_tokens}. */
  public JsonNode create(Map<String, Object> params) {
    return transport.post("/v1/messages", "api_key", with(params, "stream", false));
  }

  /** Create a streaming message. */
  public Stream createStream(Map<String, Object> params) {
    return transport.postStream("/v1/messages", "api_key", with(params, "stream", true));
  }

  /** Estimate the token count of a prompt locally (no upstream call). */
  public JsonNode countTokens(Map<String, Object> params) {
    return transport.post("/v1/messages/count_tokens", "api_key", params);
  }
}
