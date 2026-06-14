package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

/** Google Gemini-compatible generation — {@code POST /v1beta/models/{model}:{method}}. */
public final class GeminiResource extends Resource {

  GeminiResource(Transport transport) {
    super(transport);
  }

  /** Non-streaming {@code generateContent}. {@code params} requires {@code contents}. */
  public JsonNode generateContent(String model, Map<String, Object> params) {
    return transport.post("/v1beta/models/" + enc(model) + ":generateContent", "api_key", params);
  }

  /** Streaming {@code streamGenerateContent}. */
  public Stream streamGenerateContent(String model, Map<String, Object> params) {
    return transport.postStream("/v1beta/models/" + enc(model) + ":streamGenerateContent", "api_key", params);
  }
}
