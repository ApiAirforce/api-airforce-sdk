use super::enc;
use crate::client::Client;
use crate::error::Result;
use reqwest::Method;
use serde::Serialize;
use serde_json::{json, Value};

/// Organization self-service — `/api/org/*` (session JWT).
///
/// The org context is implicit via the caller's membership (one org per user).
/// Endpoints return `404 no_org` when the caller belongs to no org and
/// `403 membership_inactive` for suspended members. Roles: `owner` ⊃ `admin` ⊃
/// `member`; the required role is noted per method.
pub struct Org<'a> {
    pub(crate) client: &'a Client,
}

impl Org<'_> {
    /// The caller's org and own role — `GET /api/org` → `{org, role}`.
    pub async fn get(&self) -> Result<Value> {
        self.client.get_json("/api/org", "session", None).await
    }

    /// Rename the org (owner only; 1–100 chars) — `PATCH /api/org`.
    pub async fn rename(&self, name: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::PATCH,
                "/api/org",
                "session",
                Some(json!({ "name": name })),
            )
            .await
    }

    /// Owner-only SSO configuration — `PATCH /api/org/sso` with
    /// `{tenant_id?, verified_domain?, enforced?}`. An empty string clears a
    /// field; an omitted field is unchanged. `409` when the tenant or domain
    /// is already claimed by another org.
    pub async fn update_sso(&self, patch: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PATCH,
                "/api/org/sso",
                "session",
                Some(serde_json::to_value(patch)?),
            )
            .await
    }

    /// List members (owner/admin) — returns the `members` array.
    pub async fn members(&self) -> Result<Value> {
        let res = self
            .client
            .get_json("/api/org/members", "session", None)
            .await?;
        Ok(res.get("members").cloned().unwrap_or(res))
    }

    /// Change a member's role and/or status — `PATCH /api/org/members/{user_id}`
    /// with `{role?, status?}`. Role changes are owner-only; suspending a
    /// member disables their org keys; the owner row is immutable.
    pub async fn update_member(&self, user_id: &str, patch: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PATCH,
                &format!("/api/org/members/{}", enc(user_id)),
                "session",
                Some(serde_json::to_value(patch)?),
            )
            .await
    }

    /// Remove a member (owner/admin), or leave the org when `user_id` is the
    /// caller. The owner cannot be removed; the member's org keys are disabled.
    pub async fn remove_member(&self, user_id: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/api/org/members/{}", enc(user_id)),
                "session",
                None,
            )
            .await
    }

    /// List pending invites (owner/admin) — returns the `invites` array.
    pub async fn invites(&self) -> Result<Value> {
        let res = self
            .client
            .get_json("/api/org/invites", "session", None)
            .await?;
        Ok(res.get("invites").cloned().unwrap_or(res))
    }

    /// Invite by email — `POST /api/org/invites` with `{email, role?='member'}`
    /// (admin invites are owner-only; 7-day expiry). Mail delivery is
    /// best-effort — the returned `invite_url` is the reliable path.
    pub async fn create_invite(&self, request: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/org/invites",
                "session",
                Some(serde_json::to_value(request)?),
            )
            .await
    }

    /// Accept an invite token (any logged-in user without an org; the account
    /// email must match the invite and be verified) — `POST /api/org/invites/accept`.
    pub async fn accept_invite(&self, token: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/org/invites/accept",
                "session",
                Some(json!({ "token": token })),
            )
            .await
    }

    /// Revoke a pending invite (owner/admin) — `DELETE /api/org/invites/{id}`.
    pub async fn revoke_invite(&self, id: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/api/org/invites/{}", enc(id)),
                "session",
                None,
            )
            .await
    }

    /// List org keys (owner/admin: all; member: own only) — returns the `keys`
    /// array. Key material is masked.
    pub async fn keys(&self) -> Result<Value> {
        let res = self
            .client
            .get_json("/api/org/keys", "session", None)
            .await?;
        Ok(res.get("keys").cloned().unwrap_or(res))
    }

    /// Create a key for a member (owner/admin) — `POST /api/org/keys` with
    /// `{member_user_id, label?, credit_allowance?, limit_reset?, rpm_limit?,
    /// allowed_models?, …}`. Bills the org owner's wallet. The full key is
    /// returned **only once**.
    pub async fn create_key(&self, request: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/org/keys",
                "session",
                Some(serde_json::to_value(request)?),
            )
            .await
    }

    /// Update an org key (owner/admin) — `PATCH /api/org/keys/{id}` with the
    /// create fields plus `disabled?` (`member_user_id` is not changeable).
    pub async fn update_key(&self, id: &str, patch: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PATCH,
                &format!("/api/org/keys/{}", enc(id)),
                "session",
                Some(serde_json::to_value(patch)?),
            )
            .await
    }

    /// Delete an org key (owner/admin) — `DELETE /api/org/keys/{id}`.
    pub async fn delete_key(&self, id: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/api/org/keys/{}", enc(id)),
                "session",
                None,
            )
            .await
    }

    /// Usage aggregates — `GET /api/org/usage`. Supported `query` pairs:
    /// `from` / `to` (unix seconds, default last 30 days), `member_user_id`,
    /// `key_id`. Members are scoped to their own usage; `cost_cents` values
    /// are cents.
    pub async fn usage(&self, query: &[(&str, &str)]) -> Result<Value> {
        let pairs: Vec<(String, String)> = query
            .iter()
            .map(|&(k, v)| (k.to_string(), v.to_string()))
            .collect();
        let q = if pairs.is_empty() {
            None
        } else {
            Some(pairs.as_slice())
        };
        self.client.get_json("/api/org/usage", "session", q).await
    }
}
