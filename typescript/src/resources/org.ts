/**
 * Organizations — `/api/org/*` (session token).
 *
 * The org context is implicit via the caller's membership (one org per user).
 * Roles: `owner` ⊃ `admin` ⊃ `member`. Callers without an org get a 404
 * (`no_org`); suspended members get 403 (`membership_inactive`) everywhere.
 * Creating an org itself is not self-service.
 */

import { APIResource, type RequestConfig } from "./resource";
import type { LimitReset } from "./keys";

export type OrgRole = "owner" | "admin" | "member";
export type OrgMemberStatus = "active" | "suspended";

export interface OrgSsoSettings {
  tenant_id?: string;
  verified_domain?: string;
  enforced?: boolean;
}

export interface Org {
  id: string;
  name: string;
  created_at: string;
  member_count: number;
  settings: { sso: OrgSsoSettings | null };
}

export interface OrgMember {
  user_id: string;
  email?: string;
  username?: string;
  role: OrgRole;
  status: OrgMemberStatus;
  joined_at: string;
}

export interface OrgInvite {
  id: string;
  org_id: string;
  email: string;
  role: OrgRole;
  invited_by: string;
  created_at: string;
  expires_at: string;
}

/**
 * An org-scoped API key. Same per-key semantics as personal secondary keys
 * (allowance, limit window, scoping); bills the org owner's wallet. The full
 * `key` is present only in the create response — list/update responses carry
 * `masked_key` / `key_prefix` / `key_last4` instead.
 */
export interface OrgKey {
  /** `okey_…` identifier (not the secret). */
  id: string;
  org_id: string;
  member_user_id: string;
  member_email?: string;
  member_username?: string;
  /** Full key material — create response only. */
  key?: string;
  masked_key?: string;
  key_prefix?: string;
  key_last4?: string;
  label?: string;
  created_at?: string;
  disabled?: boolean;
  tier?: string;
  rpm_limit?: number;
  credit_allowance?: number;
  credits_used?: number;
  limit_reset?: string;
  allowed_models?: string[];
  allowed_ips?: string[];
  [key: string]: unknown;
}

export interface CreateOrgKeyParams {
  /** The member the key is issued for. */
  member_user_id: string;
  label?: string;
  credit_allowance?: number;
  limit_reset?: LimitReset;
  rpm_limit?: number;
  allowed_models?: string[];
  blocked_models?: string[];
  allowed_makers?: string[];
  blocked_makers?: string[];
  allowed_classes?: string[];
  blocked_classes?: string[];
  allowed_channels?: string[];
  blocked_channels?: string[];
  allowed_methods?: string[];
  blocked_methods?: string[];
  allowed_ips?: string[];
}

export interface UpdateOrgKeyParams
  extends Omit<CreateOrgKeyParams, "member_user_id"> {
  disabled?: boolean;
}

export interface OrgUsageParams {
  /** Window start, unix seconds. Default: 30 days ago. */
  from?: number;
  /** Window end, unix seconds. Default: now. */
  to?: number;
  /** Filter to one member (owner/admin only). */
  member_user_id?: string;
  /** Filter to one key. */
  key_id?: string;
}

export interface OrgUsage {
  total: {
    requests: number;
    tokens_in: number;
    tokens_out: number;
    /** Cents. */
    cost_cents: number;
  };
  per_member: Array<{
    user_id: string;
    email?: string;
    username?: string;
    requests: number;
    tokens_in: number;
    tokens_out: number;
    cost_cents: number;
  }>;
  per_key: Array<{
    key_id: string;
    label?: string;
    member_user_id?: string;
    requests: number;
    cost_cents: number;
    credits_used: number;
    credit_allowance?: number;
  }>;
  timeseries: Array<{
    date: string;
    requests: number;
    [key: string]: unknown;
  }>;
  attribution_since: string;
}

export class Orgs extends APIResource {
  /** The caller's org and their own role in it. */
  get(options: RequestConfig = {}): Promise<{ org: Org; role: OrgRole }> {
    return this.transport.request({
      method: "GET",
      path: "/api/org",
      auth: "session",
      ...options,
    });
  }

  /** Rename the org (owner only; name 1–100 chars). */
  update(body: { name?: string }, options: RequestConfig = {}): Promise<Org> {
    return this.transport.request({
      method: "PATCH",
      path: "/api/org",
      auth: "session",
      body,
      ...options,
    });
  }

  /**
   * Configure org SSO (owner only). An empty string clears a field; omitted
   * fields are unchanged. 409 `tenant_already_claimed` /
   * `domain_already_claimed` on uniqueness conflicts.
   */
  updateSso(body: OrgSsoSettings, options: RequestConfig = {}): Promise<Org> {
    return this.transport.request({
      method: "PATCH",
      path: "/api/org/sso",
      auth: "session",
      body,
      ...options,
    });
  }

  // --- members ---------------------------------------------------------------

  /** List members (owner/admin only). */
  async listMembers(options: RequestConfig = {}): Promise<OrgMember[]> {
    const res = await this.transport.request<{ members: OrgMember[] }>({
      method: "GET",
      path: "/api/org/members",
      auth: "session",
      ...options,
    });
    return res.members;
  }

  /**
   * Change a member's role (owner only) and/or status. Suspending disables
   * the member's org keys; the owner row is immutable; admins may only manage
   * plain members.
   */
  updateMember(
    userId: string,
    body: { role?: "admin" | "member"; status?: OrgMemberStatus },
    options: RequestConfig = {},
  ): Promise<OrgMember> {
    return this.transport.request({
      method: "PATCH",
      path: `/api/org/members/${encodeURIComponent(userId)}`,
      auth: "session",
      body,
      ...options,
    });
  }

  /**
   * Remove a member (owner/admin) or leave the org (self). The owner cannot
   * be removed; the member's org keys are disabled.
   */
  removeMember(
    userId: string,
    options: RequestConfig = {},
  ): Promise<{ removed: boolean }> {
    return this.transport.request({
      method: "DELETE",
      path: `/api/org/members/${encodeURIComponent(userId)}`,
      auth: "session",
      ...options,
    });
  }

  // --- invites ---------------------------------------------------------------

  /** List pending invites (owner/admin only). */
  async listInvites(options: RequestConfig = {}): Promise<OrgInvite[]> {
    const res = await this.transport.request<{ invites: OrgInvite[] }>({
      method: "GET",
      path: "/api/org/invites",
      auth: "session",
      ...options,
    });
    return res.invites;
  }

  /**
   * Invite by email (7-day expiry). Admin invites are owner-only. The invite
   * mail is best-effort — `invite_url` is the reliable path. 429
   * `invite_cooldown` / `invite_cap_reached` on limits.
   */
  createInvite(
    body: { email: string; role?: "member" | "admin" },
    options: RequestConfig = {},
  ): Promise<{
    invite: { id: string; email: string; role: OrgRole; expires_at: string };
    invite_url: string;
  }> {
    return this.transport.request({
      method: "POST",
      path: "/api/org/invites",
      auth: "session",
      body,
      ...options,
    });
  }

  /**
   * Accept an invite (any logged-in user without an org). The caller's email
   * must match the invite and be verified. 409 `already_in_org`, 410 expired.
   */
  acceptInvite(
    token: string,
    options: RequestConfig = {},
  ): Promise<{ org: Org; role: OrgRole }> {
    return this.transport.request({
      method: "POST",
      path: "/api/org/invites/accept",
      auth: "session",
      body: { token },
      ...options,
    });
  }

  /** Revoke a pending invite (owner/admin only). */
  revokeInvite(
    id: string,
    options: RequestConfig = {},
  ): Promise<{ revoked: boolean }> {
    return this.transport.request({
      method: "DELETE",
      path: `/api/org/invites/${encodeURIComponent(id)}`,
      auth: "session",
      ...options,
    });
  }

  // --- org keys ----------------------------------------------------------------

  /** List org keys — owner/admin: all; member: own only. Keys are masked. */
  async listKeys(options: RequestConfig = {}): Promise<OrgKey[]> {
    const res = await this.transport.request<{ keys: OrgKey[] }>({
      method: "GET",
      path: "/api/org/keys",
      auth: "session",
      ...options,
    });
    return res.keys;
  }

  /**
   * Create a key for a member (owner/admin). Bills the org owner's wallet;
   * validation mirrors personal keys. The full key is returned only here.
   */
  async createKey(
    params: CreateOrgKeyParams,
    options: RequestConfig = {},
  ): Promise<OrgKey> {
    const res = await this.transport.request<{ item: OrgKey }>({
      method: "POST",
      path: "/api/org/keys",
      auth: "session",
      body: params,
      ...options,
    });
    return res.item;
  }

  /**
   * Update an org key (owner/admin). Org-marked keys only — the owner's
   * private keys are unreachable here; `member_user_id` is not changeable.
   */
  async updateKey(
    id: string,
    params: UpdateOrgKeyParams,
    options: RequestConfig = {},
  ): Promise<OrgKey> {
    const res = await this.transport.request<{ item: OrgKey }>({
      method: "PATCH",
      path: `/api/org/keys/${encodeURIComponent(id)}`,
      auth: "session",
      body: params,
      ...options,
    });
    return res.item;
  }

  /** Delete an org key (owner/admin). */
  deleteKey(
    id: string,
    options: RequestConfig = {},
  ): Promise<{ deleted: boolean }> {
    return this.transport.request({
      method: "DELETE",
      path: `/api/org/keys/${encodeURIComponent(id)}`,
      auth: "session",
      ...options,
    });
  }

  // --- usage -------------------------------------------------------------------

  /**
   * Aggregate + per-member + per-key + daily timeseries usage. Members are
   * scoped to themselves; `cost_cents` values are cents.
   */
  usage(
    params: OrgUsageParams = {},
    options: RequestConfig = {},
  ): Promise<OrgUsage> {
    return this.transport.request({
      method: "GET",
      path: "/api/org/usage",
      auth: "session",
      query: {
        from: params.from,
        to: params.to,
        member_user_id: params.member_user_id,
        key_id: params.key_id,
      },
      ...options,
    });
  }
}
