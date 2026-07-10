package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Account self-service — {@code /api/me}, {@code /api/user/*}, custom provider models, closure. */
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

  /** Pin models to a routing category — {@code {model: category_id}}. */
  public JsonNode setRoutingCategoryPrefs(Map<String, Object> prefs) {
    return transport.method("PUT", "/api/user/routing-category-prefs", "api_key", prefs);
  }

  /** Per-model channel order — {@code {model: {order: [...], auto_fallback?}}}. */
  public JsonNode setChannelOrderPrefs(Map<String, Object> prefs) {
    return transport.method("PUT", "/api/user/channel-order-prefs", "api_key", prefs);
  }

  /** List the caller's custom routing categories. */
  public JsonNode getCustomCategories() {
    return transport.get("/api/user/custom-categories", "api_key", null);
  }

  /** Replace the caller's custom routing categories (max 20). */
  public JsonNode setCustomCategories(List<Map<String, Object>> categories) {
    return transport.method("PUT", "/api/user/custom-categories", "api_key", categories);
  }

  /** Routing categories applicable to a model — {@code {categories: [...]}}. */
  public JsonNode routingCategories(String model) {
    return transport.get("/api/user/routing-categories", "api_key",
        Collections.singletonMap("model", model));
  }

  /** Register a custom provider model ({@code fake_name}, {@code endpoint}, ...). */
  public JsonNode createCustomModel(Map<String, Object> params) {
    return transport.post("/api/models", "session", params);
  }

  /** Update a custom provider model. */
  public JsonNode updateCustomModel(String fakeName, Map<String, Object> params) {
    return transport.method("PUT", "/api/models/" + enc(fakeName), "session", params);
  }

  /** Delete a custom provider model. */
  public JsonNode deleteCustomModel(String fakeName) {
    return transport.delete("/api/models/" + enc(fakeName), "session");
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

  /**
   * Soft-close the account — {@code DELETE /api/me/account}. Re-authenticates in the body:
   * {@code password} (required), {@code totp_code} (required when 2FA is enrolled, else 400
   * {@code totp_required}), {@code forfeit_balance_ack} (the remaining balance is zeroed
   * only when true). Revokes every session and OAuth token, rotates the primary API key,
   * disables secondary keys, and cancels subscriptions. Idempotent.
   */
  public JsonNode closeAccount(Map<String, Object> params) {
    return transport.method("DELETE", "/api/me/account", "session", params);
  }

  /**
   * Reactivate a soft-closed account within the 14-day grace window, identified by its
   * former email + password. Public (a closed account has no session) and rate-limited like
   * login. No session is minted — log in normally afterwards.
   */
  public JsonNode reactivate(String email, String password) {
    Map<String, Object> body = new HashMap<>();
    body.put("email", email);
    body.put("password", password);
    return transport.post("/auth/reactivate", "none", body);
  }
}
