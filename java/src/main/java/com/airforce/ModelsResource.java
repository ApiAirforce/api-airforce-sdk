package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Collections;
import java.util.Map;

/** Model catalog / discovery. */
public final class ModelsResource extends Resource {

  ModelsResource(Transport transport) {
    super(transport);
  }

  /** List public models. The returned node is the {@code data} array. */
  public JsonNode list(boolean channels) {
    Map<String, String> query = channels ? Collections.singletonMap("channels", "1") : null;
    JsonNode res = transport.get("/v1/models", "none", query);
    return res != null && res.has("data") ? res.get("data") : res;
  }

  /**
   * One model, the same entry {@link #list} returns for it ({@code GET /v1/models/{model}}). Ids
   * with slashes such as {@code BAAI/bge-reranker-v2-m3} keep their slashes; each segment is
   * percent-encoded. An unknown id throws the API's 404 error.
   */
  public JsonNode retrieve(String model) {
    StringBuilder path = new StringBuilder("/v1/models");
    for (String part : model.split("/", -1)) {
      path.append('/').append(enc(part));
    }
    return transport.get(path.toString(), "none", null);
  }

  /** Per-model analytics + channel breakdown. */
  public JsonNode detail(String model) {
    return transport.get("/api/models/" + enc(model) + "/detail", "none", null);
  }

  /** Effective parameter bounds for a model. */
  public JsonNode allowedParams(String model) {
    return transport.get("/api/models/" + enc(model) + "/allowed-params", "none", null);
  }

  /** Cheapest / smartest / fastest playground buckets. */
  public JsonNode classes() {
    return transport.get("/v1/playground/model-classes", "none", null);
  }
}
