package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

/** API key provisioning — {@code /v1/keys}. */
public final class KeysResource extends Resource {

  KeysResource(Transport transport) {
    super(transport);
  }

  /** Create a secondary key. The full key is returned only here. */
  public JsonNode create(Map<String, Object> params) {
    return transport.post("/v1/keys", "api_key", params);
  }

  /** List secondary keys (masked; returns the {@code keys} array). */
  public JsonNode list() {
    JsonNode res = transport.get("/v1/keys", "api_key", null);
    return res != null && res.has("keys") ? res.get("keys") : res;
  }

  /** Update a secondary key's settings. */
  public JsonNode update(String key, Map<String, Object> params) {
    return transport.method("PATCH", "/v1/keys/" + enc(key), "api_key", params);
  }

  /** Delete a secondary key. */
  public JsonNode delete(String key) {
    return transport.delete("/v1/keys/" + enc(key), "api_key");
  }
}
