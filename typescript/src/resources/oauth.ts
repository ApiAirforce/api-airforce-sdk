/**
 * OAuth 2.0 — api.airforce as a provider (for third-party integrators) plus
 * self-service app management (`/api/me/oauth-apps`, `/api/me/connected-apps`).
 */

import type { Transport } from "../core/transport";
import { APIResource, type RequestConfig } from "./resource";

export type OAuthScope =
  | "profile"
  | "chat"
  | "images"
  | "keys:read"
  | "keys:write";

export interface OAuthClient {
  client_id: string;
  name: string;
  description?: string;
  homepage_url?: string;
  logo_url?: string;
  redirect_uris: string[];
  allowed_scopes: string[];
  approval_status: "approved" | "pending" | "rejected";
  enabled: boolean;
  owner_user_id?: string;
  created_at: string;
  access_token_ttl_secs?: number;
}

export interface AuthorizeUrlParams {
  client_id: string;
  redirect_uri: string;
  scope?: string | OAuthScope[];
  state?: string;
  code_challenge?: string;
  code_challenge_method?: "S256";
}

export interface TokenResponse {
  access_token: string;
  token_type: "Bearer";
  expires_in: number;
  scope: string;
}

export interface CreateAppParams {
  name: string;
  redirect_uris: string[];
  allowed_scopes: OAuthScope[] | string[];
  description?: string;
  homepage_url?: string;
  logo_url?: string;
  contact_email?: string;
  access_token_ttl_secs?: number;
}

export interface PkcePair {
  verifier: string;
  challenge: string;
  method: "S256";
}

function base64UrlEncode(bytes: ArrayBuffer | Uint8Array): string {
  const arr = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let str = "";
  for (const b of arr) str += String.fromCharCode(b);
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export class OAuth extends APIResource {
  constructor(
    transport: Transport,
    private readonly baseURL: string,
  ) {
    super(transport);
  }

  /** Generate a PKCE verifier/challenge pair (S256). */
  static async createPkcePair(): Promise<PkcePair> {
    const random = new Uint8Array(32);
    globalThis.crypto.getRandomValues(random);
    const verifier = base64UrlEncode(random);
    const digest = await globalThis.crypto.subtle.digest(
      "SHA-256",
      new TextEncoder().encode(verifier),
    );
    return { verifier, challenge: base64UrlEncode(digest), method: "S256" };
  }

  /** Build the `/oauth/authorize` URL to redirect a user to. */
  authorizeUrl(params: AuthorizeUrlParams): string {
    const url = new URL("/oauth/authorize", this.baseURL);
    const scope = Array.isArray(params.scope)
      ? params.scope.join(" ")
      : params.scope;
    url.searchParams.set("response_type", "code");
    url.searchParams.set("client_id", params.client_id);
    url.searchParams.set("redirect_uri", params.redirect_uri);
    if (scope) url.searchParams.set("scope", scope);
    if (params.state) url.searchParams.set("state", params.state);
    if (params.code_challenge) {
      url.searchParams.set("code_challenge", params.code_challenge);
      url.searchParams.set(
        "code_challenge_method",
        params.code_challenge_method ?? "S256",
      );
    }
    return url.toString();
  }

  /** Exchange an authorization code for an access token. */
  exchangeToken(
    params: {
      code: string;
      redirect_uri: string;
      client_id?: string;
      client_secret?: string;
      code_verifier?: string;
    },
    options: RequestConfig = {},
  ): Promise<TokenResponse> {
    return this.transport.request({
      method: "POST",
      path: "/oauth/token",
      auth: "none",
      urlencoded: { grant_type: "authorization_code", ...params },
      ...options,
    });
  }

  /** Fetch the profile for an `airf_oat_` access token. */
  userInfo(
    accessToken: string,
    options: RequestConfig = {},
  ): Promise<Record<string, unknown>> {
    return this.transport.request({
      method: "GET",
      path: "/oauth/userinfo",
      auth: "none",
      headers: { authorization: `Bearer ${accessToken}` },
      ...options,
    });
  }

  /** Revoke an access token (always succeeds, per RFC 7009). */
  async revokeToken(token: string, options: RequestConfig = {}): Promise<void> {
    await this.transport.request({
      method: "POST",
      path: "/oauth/revoke",
      auth: "none",
      urlencoded: { token },
      ...options,
    });
  }

  // --- self-service app management (session) --------------------------------

  /** List OAuth apps the caller owns. */
  listApps(
    options: RequestConfig = {},
  ): Promise<{ apps: OAuthClient[]; limit: number; count: number }> {
    return this.transport.request({
      method: "GET",
      path: "/api/me/oauth-apps",
      auth: "session",
      ...options,
    });
  }

  /** Create a new OAuth app (lands Pending unless auto-approved). */
  createApp(
    params: CreateAppParams,
    options: RequestConfig = {},
  ): Promise<{ app: OAuthClient; client_secret: string }> {
    return this.transport.request({
      method: "POST",
      path: "/api/me/oauth-apps",
      auth: "session",
      body: params,
      ...options,
    });
  }

  getApp(clientId: string, options: RequestConfig = {}): Promise<OAuthClient> {
    return this.transport.request({
      method: "GET",
      path: `/api/me/oauth-apps/${encodeURIComponent(clientId)}`,
      auth: "session",
      ...options,
    });
  }

  updateApp(
    clientId: string,
    patch: Partial<CreateAppParams>,
    options: RequestConfig = {},
  ): Promise<OAuthClient> {
    return this.transport.request({
      method: "PATCH",
      path: `/api/me/oauth-apps/${encodeURIComponent(clientId)}`,
      auth: "session",
      body: patch,
      ...options,
    });
  }

  deleteApp(
    clientId: string,
    options: RequestConfig = {},
  ): Promise<{ success: boolean }> {
    return this.transport.request({
      method: "DELETE",
      path: `/api/me/oauth-apps/${encodeURIComponent(clientId)}`,
      auth: "session",
      ...options,
    });
  }

  rotateSecret(
    clientId: string,
    options: RequestConfig = {},
  ): Promise<{ ok: boolean; client_secret: string }> {
    return this.transport.request({
      method: "POST",
      path: `/api/me/oauth-apps/${encodeURIComponent(clientId)}/rotate-secret`,
      auth: "session",
      ...options,
    });
  }

  /** List apps the caller has authorized (granted consent to). */
  connectedApps(
    options: RequestConfig = {},
  ): Promise<{ connected_apps: Array<Record<string, unknown>> }> {
    return this.transport.request({
      method: "GET",
      path: "/api/me/connected-apps",
      auth: "session",
      ...options,
    });
  }

  /** Revoke all tokens granted to a connected app. */
  revokeConnectedApp(
    clientId: string,
    options: RequestConfig = {},
  ): Promise<{ ok: boolean; tokens_revoked: number }> {
    return this.transport.request({
      method: "DELETE",
      path: `/api/me/connected-apps/${encodeURIComponent(clientId)}`,
      auth: "session",
      ...options,
    });
  }
}
