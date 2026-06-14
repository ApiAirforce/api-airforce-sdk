/**
 * Two-factor authentication (TOTP) — `/api/2fa/*`. Session-authenticated.
 */

import { APIResource, type RequestConfig } from "./resource";

export class TwoFactor extends APIResource {
  /** Begin enrollment; returns the TOTP secret + otpauth URL for a QR code. */
  setupInit(
    options: RequestConfig = {},
  ): Promise<{ secret: string; otpauth_url: string }> {
    return this.transport.request({
      method: "POST",
      path: "/api/2fa/setup-init",
      auth: "session",
      ...options,
    });
  }

  /** Verify the first TOTP code; returns one-time backup codes. */
  setupVerify(
    code: string,
    options: RequestConfig = {},
  ): Promise<{ backup_codes: string[] }> {
    return this.transport.request({
      method: "POST",
      path: "/api/2fa/setup-verify",
      auth: "session",
      body: { code },
      ...options,
    });
  }

  /** Disable 2FA (requires password + a current code). */
  disable(
    password: string,
    code: string,
    options: RequestConfig = {},
  ): Promise<{ success: boolean }> {
    return this.transport.request({
      method: "POST",
      path: "/api/2fa/disable",
      auth: "session",
      body: { password, code },
      ...options,
    });
  }

  /** Regenerate backup codes (requires a current code). */
  regenerateBackupCodes(
    code: string,
    options: RequestConfig = {},
  ): Promise<{ backup_codes: string[] }> {
    return this.transport.request({
      method: "POST",
      path: "/api/2fa/regenerate-backup-codes",
      auth: "session",
      body: { code },
      ...options,
    });
  }

  /** Step-up verification; returns a short-lived step-up token. */
  verifyStepUp(
    code: string,
    options: RequestConfig = {},
  ): Promise<{ ok: boolean; step_up_token: string }> {
    return this.transport.request({
      method: "POST",
      path: "/api/2fa/verify-step-up",
      auth: "session",
      body: { code },
      ...options,
    });
  }

  /** Check current step-up status. */
  stepUpStatus(
    options: RequestConfig = {},
  ): Promise<{ verified: boolean; expires_at?: string }> {
    return this.transport.request({
      method: "GET",
      path: "/api/2fa/step-up-status",
      auth: "session",
      ...options,
    });
  }
}
