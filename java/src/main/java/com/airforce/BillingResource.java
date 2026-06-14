package com.airforce;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Collections;
import java.util.Map;

/** Billing, plans, and public analytics. */
public final class BillingResource extends Resource {

  BillingResource(Transport transport) {
    super(transport);
  }

  /** Create a Creem checkout session. Requires {@code plan}. */
  public JsonNode createCheckout(Map<String, Object> params) {
    return transport.post("/api/creem/create-checkout", "session", params);
  }

  /** Create a NowPayments crypto invoice. Requires {@code plan}. */
  public JsonNode createCryptoInvoice(Map<String, Object> params) {
    return transport.post("/api/create-nowpayments-invoice", "session", params);
  }

  /** Create a Creem customer-portal session. */
  public JsonNode createPortalSession() {
    return transport.post("/api/create-portal-session", "session", Collections.emptyMap());
  }

  /** Public, unauthenticated global analytics snapshot. */
  public JsonNode analytics() {
    return transport.get("/v1/analytics", "none", null);
  }
}
