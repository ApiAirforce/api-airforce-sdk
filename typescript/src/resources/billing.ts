/**
 * Billing & plans — checkout, crypto invoices, customer portal, public analytics.
 */

import { APIResource, type RequestConfig } from "./resource";

export type PlanId =
  | "starter"
  | "premium"
  | "plus"
  | "pro"
  | "master"
  | "elite"
  | "ultra"
  | "credits";

export interface CheckoutParams {
  plan: PlanId;
  is_onetime?: boolean;
  quantity?: number;
  /** USD amount for the `credits` top-up plan. */
  price_amount?: number;
}

export interface PublicAnalytics {
  total_requests: number;
  total_tokens: number;
  total_images: number;
  uptime_percent: number;
  total_users: number;
  active_today: number;
}

export class Billing extends APIResource {
  /** Create a Creem checkout session. Returns a `checkout_url`. */
  createCheckout(
    params: CheckoutParams,
    options: RequestConfig = {},
  ): Promise<{ id: string; checkout_url: string; [key: string]: unknown }> {
    return this.transport.request({
      method: "POST",
      path: "/api/creem/create-checkout",
      auth: "session",
      body: params,
      ...options,
    });
  }

  /** Create a NowPayments crypto invoice. */
  createCryptoInvoice(
    params: { plan: PlanId; price_amount?: number },
    options: RequestConfig = {},
  ): Promise<{ id: string; status: string; price_amount: number; [key: string]: unknown }> {
    return this.transport.request({
      method: "POST",
      path: "/api/create-nowpayments-invoice",
      auth: "session",
      body: params,
      ...options,
    });
  }

  /** Create a Creem customer-portal session for managing the subscription. */
  createPortalSession(
    options: RequestConfig = {},
  ): Promise<{ url: string }> {
    return this.transport.request({
      method: "POST",
      path: "/api/create-portal-session",
      auth: "session",
      body: {},
      ...options,
    });
  }

  /** Public, unauthenticated global analytics snapshot. */
  analytics(options: RequestConfig = {}): Promise<PublicAnalytics> {
    return this.transport.request({
      method: "GET",
      path: "/v1/analytics",
      auth: "none",
      ...options,
    });
  }
}
