/**
 * Notifications — `/api/me/notification-prefs`, `/api/me/notifications`,
 * `/api/me/channels` (all session token).
 *
 * Covers per-user notification preferences, the in-app feed, and linking the
 * delivery channels notifications are routed through.
 */

import { APIResource, type RequestConfig } from "./resource";

export type DigestFrequency = "off" | "instant" | "daily" | "weekly";

export interface QuietHours {
  /** `HH:MM` (24h). */
  start: string;
  /** `HH:MM` (24h). */
  end: string;
  /** IANA timezone, e.g. `Europe/Berlin`. */
  tz: string;
}

export interface PriceDropPrefs {
  enabled: boolean;
  scope: "global" | "watchlist_only";
  threshold_pct: number;
  min_absolute_drop_cents_per_1m: number;
}

export interface NewModelPrefs {
  enabled: boolean;
  providers: string[];
  modalities: string[];
}

export interface WatchlistEntry {
  added_at?: string;
  threshold_pct?: number;
  min_absolute_drop_cents_per_1m?: number;
}

export interface NotificationPrefs {
  /** Per-category delivery routing: category → linked channel ids. */
  routing: Record<string, string[]>;
  price_drop: PriceDropPrefs;
  new_model: NewModelPrefs;
  /** Watched models (≤200 entries), keyed by public model name. */
  watchlist: Record<string, WatchlistEntry>;
  digest_frequency: DigestFrequency;
  quiet_hours?: QuietHours | null;
  unsubscribed_all: boolean;
  strong_model_categories: string[];
}

/**
 * Partial update payload: absent fields are unchanged; `quiet_hours: null`
 * clears the quiet-hours window. Unknown channel ids in `routing` are dropped
 * server-side.
 */
export interface NotificationPrefsUpdate {
  routing?: Record<string, string[]>;
  price_drop?: Partial<PriceDropPrefs>;
  new_model?: Partial<NewModelPrefs>;
  watchlist?: Record<string, WatchlistEntry>;
  digest_frequency?: DigestFrequency;
  quiet_hours?: QuietHours | null;
  unsubscribed_all?: boolean;
  strong_model_categories?: string[];
}

export interface FeedItem {
  id: string;
  event_id: string;
  kind: string;
  params_json: string;
  link_url?: string;
  read_at?: string;
  created_at: string;
}

export interface ChannelIdentity {
  channel: string;
  address: string;
  display?: string;
  status: string;
  verified_at?: string;
  created_at: string;
}

/**
 * Result of starting a channel link. Address-based channels get a
 * verification code delivered through the channel itself (30-min expiry);
 * bot channels linked with an empty address get a one-time code / deep link
 * to complete the link from the bot side.
 */
export type LinkChannelResult =
  | { status: "verification_sent"; channel: string }
  | {
      status: "link_ready";
      channel: string;
      code: string;
      deep_link?: string;
      expires_minutes: number;
    };

export class Notifications extends APIResource {
  /** Read the caller's notification preferences. */
  getPrefs(options: RequestConfig = {}): Promise<NotificationPrefs> {
    return this.transport.request({
      method: "GET",
      path: "/api/me/notification-prefs",
      auth: "session",
      ...options,
    });
  }

  /** Partially update the preferences. Returns the updated document. */
  updatePrefs(
    body: NotificationPrefsUpdate,
    options: RequestConfig = {},
  ): Promise<NotificationPrefs> {
    return this.transport.request({
      method: "PATCH",
      path: "/api/me/notification-prefs",
      auth: "session",
      body,
      ...options,
    });
  }

  /**
   * The in-app notification feed, newest first, cursor-paged: pass the last
   * item's `created_at` as `before` to fetch the next page.
   */
  list(
    params: { limit?: number; before?: string } = {},
    options: RequestConfig = {},
  ): Promise<{ items: FeedItem[]; unread: number }> {
    return this.transport.request({
      method: "GET",
      path: "/api/me/notifications",
      auth: "session",
      query: { limit: params.limit, before: params.before },
      ...options,
    });
  }

  /** Mark feed items read — by ids, or everything with `{all: true}`. */
  markRead(
    body: { ids?: string[]; all?: boolean },
    options: RequestConfig = {},
  ): Promise<{ updated: number; unread: number }> {
    return this.transport.request({
      method: "POST",
      path: "/api/me/notifications/read",
      auth: "session",
      body,
      ...options,
    });
  }

  // --- delivery channels -------------------------------------------------------

  /** List linked delivery-channel identities + linkable channel ids. */
  listChannels(options: RequestConfig = {}): Promise<{
    identities: ChannelIdentity[];
    available_channels: string[];
  }> {
    return this.transport.request({
      method: "GET",
      path: "/api/me/channels",
      auth: "session",
      ...options,
    });
  }

  /**
   * Start linking a channel. The verification code is delivered through the
   * channel itself (proves control) and expires after 30 minutes. Bot
   * channels accept an empty `address` and return a one-time link code /
   * deep link instead.
   */
  linkChannel(
    body: { channel: string; address: string; display?: string },
    options: RequestConfig = {},
  ): Promise<LinkChannelResult> {
    return this.transport.request({
      method: "POST",
      path: "/api/me/channels",
      auth: "session",
      body,
      ...options,
    });
  }

  /** Complete channel verification with the delivered code (400 on invalid/expired). */
  verifyChannel(
    body: { channel: string; code: string },
    options: RequestConfig = {},
  ): Promise<{ status: "verified"; channel: string }> {
    return this.transport.request({
      method: "POST",
      path: "/api/me/channels/verify",
      auth: "session",
      body,
      ...options,
    });
  }

  /** Unlink/revoke a channel identity. */
  unlinkChannel(
    channel: string,
    options: RequestConfig = {},
  ): Promise<{ status: "revoked"; channel: string }> {
    return this.transport.request({
      method: "DELETE",
      path: `/api/me/channels/${encodeURIComponent(channel)}`,
      auth: "session",
      ...options,
    });
  }
}
