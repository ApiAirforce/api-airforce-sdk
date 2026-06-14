package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** OAuth 2.0 provider flow + self-service app management. */
public final class OAuthResource extends Resource {

  private static final Base64.Encoder B64URL = Base64.getUrlEncoder().withoutPadding();

  OAuthResource(Transport transport) {
    super(transport);
  }

  /** Generate a PKCE verifier/challenge pair (S256). Keys: verifier, challenge, method. */
  public static Map<String, String> createPkcePair() {
    byte[] random = new byte[32];
    new SecureRandom().nextBytes(random);
    String verifier = B64URL.encodeToString(random);
    byte[] digest;
    try {
      digest = MessageDigest.getInstance("SHA-256").digest(verifier.getBytes(StandardCharsets.US_ASCII));
    } catch (Exception e) {
      throw new AirforceException("airforce: SHA-256 unavailable");
    }
    Map<String, String> pair = new LinkedHashMap<>();
    pair.put("verifier", verifier);
    pair.put("challenge", B64URL.encodeToString(digest));
    pair.put("method", "S256");
    return pair;
  }

  /**
   * Build the {@code /oauth/authorize} URL to redirect a user to. Params: client_id,
   * redirect_uri (required); scope (String or List), state, code_challenge,
   * code_challenge_method.
   */
  public String authorizeUrl(Map<String, Object> params) {
    StringBuilder q = new StringBuilder(transport.baseUrl()).append("/oauth/authorize?");
    q.append("response_type=code");
    appendParam(q, "client_id", params.get("client_id"));
    appendParam(q, "redirect_uri", params.get("redirect_uri"));
    Object scope = params.get("scope");
    if (scope instanceof List) {
      appendParam(q, "scope", String.join(" ", ((List<?>) scope).stream().map(String::valueOf).toArray(String[]::new)));
    } else if (scope != null) {
      appendParam(q, "scope", scope);
    }
    appendParam(q, "state", params.get("state"));
    Object challenge = params.get("code_challenge");
    if (challenge != null) {
      appendParam(q, "code_challenge", challenge);
      Object method = params.getOrDefault("code_challenge_method", "S256");
      appendParam(q, "code_challenge_method", method);
    }
    return q.toString();
  }

  private static void appendParam(StringBuilder q, String key, Object value) {
    if (value == null) {
      return;
    }
    q.append('&').append(key).append('=')
        .append(URLEncoder.encode(String.valueOf(value), StandardCharsets.UTF_8));
  }

  /** Exchange an authorization code for an access token. */
  public JsonNode exchangeToken(Map<String, String> params) {
    Map<String, String> form = new LinkedHashMap<>();
    form.put("grant_type", "authorization_code");
    params.forEach((k, v) -> {
      if (v != null) {
        form.put(k, v);
      }
    });
    return form("/oauth/token", form);
  }

  /** Fetch the profile for an access token. */
  public JsonNode userInfo(String accessToken) {
    Transport.RequestSpec spec = new Transport.RequestSpec();
    spec.auth = "none";
    spec.headers = java.util.Collections.singletonMap("authorization", "Bearer " + accessToken);
    return transport.requestJson("GET", "/oauth/userinfo", spec);
  }

  /** Revoke an access token. */
  public JsonNode revokeToken(String token) {
    return form("/oauth/revoke", java.util.Collections.singletonMap("token", token));
  }

  public JsonNode listApps() {
    return transport.get("/api/me/oauth-apps", "session", null);
  }

  public JsonNode createApp(Map<String, Object> params) {
    return transport.post("/api/me/oauth-apps", "session", params);
  }

  public JsonNode getApp(String clientId) {
    return transport.get("/api/me/oauth-apps/" + enc(clientId), "session", null);
  }

  public JsonNode updateApp(String clientId, Map<String, Object> patch) {
    return transport.method("PATCH", "/api/me/oauth-apps/" + enc(clientId), "session", patch);
  }

  public JsonNode deleteApp(String clientId) {
    return transport.delete("/api/me/oauth-apps/" + enc(clientId), "session");
  }

  public JsonNode rotateSecret(String clientId) {
    return transport.post("/api/me/oauth-apps/" + enc(clientId) + "/rotate-secret", "session", null);
  }

  public JsonNode connectedApps() {
    return transport.get("/api/me/connected-apps", "session", null);
  }

  public JsonNode revokeConnectedApp(String clientId) {
    return transport.delete("/api/me/connected-apps/" + enc(clientId), "session");
  }

  private JsonNode form(String path, Map<String, String> fields) {
    StringBuilder encoded = new StringBuilder();
    for (Map.Entry<String, String> e : fields.entrySet()) {
      if (encoded.length() > 0) {
        encoded.append('&');
      }
      encoded.append(URLEncoder.encode(e.getKey(), StandardCharsets.UTF_8))
          .append('=')
          .append(URLEncoder.encode(e.getValue(), StandardCharsets.UTF_8));
    }
    Transport.RequestSpec spec = new Transport.RequestSpec();
    spec.auth = "none";
    spec.rawBody = encoded.toString().getBytes(StandardCharsets.UTF_8);
    spec.contentType = "application/x-www-form-urlencoded";
    return transport.requestJson("POST", path, spec);
  }
}
