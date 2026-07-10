use super::enc;
use crate::client::Client;
use crate::error::Result;
use reqwest::Method;
use serde::Serialize;
use serde_json::{json, Value};

/// Account self-service — `/api/me`, `/api/user/*`.
pub struct Account<'a> {
    pub(crate) client: &'a Client,
}

impl Account<'_> {
    pub async fn me(&self) -> Result<Value> {
        self.client.get_json("/api/me", "session", None).await
    }
    pub async fn usage(&self) -> Result<Value> {
        self.client.get_json("/api/usage", "session", None).await
    }
    pub async fn my_usage(&self) -> Result<Value> {
        self.client.get_json("/api/my-usage", "session", None).await
    }
    pub async fn update(&self, body: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PUT,
                "/api/user/update",
                "session",
                Some(serde_json::to_value(body)?),
            )
            .await
    }
    pub async fn request_password_reset(&self, email: &str, locale: Option<&str>) -> Result<Value> {
        let body = match locale {
            Some(l) => json!({ "email": email, "locale": l }),
            None => json!({ "email": email }),
        };
        self.client
            .request_json(
                Method::POST,
                "/api/auth/request-password-reset",
                "none",
                Some(body),
            )
            .await
    }
    pub async fn reset_password(&self, token: &str, new_password: &str) -> Result<Value> {
        let body = json!({ "token": token, "new_password": new_password });
        self.client
            .request_json(Method::POST, "/api/auth/reset-password", "none", Some(body))
            .await
    }
    pub async fn referral_code(&self) -> Result<Value> {
        self.client
            .get_json("/api/referral/code", "session", None)
            .await
    }
    pub async fn referred_users(&self) -> Result<Value> {
        self.client
            .get_json("/api/referral/referred-users", "session", None)
            .await
    }
    pub async fn get_price_caps(&self) -> Result<Value> {
        self.client
            .get_json("/api/user/price-caps", "session", None)
            .await
    }
    pub async fn set_price_caps(&self, caps: impl Serialize) -> Result<Value> {
        let body = json!({ "caps": serde_json::to_value(caps)? });
        self.client
            .request_json(Method::PUT, "/api/user/price-caps", "session", Some(body))
            .await
    }
    pub async fn delete_price_cap(&self, model: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/api/user/price-caps/{}", enc(model)),
                "session",
                None,
            )
            .await
    }
    pub async fn get_model_aliases(&self) -> Result<Value> {
        self.client
            .get_json("/api/user/model-aliases", "session", None)
            .await
    }
    pub async fn set_model_alias(&self, alias: &str, model: &str) -> Result<Value> {
        let body = json!({ "alias": alias, "model": model });
        self.client
            .request_json(
                Method::PUT,
                "/api/user/model-aliases",
                "session",
                Some(body),
            )
            .await
    }
    pub async fn set_model_aliases_batch(&self, aliases: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PUT,
                "/api/user/model-aliases/batch",
                "session",
                Some(serde_json::to_value(aliases)?),
            )
            .await
    }
    pub async fn delete_model_alias(&self, alias: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/api/user/model-aliases/{}", enc(alias)),
                "session",
                None,
            )
            .await
    }
    pub async fn get_model_defaults(&self) -> Result<Value> {
        self.client
            .get_json("/api/user/model-defaults", "session", None)
            .await
    }
    pub async fn set_model_default(&self, model: &str, def: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PUT,
                &format!("/api/user/model-defaults/{}", enc(model)),
                "session",
                Some(serde_json::to_value(def)?),
            )
            .await
    }
    pub async fn delete_model_default(&self, model: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/api/user/model-defaults/{}", enc(model)),
                "session",
                None,
            )
            .await
    }
    pub async fn get_smart_routing(&self) -> Result<Value> {
        self.client
            .get_json("/api/user/smart-routing", "api_key", None)
            .await
    }
    pub async fn set_smart_routing(&self, groups: impl Serialize) -> Result<Value> {
        let body = json!({ "groups": serde_json::to_value(groups)? });
        self.client
            .request_json(
                Method::PUT,
                "/api/user/smart-routing",
                "api_key",
                Some(body),
            )
            .await
    }
    pub async fn test_smart_routing(&self, model: &str) -> Result<Value> {
        self.client
            .get_json(
                "/api/user/smart-routing/test",
                "api_key",
                Some(&[("model".to_string(), model.to_string())]),
            )
            .await
    }
    pub async fn get_channel_prefs(&self) -> Result<Value> {
        self.client
            .get_json("/api/user/channel-prefs", "api_key", None)
            .await
    }
    pub async fn set_channel_pins(&self, pins: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PUT,
                "/api/user/channel-prefs",
                "api_key",
                Some(serde_json::to_value(pins)?),
            )
            .await
    }
    /// Pin models to a routing category — `PUT /api/user/routing-category-prefs`
    /// with `{model: category_id}`.
    pub async fn set_routing_category_prefs(&self, prefs: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PUT,
                "/api/user/routing-category-prefs",
                "api_key",
                Some(serde_json::to_value(prefs)?),
            )
            .await
    }
    /// Per-model channel try-order — `PUT /api/user/channel-order-prefs` with
    /// `{model: {order: string[], auto_fallback?}}`.
    pub async fn set_channel_order_prefs(&self, prefs: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PUT,
                "/api/user/channel-order-prefs",
                "api_key",
                Some(serde_json::to_value(prefs)?),
            )
            .await
    }
    pub async fn get_custom_categories(&self) -> Result<Value> {
        self.client
            .get_json("/api/user/custom-categories", "api_key", None)
            .await
    }
    /// Replace the caller's custom routing categories (max 20) —
    /// `PUT /api/user/custom-categories` with a `RoutingCategory[]`.
    pub async fn set_custom_categories(&self, categories: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PUT,
                "/api/user/custom-categories",
                "api_key",
                Some(serde_json::to_value(categories)?),
            )
            .await
    }
    /// Routing categories selectable for a model —
    /// `GET /api/user/routing-categories?model=` → `{categories}`.
    pub async fn routing_categories(&self, model: &str) -> Result<Value> {
        self.client
            .get_json(
                "/api/user/routing-categories",
                "api_key",
                Some(&[("model".to_string(), model.to_string())]),
            )
            .await
    }
    /// Register a custom provider model — `POST /api/models` with
    /// `{fake_name, endpoint, api_key?, …}` (endpoint is SSRF-validated).
    pub async fn create_custom_model(&self, request: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/models",
                "session",
                Some(serde_json::to_value(request)?),
            )
            .await
    }
    /// Update a custom provider model — `PUT /api/models/{name}`.
    pub async fn update_custom_model(&self, name: &str, request: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PUT,
                &format!("/api/models/{}", enc(name)),
                "session",
                Some(serde_json::to_value(request)?),
            )
            .await
    }
    /// Delete a custom provider model — `DELETE /api/models/{name}`.
    pub async fn delete_custom_model(&self, name: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/api/models/{}", enc(name)),
                "session",
                None,
            )
            .await
    }
    pub async fn sessions(&self) -> Result<Value> {
        self.client
            .get_json("/api/me/sessions", "session", None)
            .await
    }
    pub async fn revoke_session(&self, jti: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/api/me/sessions/{}", enc(jti)),
                "session",
                None,
            )
            .await
    }
    pub async fn revoke_other_sessions(&self) -> Result<Value> {
        self.client
            .request_json(Method::DELETE, "/api/me/sessions", "session", None)
            .await
    }
    pub async fn login_history(&self, limit: Option<u32>) -> Result<Value> {
        let query = limit.map(|l| vec![("limit".to_string(), l.to_string())]);
        self.client
            .get_json("/api/me/login-history", "session", query.as_deref())
            .await
    }
    pub async fn reset_api_key(&self) -> Result<Value> {
        self.client
            .request_json(Method::POST, "/api/user/reset-api-key", "session", None)
            .await
    }
    pub async fn set_primary_allowed_ips(&self, ips: impl Serialize) -> Result<Value> {
        let body = json!({ "allowed_ips": serde_json::to_value(ips)? });
        self.client
            .request_json(
                Method::PUT,
                "/api/user/primary-allowed-ips",
                "session",
                Some(body),
            )
            .await
    }
    pub async fn set_backup_pool_enabled(&self, enabled: bool) -> Result<Value> {
        let body = json!({ "enabled": enabled });
        self.client
            .request_json(
                Method::PUT,
                "/api/user/backup-pool-enabled",
                "api_key",
                Some(body),
            )
            .await
    }
    pub async fn toggle_pay_as_you_go(&self) -> Result<Value> {
        self.client
            .request_json(Method::POST, "/api/pay-as-you-go/toggle", "session", None)
            .await
    }
    /// Soft-close the calling account — `DELETE /api/me/account`.
    ///
    /// Re-authenticates in the body: `password` is required and `totp_code`
    /// is required when 2FA is enrolled (400 `totp_required` otherwise; 401
    /// `invalid_credentials` on bad re-auth). Revokes every session and OAuth
    /// token, rotates the primary API key, disables secondary keys and
    /// cancels subscriptions. The remaining balance is forfeited **only**
    /// when `forfeit_balance_ack` is `true` (never auto-refunded). Idempotent
    /// — a repeat call returns `{closed: true}`. The account can be restored
    /// within a 14-day grace window via
    /// [`Auth::reactivate`](crate::Auth::reactivate).
    pub async fn close_account(
        &self,
        password: &str,
        totp_code: Option<&str>,
        forfeit_balance_ack: bool,
    ) -> Result<Value> {
        let mut body = json!({
            "password": password,
            "forfeit_balance_ack": forfeit_balance_ack,
        });
        if let Some(code) = totp_code {
            body["totp_code"] = json!(code);
        }
        self.client
            .request_json(Method::DELETE, "/api/me/account", "session", Some(body))
            .await
    }
}

/// API key provisioning — `/v1/keys`.
pub struct Keys<'a> {
    pub(crate) client: &'a Client,
}

impl Keys<'_> {
    pub async fn create(&self, request: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/v1/keys",
                "api_key",
                Some(serde_json::to_value(request)?),
            )
            .await
    }
    pub async fn list(&self) -> Result<Value> {
        let res = self.client.get_json("/v1/keys", "api_key", None).await?;
        Ok(res.get("keys").cloned().unwrap_or(res))
    }
    pub async fn update(&self, key: &str, request: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PATCH,
                &format!("/v1/keys/{}", enc(key)),
                "api_key",
                Some(serde_json::to_value(request)?),
            )
            .await
    }
    pub async fn delete(&self, key: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/v1/keys/{}", enc(key)),
                "api_key",
                None,
            )
            .await
    }
}

/// Billing, plans, and public analytics.
pub struct Billing<'a> {
    pub(crate) client: &'a Client,
}

impl Billing<'_> {
    pub async fn create_checkout(&self, request: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/creem/create-checkout",
                "session",
                Some(serde_json::to_value(request)?),
            )
            .await
    }
    pub async fn create_crypto_invoice(&self, request: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/create-nowpayments-invoice",
                "session",
                Some(serde_json::to_value(request)?),
            )
            .await
    }
    pub async fn create_portal_session(&self) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/create-portal-session",
                "session",
                Some(json!({})),
            )
            .await
    }
    pub async fn analytics(&self) -> Result<Value> {
        self.client.get_json("/v1/analytics", "none", None).await
    }
}
