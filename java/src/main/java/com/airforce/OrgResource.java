package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Organization self-service — {@code /api/org/*}. All endpoints use the session token; the
 * org context is implicit via the caller's membership (one org per user). Roles: owner
 * &gt; admin &gt; member. Callers without an org get a 404 ({@code no_org}); suspended
 * members get 403 ({@code membership_inactive}).
 */
public final class OrgResource extends Resource {

  OrgResource(Transport transport) {
    super(transport);
  }

  /** The caller's org and own role — {@code {org, role}}. */
  public JsonNode get() {
    return transport.get("/api/org", "session", null);
  }

  /** Rename the org (owner only; name 1–100 chars). */
  public JsonNode update(Map<String, Object> params) {
    return transport.method("PATCH", "/api/org", "session", params);
  }

  /**
   * Owner-only SSO config ({@code tenant_id}, {@code verified_domain}, {@code enforced});
   * an empty string clears a field, omitted fields stay unchanged. 409 when the tenant or
   * domain is already claimed.
   */
  public JsonNode updateSso(Map<String, Object> params) {
    return transport.method("PATCH", "/api/org/sso", "session", params);
  }

  /** List members (owner/admin only; returns the {@code members} array). */
  public JsonNode members() {
    JsonNode res = transport.get("/api/org/members", "session", null);
    return res != null && res.has("members") ? res.get("members") : res;
  }

  /**
   * Change a member's {@code role} (owner only) and/or {@code status}; suspending disables
   * the member's org keys. The owner row is immutable; admins may only manage plain members.
   */
  public JsonNode updateMember(String userId, Map<String, Object> params) {
    return transport.method("PATCH", "/api/org/members/" + enc(userId), "session", params);
  }

  /** Remove a member (owner/admin) or leave the org (self); the owner cannot be removed. */
  public JsonNode removeMember(String userId) {
    return transport.delete("/api/org/members/" + enc(userId), "session");
  }

  /** List pending invites (owner/admin; returns the {@code invites} array). */
  public JsonNode invites() {
    JsonNode res = transport.get("/api/org/invites", "session", null);
    return res != null && res.has("invites") ? res.get("invites") : res;
  }

  /**
   * Invite by email (7-day expiry). {@code role} is 'member' (default) or 'admin' (owner
   * only); pass null for the default. The response's {@code invite_url} is the reliable
   * delivery path — the invite mail is best-effort. 429 on cooldown/cap.
   */
  public JsonNode createInvite(String email, String role) {
    Map<String, Object> body = new HashMap<>();
    body.put("email", email);
    if (role != null) {
      body.put("role", role);
    }
    return transport.post("/api/org/invites", "session", body);
  }

  /**
   * Accept an invite token (any logged-in user without an org). The account email must
   * match the invite and be verified. 409 {@code already_in_org}, 410 when expired.
   */
  public JsonNode acceptInvite(String token) {
    return transport.post("/api/org/invites/accept", "session", Collections.singletonMap("token", token));
  }

  /** Revoke a pending invite (owner/admin). */
  public JsonNode revokeInvite(String id) {
    return transport.delete("/api/org/invites/" + enc(id), "session");
  }

  /** List org keys — owner/admin: all; member: own only (returns the {@code keys} array). */
  public JsonNode keys() {
    JsonNode res = transport.get("/api/org/keys", "session", null);
    return res != null && res.has("keys") ? res.get("keys") : res;
  }

  /**
   * Create a key for a member (owner/admin). Requires {@code member_user_id}; optional
   * keys mirror personal keys (label, credit_allowance, limit_reset, rpm_limit, model /
   * maker / class / channel / method allow- and block-lists, allowed_ips). Bills the org
   * owner's wallet; the full key is returned only here.
   */
  public JsonNode createKey(Map<String, Object> params) {
    return transport.post("/api/org/keys", "session", params);
  }

  /**
   * Update an org key (owner/admin) — same fields as create plus {@code disabled};
   * {@code member_user_id} is not changeable.
   */
  public JsonNode updateKey(String id, Map<String, Object> params) {
    return transport.method("PATCH", "/api/org/keys/" + enc(id), "session", params);
  }

  /** Delete an org key (owner/admin). */
  public JsonNode deleteKey(String id) {
    return transport.delete("/api/org/keys/" + enc(id), "session");
  }

  /**
   * Aggregate, per-member, per-key and daily-timeseries usage. Query keys: {@code from} /
   * {@code to} (unix seconds; default last 30 days), {@code member_user_id}, {@code key_id};
   * pass null for no filters. Cost values are cents. Members see only their own usage.
   */
  public JsonNode usage(Map<String, String> query) {
    return transport.get("/api/org/usage", "session", query);
  }
}
