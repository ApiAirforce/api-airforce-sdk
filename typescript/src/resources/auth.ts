/**
 * Authentication — `/auth/*`. On successful login the session token is parsed
 * from the `Set-Cookie` response and adopted by the client automatically, so
 * subsequent account/billing calls just work.
 */

import { APIResource, type RequestConfig } from "./resource";

/** Extract the `airforce_session` JWT from a `Set-Cookie` response. */
function extractSessionCookie(headers: Headers): string | undefined {
  const getSetCookie = (
    headers as unknown as { getSetCookie?: () => string[] }
  ).getSetCookie;
  const cookies =
    typeof getSetCookie === "function"
      ? getSetCookie.call(headers)
      : headers.get("set-cookie")
        ? [headers.get("set-cookie") as string]
        : [];
  for (const cookie of cookies) {
    const match = /(?:^|;\s*)airforce_session=([^;]+)/.exec(cookie);
    if (match?.[1]) return decodeURIComponent(match[1]);
  }
  return undefined;
}

export interface SignupParams {
  username: string;
  password: string;
  email: string;
  captcha_token: string;
  referral_code?: string;
  locale?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
}

export interface LoginParams {
  username: string;
  password: string;
  captcha_token: string;
}

export interface LoginResult {
  ok?: boolean;
  requires_2fa?: boolean;
  challenge_token?: string;
  must_enroll_2fa?: boolean;
  verification_sent?: boolean;
  email_masked?: string;
  /** Session JWT parsed from the cookie (Node). The client adopts it. */
  sessionToken?: string;
  [key: string]: unknown;
}

export class Auth extends APIResource {
  private async submitAndAdopt(
    path: string,
    body: unknown,
    headers?: Record<string, string>,
    options: RequestConfig = {},
  ): Promise<LoginResult> {
    const { data, headers: resHeaders } =
      await this.transport.requestDetailed<LoginResult>({
        method: "POST",
        path,
        auth: "none",
        body,
        ...(headers ? { headers } : {}),
        ...options,
      });
    const sessionToken = extractSessionCookie(resHeaders);
    if (sessionToken) this.transport.setSessionToken(sessionToken);
    return { ...(data ?? {}), sessionToken };
  }

  /** Register a new account. */
  signup(params: SignupParams, options?: RequestConfig): Promise<LoginResult> {
    return this.submitAndAdopt("/auth/signup", params, undefined, options);
  }

  /** Hint whether signup will require the strict CAPTCHA widget. */
  signupPrecheck(
    params: { username?: string; email?: string },
    options: RequestConfig = {},
  ): Promise<{ strict: boolean }> {
    return this.transport.request({
      method: "POST",
      path: "/auth/signup/precheck",
      auth: "none",
      body: params,
      ...options,
    });
  }

  /** Log in. Returns a 2FA challenge when TOTP is enrolled. */
  login(params: LoginParams, options?: RequestConfig): Promise<LoginResult> {
    return this.submitAndAdopt("/auth/login", params, undefined, options);
  }

  /** Complete a 2FA login with the challenge token from {@link login}. */
  verify2fa(
    challengeToken: string,
    body: { code: string; backup_code?: string },
    options?: RequestConfig,
  ): Promise<LoginResult> {
    return this.submitAndAdopt(
      "/auth/2fa/verify",
      body,
      { authorization: `Bearer ${challengeToken}` },
      options,
    );
  }

  /** Confirm an email-verification token. */
  verifyEmail(
    token: string,
    options: RequestConfig = {},
  ): Promise<{ verified: boolean; username: string }> {
    return this.transport.request({
      method: "POST",
      path: "/auth/verify",
      auth: "none",
      body: { token },
      ...options,
    });
  }

  /** Resend the verification email. */
  resendVerification(
    identifier: string,
    options: RequestConfig = {},
  ): Promise<{ ok: boolean }> {
    return this.transport.request({
      method: "POST",
      path: "/auth/resend-verification",
      auth: "none",
      body: { identifier },
      ...options,
    });
  }

  /** Invalidate the current session and clear the local session token. */
  async logout(options: RequestConfig = {}): Promise<{ ok: boolean }> {
    const result = await this.transport.request<{ ok: boolean }>({
      method: "POST",
      path: "/auth/logout",
      auth: "session",
      ...options,
    });
    this.transport.setSessionToken(undefined);
    return result;
  }
}
