package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

/** Embeddings — {@code POST /v1/embeddings}. */
public final class EmbeddingsResource extends Resource {

  EmbeddingsResource(Transport transport) {
    super(transport);
  }

  /**
   * Create embeddings. {@code params} must include {@code model} and a non-empty
   * {@code input} (string, string[], int[] or int[][]); optional keys: encoding_format,
   * dimensions, user. Billed on input tokens only; no streaming. Returns the OpenAI shape
   * {@code {object:'list', data:[{embedding, index}], model, usage}}.
   */
  public JsonNode create(Map<String, Object> params) {
    return transport.post("/v1/embeddings", "api_key", params);
  }
}
