/**
 * API key provisioning — `/v1/keys` (primary-key authenticated).
 */

import { APIResource, type RequestConfig } from "./resource";

export type KeyTier = "default" | "premium" | "paygo";
export type LimitReset = "daily" | "weekly" | "monthly" | "none";

export interface ApiKey {
  /** Full key on create; masked (`sk-air-…last4`) afterwards. */
  key: string;
  label?: string;
  created_at?: string;
  disabled?: boolean;
  tier: string;
  rpm_limit?: number;
  credit_allowance?: number;
  credits_used?: number;
  limit_reset?: string;
  allowed_models: string[];
  allowed_ips: string[];
}

export interface CreateKeyParams {
  label?: string;
  rpm_limit?: number;
  credit_allowance?: number;
  tier?: KeyTier;
  allowed_models?: string[];
  allowed_ips?: string[];
  limit_reset?: LimitReset;
}

export interface UpdateKeyParams extends CreateKeyParams {
  disabled?: boolean;
}

export class Keys extends APIResource {
  /** Create a secondary key. The full key is returned only here. */
  create(
    params: CreateKeyParams = {},
    options: RequestConfig = {},
  ): Promise<ApiKey> {
    return this.transport.request({
      method: "POST",
      path: "/v1/keys",
      body: params,
      ...options,
    });
  }

  /** List secondary keys (masked). */
  async list(options: RequestConfig = {}): Promise<ApiKey[]> {
    const res = await this.transport.request<{ keys: ApiKey[]; total: number }>({
      method: "GET",
      path: "/v1/keys",
      ...options,
    });
    return res.keys;
  }

  /** Update a secondary key's settings. */
  update(
    key: string,
    params: UpdateKeyParams,
    options: RequestConfig = {},
  ): Promise<ApiKey> {
    return this.transport.request({
      method: "PATCH",
      path: `/v1/keys/${encodeURIComponent(key)}`,
      body: params,
      ...options,
    });
  }

  /** Delete a secondary key. */
  delete(
    key: string,
    options: RequestConfig = {},
  ): Promise<{ deleted: boolean }> {
    return this.transport.request({
      method: "DELETE",
      path: `/v1/keys/${encodeURIComponent(key)}`,
      ...options,
    });
  }
}
