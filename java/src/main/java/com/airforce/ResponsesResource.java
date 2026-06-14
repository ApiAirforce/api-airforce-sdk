package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

/** OpenAI Responses API — {@code POST /v1/responses}. */
public final class ResponsesResource extends Resource {

  ResponsesResource(Transport transport) {
    super(transport);
  }

  /** Create a non-streaming response. Requires {@code model} and {@code input}. */
  public JsonNode create(Map<String, Object> params) {
    return transport.post("/v1/responses", "api_key", with(params, "stream", false));
  }

  /** Create a streaming response. */
  public Stream createStream(Map<String, Object> params) {
    return transport.postStream("/v1/responses", "api_key", with(params, "stream", true));
  }
}
