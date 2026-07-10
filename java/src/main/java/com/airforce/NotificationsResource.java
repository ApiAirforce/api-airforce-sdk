package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Notification preferences, the in-app feed, and delivery-channel linking —
 * {@code /api/me/notification-prefs}, {@code /api/me/notifications}, {@code /api/me/channels}.
 * All endpoints use the session token.
 */
public final class NotificationsResource extends Resource {

  NotificationsResource(Transport transport) {
    super(transport);
  }

  /** Read the caller's notification preferences. */
  public JsonNode getPrefs() {
    return transport.get("/api/me/notification-prefs", "session", null);
  }

  /**
   * Partially update preferences: absent fields stay unchanged, {@code quiet_hours: null}
   * clears quiet hours, unknown channel ids in {@code routing} are dropped server-side.
   */
  public JsonNode updatePrefs(Map<String, Object> params) {
    return transport.method("PATCH", "/api/me/notification-prefs", "session", params);
  }

  /**
   * The in-app feed, newest first — {@code {items, unread}}. {@code limit} 1–100 (default
   * 30); {@code before} is a {@code created_at} cursor for paging. Pass null to omit either.
   */
  public JsonNode list(Integer limit, String before) {
    Map<String, String> query = new HashMap<>();
    if (limit != null) {
      query.put("limit", String.valueOf(limit));
    }
    if (before != null) {
      query.put("before", before);
    }
    return transport.get("/api/me/notifications", "session", query.isEmpty() ? null : query);
  }

  /** Mark specific feed items read. */
  public JsonNode markRead(List<String> ids) {
    return transport.post("/api/me/notifications/read", "session", Collections.singletonMap("ids", ids));
  }

  /** Mark the whole feed read. */
  public JsonNode markAllRead() {
    return transport.post("/api/me/notifications/read", "session", Collections.singletonMap("all", true));
  }

  /** Linked delivery-channel identities plus linkable channel ids. */
  public JsonNode channels() {
    return transport.get("/api/me/channels", "session", null);
  }

  /**
   * Start linking a delivery channel; the verification code is delivered through the
   * channel itself and expires after 30 minutes. Bot channels accept an empty
   * {@code address} and answer with a one-time link code / deep link instead
   * ({@code status:'link_ready'}).
   */
  public JsonNode linkChannel(String channel, String address, String display) {
    Map<String, Object> body = new HashMap<>();
    body.put("channel", channel);
    body.put("address", address);
    if (display != null) {
      body.put("display", display);
    }
    return transport.post("/api/me/channels", "session", body);
  }

  /** Complete channel verification with the delivered code. */
  public JsonNode verifyChannel(String channel, String code) {
    Map<String, Object> body = new HashMap<>();
    body.put("channel", channel);
    body.put("code", code);
    return transport.post("/api/me/channels/verify", "session", body);
  }

  /** Unlink/revoke a channel identity. */
  public JsonNode unlinkChannel(String channel) {
    return transport.delete("/api/me/channels/" + enc(channel), "session");
  }
}
