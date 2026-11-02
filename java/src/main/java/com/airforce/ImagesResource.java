package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Image generation — {@code POST /v1/images/generations} — and edits — {@code POST
 * /v1/images/edits}.
 */
public final class ImagesResource extends Resource {

  ImagesResource(Transport transport) {
    super(transport);
  }

  /** Generate one or more images. Requires {@code model} and {@code prompt}. */
  public JsonNode generate(Map<String, Object> params) {
    return transport.post("/v1/images/generations", "api_key", params);
  }

  /**
   * Edit or vary input image(s) (multipart). {@code fields} must include {@code model} and
   * {@code prompt}; optional n, size, aspect_ratio, quality, response_format. {@code images}
   * maps file name to bytes, at least one and at most 16, 25 MB each; each becomes one {@code
   * image} part. {@code mask} (file name to bytes) may be null. Same models, prices and response
   * shape as {@link #generate}.
   */
  public JsonNode edit(
      Map<String, String> fields,
      List<Map.Entry<String, byte[]>> images,
      Map.Entry<String, byte[]> mask) {
    List<Multipart.FilePart> parts = new ArrayList<>();
    for (Map.Entry<String, byte[]> img : images) {
      parts.add(new Multipart.FilePart("image", img.getKey(), img.getValue()));
    }
    if (mask != null) {
      parts.add(new Multipart.FilePart("mask", mask.getKey(), mask.getValue()));
    }
    Multipart m = Multipart.build(fields, parts);
    Transport.RequestSpec spec = new Transport.RequestSpec();
    spec.auth = "api_key";
    spec.rawBody = m.body;
    spec.contentType = m.contentType;
    return transport.requestJson("POST", "/v1/images/edits", spec);
  }
}
