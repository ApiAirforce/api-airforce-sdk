package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/** Two-factor authentication — {@code /api/2fa/*}. */
public final class TwoFactorResource extends Resource {

  TwoFactorResource(Transport transport) {
    super(transport);
  }

  public JsonNode setupInit() {
    return transport.post("/api/2fa/setup-init", "session", null);
  }

  public JsonNode setupVerify(String code) {
    return transport.post("/api/2fa/setup-verify", "session", Collections.singletonMap("code", code));
  }

  public JsonNode disable(String password, String code) {
    Map<String, Object> body = new HashMap<>();
    body.put("password", password);
    body.put("code", code);
    return transport.post("/api/2fa/disable", "session", body);
  }

  public JsonNode regenerateBackupCodes(String code) {
    return transport.post("/api/2fa/regenerate-backup-codes", "session", Collections.singletonMap("code", code));
  }

  public JsonNode verifyStepUp(String code) {
    return transport.post("/api/2fa/verify-step-up", "session", Collections.singletonMap("code", code));
  }

  public JsonNode stepUpStatus() {
    return transport.get("/api/2fa/step-up-status", "session", null);
  }
}
