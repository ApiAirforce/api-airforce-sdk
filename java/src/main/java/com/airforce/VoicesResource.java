package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Voice cloning — {@code /v1/voices/*}. */
public final class VoicesResource extends Resource {

  VoicesResource(Transport transport) {
    super(transport);
  }

  /** Current consent paragraph + hash (public, no auth). */
  public JsonNode consentText() {
    return transport.get("/v1/voices/consent-text", "none", null);
  }

  /** Create a cloned voice from one or more audio samples. */
  public JsonNode clone(String name, String consentHash, List<Multipart.FilePart> samples, Map<String, String> extra) {
    Map<String, String> fields = new HashMap<>();
    fields.put("name", name);
    fields.put("consent_hash", consentHash);
    if (extra != null) {
      fields.putAll(extra);
    }
    List<Multipart.FilePart> files = new ArrayList<>();
    for (Multipart.FilePart sample : samples) {
      files.add(new Multipart.FilePart("files", sample.filename, sample.data));
    }
    Multipart m = Multipart.build(fields, files);
    Transport.RequestSpec spec = new Transport.RequestSpec();
    spec.auth = "api_key";
    spec.rawBody = m.body;
    spec.contentType = m.contentType;
    return transport.requestJson("POST", "/v1/voices/clone", spec);
  }

  /** List the caller's cloned voices (returns the {@code voices} array). */
  public JsonNode library() {
    JsonNode res = transport.get("/v1/voices/library", "api_key", null);
    return res != null && res.has("voices") ? res.get("voices") : res;
  }

  /** Rename or re-describe a cloned voice. */
  public JsonNode update(String voiceId, Map<String, Object> body) {
    return transport.method("PATCH", "/v1/voices/clone/" + enc(voiceId), "api_key", body);
  }

  /** Delete a cloned voice. */
  public JsonNode delete(String voiceId) {
    return transport.delete("/v1/voices/clone/" + enc(voiceId), "api_key");
  }

  /** Helper to build a sample part from raw bytes. */
  public static Multipart.FilePart sample(String filename, byte[] data) {
    return new Multipart.FilePart("files", filename, data);
  }
}
