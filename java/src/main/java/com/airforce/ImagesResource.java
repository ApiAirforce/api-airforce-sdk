package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;

/** Image generation — {@code POST /v1/images/generations}. */
public final class ImagesResource extends Resource {

  ImagesResource(Transport transport) {
    super(transport);
  }

  /** Generate one or more images. Requires {@code model} and {@code prompt}. */
  public JsonNode generate(Map<String, Object> params) {
    return transport.post("/v1/images/generations", "api_key", params);
  }
}
