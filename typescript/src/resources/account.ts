/**
 * Account self-service — `/api/me`, `/api/user/*`. Most endpoints require a
 * session token; smart-routing / channel-prefs accept an API key.
 */

import { APIResource, type RequestConfig } from "./resource";

export interface UserResponse {
  id: string;
  username: string;
  is_admin: boolean;
  api_key: string;
  plan: string;
  subscription_id?: string;
  subscription_source?: string;
  requests_today: number;
  tokens_today: number;
  total_tokens: number;
  images_generated_today: number;
  total_images_generated: number;
  /** Wallet balance in cents. */
  balance: number;
  pay_as_you_go: boolean;
  email?: string;
  has_password: boolean;
  main_quota_remaining_cents?: number;
  main_quota_daily_used_cents?: number;
  main_quota_weekly_used_cents?: number;
  backup_quota_remaining_cents?: number;
  backup_pool_enabled?: boolean;
  current_plan_caps?: { daily_cap_cents?: number; weekly_cap_cents?: number };
  plan_expiry?: string;
  created_at: string;
  last_login?: string;
  totp_enabled: boolean;
  must_enroll_2fa: boolean;
  is_warm?: boolean;
  has_ever_paid?: boolean;
  models?: unknown[];
  model_aliases?: Record<string, string>;
  model_defaults?: Record<string, UserModelDefault>;
  [key: string]: unknown;
}

export interface UsageSummary {
  total_usage: { tokens: number; cost_cents: number; requests: number };
  by_model: Array<{
    model: string;
    tokens: number;
    cost_cents: number;
    requests: number;
    providers: string[];
  }>;
  by_provider: Array<{
    provider: string;
    tokens: number;
    cost_cents: number;
    requests: number;
  }>;
  usage_log: Array<Record<string, unknown>>;
}

export interface ModelPriceCap {
  max_input_cents_per_m?: number;
  max_output_cents_per_m?: number;
  max_cache_write_5m_cents_per_m?: number;
  max_cache_write_1h_cents_per_m?: number;
  max_cache_read_cents_per_m?: number;
}

export interface UserModelDefault {
  temperature?: number;
  top_p?: number;
  max_tokens?: number;
  thinking?: "on" | "off" | "auto";
  thinking_budget?: number;
  reasoning_effort?: "low" | "medium" | "high";
  stop?: string[];
}

export interface SmartRoutingConfig {
  groups: Record<string, { priority_order: string[] }>;
}

export interface SessionEntry {
  jti: string;
  created_at: string;
  ip: string;
  user_agent: string;
  last_seen?: string;
}

export class Account extends APIResource {
  /** Current user profile + quotas. */
  me(options: RequestConfig = {}): Promise<UserResponse> {
    return this.transport.request({
      method: "GET",
      path: "/api/me",
      auth: "session",
      ...options,
    });
  }

  /** Account + billing summary (alias of `/api/me`). */
  usage(options: RequestConfig = {}): Promise<UserResponse> {
    return this.transport.request({
      method: "GET",
      path: "/api/usage",
      auth: "session",
      ...options,
    });
  }

  /** Detailed usage log + aggregates. */
  myUsage(options: RequestConfig = {}): Promise<UsageSummary> {
    return this.transport.request({
      method: "GET",
      path: "/api/my-usage",
      auth: "session",
      ...options,
    });
  }

  /** Update username / email / password. */
  update(
    body: { username?: string; email?: string; password?: string },
    options: RequestConfig = {},
  ): Promise<{ success: boolean; message: string }> {
    return this.transport.request({
      method: "PUT",
      path: "/api/user/update",
      auth: "session",
      body,
      ...options,
    });
  }

  /** Request a password-reset email (no auth). */
  requestPasswordReset(
    body: { email: string; locale?: string },
    options: RequestConfig = {},
  ): Promise<{ success: boolean; message: string }> {
    return this.transport.request({
      method: "POST",
      path: "/api/auth/request-password-reset",
      auth: "none",
      body,
      ...options,
    });
  }

  /** Complete a password reset with a token (no auth). */
  resetPassword(
    body: { token: string; new_password: string },
    options: RequestConfig = {},
  ): Promise<{ success: boolean; message: string }> {
    return this.transport.request({
      method: "POST",
      path: "/api/auth/reset-password",
      auth: "none",
      body,
      ...options,
    });
  }

  /** Get (or lazily create) the caller's referral code. */
  referralCode(options: RequestConfig = {}): Promise<{ referral_code: string }> {
    return this.transport.request({
      method: "GET",
      path: "/api/referral/code",
      auth: "session",
      ...options,
    });
  }

  /** List users referred by the caller. */
  referredUsers(
    options: RequestConfig = {},
  ): Promise<{ referred_users: string[]; referral_count: number }> {
    return this.transport.request({
      method: "GET",
      path: "/api/referral/referred-users",
      auth: "session",
      ...options,
    });
  }

  // --- price caps ----------------------------------------------------------

  getPriceCaps(
    options: RequestConfig = {},
  ): Promise<{ caps: Record<string, ModelPriceCap> }> {
    return this.transport.request({
      method: "GET",
      path: "/api/user/price-caps",
      auth: "session",
      ...options,
    });
  }

  setPriceCaps(
    caps: Record<string, ModelPriceCap>,
    options: RequestConfig = {},
  ): Promise<{ caps: Record<string, ModelPriceCap> }> {
    return this.transport.request({
      method: "PUT",
      path: "/api/user/price-caps",
      auth: "session",
      body: { caps },
      ...options,
    });
  }

  deletePriceCap(
    model: string,
    options: RequestConfig = {},
  ): Promise<{ success: boolean }> {
    return this.transport.request({
      method: "DELETE",
      path: `/api/user/price-caps/${encodeURIComponent(model)}`,
      auth: "session",
      ...options,
    });
  }

  // --- model aliases -------------------------------------------------------

  getModelAliases(options: RequestConfig = {}): Promise<Record<string, string>> {
    return this.transport.request({
      method: "GET",
      path: "/api/user/model-aliases",
      auth: "session",
      ...options,
    });
  }

  setModelAlias(
    alias: string,
    model: string,
    options: RequestConfig = {},
  ): Promise<{ success: boolean; alias: string; model: string }> {
    return this.transport.request({
      method: "PUT",
      path: "/api/user/model-aliases",
      auth: "session",
      body: { alias, model },
      ...options,
    });
  }

  setModelAliasesBatch(
    aliases: Array<{ alias: string; model: string }>,
    options: RequestConfig = {},
  ): Promise<{ success: boolean; count: number }> {
    return this.transport.request({
      method: "PUT",
      path: "/api/user/model-aliases/batch",
      auth: "session",
      body: aliases,
      ...options,
    });
  }

  deleteModelAlias(
    alias: string,
    options: RequestConfig = {},
  ): Promise<{ success: boolean; removed: boolean }> {
    return this.transport.request({
      method: "DELETE",
      path: `/api/user/model-aliases/${encodeURIComponent(alias)}`,
      auth: "session",
      ...options,
    });
  }

  // --- model defaults ------------------------------------------------------

  getModelDefaults(
    options: RequestConfig = {},
  ): Promise<{ defaults: Record<string, UserModelDefault> }> {
    return this.transport.request({
      method: "GET",
      path: "/api/user/model-defaults",
      auth: "session",
      ...options,
    });
  }

  setModelDefault(
    model: string,
    def: UserModelDefault,
    options: RequestConfig = {},
  ): Promise<{ success: boolean; model: string; cleared: boolean }> {
    return this.transport.request({
      method: "PUT",
      path: `/api/user/model-defaults/${encodeURIComponent(model)}`,
      auth: "session",
      body: def,
      ...options,
    });
  }

  deleteModelDefault(
    model: string,
    options: RequestConfig = {},
  ): Promise<{ success: boolean; removed: boolean }> {
    return this.transport.request({
      method: "DELETE",
      path: `/api/user/model-defaults/${encodeURIComponent(model)}`,
      auth: "session",
      ...options,
    });
  }

  // --- smart routing (api_key) ---------------------------------------------

  getSmartRouting(options: RequestConfig = {}): Promise<{
    user: SmartRoutingConfig;
    admin_groups: Array<{ key: string; display_name: string; variants: string[] }>;
  }> {
    return this.transport.request({
      method: "GET",
      path: "/api/user/smart-routing",
      auth: "api_key",
      ...options,
    });
  }

  setSmartRouting(
    config: SmartRoutingConfig,
    options: RequestConfig = {},
  ): Promise<{ ok: boolean }> {
    return this.transport.request({
      method: "PUT",
      path: "/api/user/smart-routing",
      auth: "api_key",
      body: config,
      ...options,
    });
  }

  testSmartRouting(
    model: string,
    options: RequestConfig = {},
  ): Promise<{ requested: string; resolved_to?: string }> {
    return this.transport.request({
      method: "GET",
      path: "/api/user/smart-routing/test",
      auth: "api_key",
      query: { model },
      ...options,
    });
  }

  // --- channel prefs (api_key) ---------------------------------------------

  getChannelPrefs(options: RequestConfig = {}): Promise<{
    channel_prefs: Record<string, string>;
    routing_category_prefs: Record<string, string>;
    channel_order_prefs: Record<string, { order: string[]; auto_fallback?: boolean }>;
  }> {
    return this.transport.request({
      method: "GET",
      path: "/api/user/channel-prefs",
      auth: "api_key",
      ...options,
    });
  }

  setChannelPins(
    pins: Record<string, string>,
    options: RequestConfig = {},
  ): Promise<{ ok: boolean }> {
    return this.transport.request({
      method: "PUT",
      path: "/api/user/channel-prefs",
      auth: "api_key",
      body: pins,
      ...options,
    });
  }

  // --- sessions ------------------------------------------------------------

  sessions(options: RequestConfig = {}): Promise<{
    count: number;
    current_jti: string;
    entries: SessionEntry[];
  }> {
    return this.transport.request({
      method: "GET",
      path: "/api/me/sessions",
      auth: "session",
      ...options,
    });
  }

  revokeSession(
    jti: string,
    options: RequestConfig = {},
  ): Promise<{ ok: boolean; revoked: boolean }> {
    return this.transport.request({
      method: "DELETE",
      path: `/api/me/sessions/${encodeURIComponent(jti)}`,
      auth: "session",
      ...options,
    });
  }

  revokeOtherSessions(
    options: RequestConfig = {},
  ): Promise<{ ok: boolean; revoked: number }> {
    return this.transport.request({
      method: "DELETE",
      path: "/api/me/sessions",
      auth: "session",
      ...options,
    });
  }

  loginHistory(
    limit?: number,
    options: RequestConfig = {},
  ): Promise<{
    count: number;
    entries: Array<{ timestamp: string; ip: string; user_agent: string; method: string }>;
  }> {
    return this.transport.request({
      method: "GET",
      path: "/api/me/login-history",
      auth: "session",
      query: limit !== undefined ? { limit } : undefined,
      ...options,
    });
  }

  // --- keys / wallet toggles -----------------------------------------------

  /** Rotate the primary API key. */
  resetApiKey(
    options: RequestConfig = {},
  ): Promise<{ success: boolean; api_key: string }> {
    return this.transport.request({
      method: "POST",
      path: "/api/user/reset-api-key",
      auth: "session",
      ...options,
    });
  }

  setPrimaryAllowedIps(
    allowed_ips: string[],
    options: RequestConfig = {},
  ): Promise<{ success: boolean; allowed_ips: string[] }> {
    return this.transport.request({
      method: "PUT",
      path: "/api/user/primary-allowed-ips",
      auth: "session",
      body: { allowed_ips },
      ...options,
    });
  }

  setBackupPoolEnabled(
    enabled: boolean,
    options: RequestConfig = {},
  ): Promise<{ backup_pool_enabled: boolean }> {
    return this.transport.request({
      method: "PUT",
      path: "/api/user/backup-pool-enabled",
      auth: "api_key",
      body: { enabled },
      ...options,
    });
  }

  /** Toggle pay-as-you-go (wallet) spending. */
  togglePayAsYouGo(
    options: RequestConfig = {},
  ): Promise<{ pay_as_you_go: boolean }> {
    return this.transport.request({
      method: "POST",
      path: "/api/pay-as-you-go/toggle",
      auth: "session",
      ...options,
    });
  }
}
