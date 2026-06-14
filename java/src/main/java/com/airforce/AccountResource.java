package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Account self-service — {@code /api/me}, {@code /api/user/*}. */
public final class AccountResource extends Resource {

  AccountResource(Transport transport) {
    super(transport);
  }

  public JsonNode me() {
    return transport.get("/api/me", "session", null);
  }

  public JsonNode usage() {
    return transport.get("/api/usage", "session", null);
  }

  public JsonNode myUsage() {
    return transport.get("/api/my-usage", "session", null);
  }

  public JsonNode update(Map<String, Object> params) {
    return transport.method("PUT", "/api/user/update", "session", params);
  }

  public JsonNode requestPasswordReset(String email, String locale) {
    Map<String, Object> body = new HashMap<>();
    body.put("email", email);
    if (locale != null) {
      body.put("locale", locale);
    }
    return transport.post("/api/auth/request-password-reset", "none", body);
  }

  public JsonNode resetPassword(String token, String newPassword) {
    Map<String, Object> body = new HashMap<>();
    body.put("token", token);
    body.put("new_password", newPassword);
    return transport.post("/api/auth/reset-password", "none", body);
  }

  public JsonNode referralCode() {
    return transport.get("/api/referral/code", "session", null);
  }

  public JsonNode referredUsers() {
    return transport.get("/api/referral/referred-users", "session", null);
  }

  public JsonNode getPriceCaps() {
    return transport.get("/api/user/price-caps", "session", null);
  }

  public JsonNode setPriceCaps(Map<String, Object> caps) {
    return transport.method("PUT", "/api/user/price-caps", "session",
        Collections.singletonMap("caps", caps));
  }

  public JsonNode deletePriceCap(String model) {
    return transport.delete("/api/user/price-caps/" + enc(model), "session");
  }

  public JsonNode getModelAliases() {
    return transport.get("/api/user/model-aliases", "session", null);
  }

  public JsonNode setModelAlias(String alias, String model) {
    Map<String, Object> body = new HashMap<>();
    body.put("alias", alias);
    body.put("model", model);
    return transport.method("PUT", "/api/user/model-aliases", "session", body);
  }

  public JsonNode setModelAliasesBatch(List<Map<String, String>> aliases) {
    return transport.method("PUT", "/api/user/model-aliases/batch", "session", aliases);
  }

  public JsonNode deleteModelAlias(String alias) {
    return transport.delete("/api/user/model-aliases/" + enc(alias), "session");
  }

  public JsonNode getModelDefaults() {
    return transport.get("/api/user/model-defaults", "session", null);
  }

  public JsonNode setModelDefault(String model, Map<String, Object> def) {
    return transport.method("PUT", "/api/user/model-defaults/" + enc(model), "session", def);
  }

  public JsonNode deleteModelDefault(String model) {
    return transport.delete("/api/user/model-defaults/" + enc(model), "session");
  }

  public JsonNode getSmartRouting() {
    return transport.get("/api/user/smart-routing", "api_key", null);
  }

  public JsonNode setSmartRouting(Map<String, Object> groups) {
    return transport.method("PUT", "/api/user/smart-routing", "api_key",
        Collections.singletonMap("groups", groups));
  }

  public JsonNode testSmartRouting(String model) {
    return transport.get("/api/user/smart-routing/test", "api_key", Collections.singletonMap("model", model));
  }

  public JsonNode getChannelPrefs() {
    return transport.get("/api/user/channel-prefs", "api_key", null);
  }

  public JsonNode setChannelPins(Map<String, Object> pins) {
    return transport.method("PUT", "/api/user/channel-prefs", "api_key", pins);
  }

  public JsonNode sessions() {
    return transport.get("/api/me/sessions", "session", null);
  }

  public JsonNode revokeSession(String jti) {
    return transport.delete("/api/me/sessions/" + enc(jti), "session");
  }

  public JsonNode revokeOtherSessions() {
    return transport.delete("/api/me/sessions", "session");
  }

  public JsonNode loginHistory(Integer limit) {
    Map<String, String> query = limit != null ? Collections.singletonMap("limit", String.valueOf(limit)) : null;
    return transport.get("/api/me/login-history", "session", query);
  }

  public JsonNode resetApiKey() {
    return transport.post("/api/user/reset-api-key", "session", null);
  }

  public JsonNode setPrimaryAllowedIps(List<String> ips) {
    return transport.method("PUT", "/api/user/primary-allowed-ips", "session",
        Collections.singletonMap("allowed_ips", ips));
  }

  public JsonNode setBackupPoolEnabled(boolean enabled) {
    return transport.method("PUT", "/api/user/backup-pool-enabled", "api_key",
        Collections.singletonMap("enabled", enabled));
  }

  public JsonNode togglePayAsYouGo() {
    return transport.post("/api/pay-as-you-go/toggle", "session", null);
  }
}
