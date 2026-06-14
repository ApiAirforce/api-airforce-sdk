package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Authentication — {@code /auth/*}. On successful login/signup the session token is parsed
 * from the response cookie and adopted by the client automatically.
 */
public final class AuthResource extends Resource {

  AuthResource(Transport transport) {
    super(transport);
  }

  private JsonNode submit(String path, Map<String, Object> body, Map<String, String> headers) {
    Transport.RequestSpec spec = new Transport.RequestSpec();
    spec.auth = "none";
    spec.jsonBody = body;
    spec.headers = headers;
    Transport.JsonAndCookie result = transport.requestJsonCookie("POST", path, spec);
    if (result.sessionCookie != null) {
      transport.setSessionToken(result.sessionCookie);
      if (result.json instanceof ObjectNode) {
        ((ObjectNode) result.json).put("session_token", result.sessionCookie);
      }
    }
    return result.json;
  }

  public JsonNode signup(Map<String, Object> params) {
    return submit("/auth/signup", params, null);
  }

  public JsonNode signupPrecheck(Map<String, Object> params) {
    return transport.post("/auth/signup/precheck", "none", params);
  }

  /** Log in. May return a 2FA challenge ({@code requires_2fa}, {@code challenge_token}). */
  public JsonNode login(String username, String password, String captchaToken) {
    Map<String, Object> body = new HashMap<>();
    body.put("username", username);
    body.put("password", password);
    body.put("captcha_token", captchaToken);
    return submit("/auth/login", body, null);
  }

  /** Complete a 2FA login with the challenge token. */
  public JsonNode verify2fa(String challengeToken, String code, String backupCode) {
    Map<String, Object> body = new HashMap<>();
    body.put("code", code);
    if (backupCode != null) {
      body.put("backup_code", backupCode);
    }
    return submit("/auth/2fa/verify", body, Collections.singletonMap("authorization", "Bearer " + challengeToken));
  }

  public JsonNode verifyEmail(String token) {
    return transport.post("/auth/verify", "none", Collections.singletonMap("token", token));
  }

  public JsonNode resendVerification(String identifier) {
    return transport.post("/auth/resend-verification", "none", Collections.singletonMap("identifier", identifier));
  }

  public JsonNode logout() {
    JsonNode result = transport.post("/auth/logout", "session", null);
    transport.setSessionToken(null);
    return result;
  }
}
