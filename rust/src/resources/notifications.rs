use super::enc;
use crate::client::Client;
use crate::error::Result;
use reqwest::Method;
use serde::Serialize;
use serde_json::{json, Value};

/// Notifications — preferences, the in-app feed, and delivery-channel linking
/// (`/api/me/notification-prefs`, `/api/me/notifications`, `/api/me/channels`).
/// All session-authenticated.
pub struct Notifications<'a> {
    pub(crate) client: &'a Client,
}

impl Notifications<'_> {
    /// Read the caller's notification preferences — `GET /api/me/notification-prefs`.
    pub async fn get_prefs(&self) -> Result<Value> {
        self.client
            .get_json("/api/me/notification-prefs", "session", None)
            .await
    }

    /// Partial preference update — `PATCH /api/me/notification-prefs`. An
    /// absent field is unchanged; `quiet_hours: null` clears quiet hours;
    /// unknown channel ids in `routing` are dropped server-side. Returns the
    /// updated preferences.
    pub async fn update_prefs(&self, patch: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PATCH,
                "/api/me/notification-prefs",
                "session",
                Some(serde_json::to_value(patch)?),
            )
            .await
    }

    /// In-app feed, newest first — `GET /api/me/notifications` →
    /// `{items, unread}`. `limit` is 1–100 (default 30); `before` is a
    /// `created_at` cursor for paging.
    pub async fn list(&self, limit: Option<u32>, before: Option<&str>) -> Result<Value> {
        let mut query: Vec<(String, String)> = Vec::new();
        if let Some(l) = limit {
            query.push(("limit".to_string(), l.to_string()));
        }
        if let Some(b) = before {
            query.push(("before".to_string(), b.to_string()));
        }
        let q = if query.is_empty() {
            None
        } else {
            Some(query.as_slice())
        };
        self.client
            .get_json("/api/me/notifications", "session", q)
            .await
    }

    /// Mark specific feed items read — `POST /api/me/notifications/read` with
    /// `{ids}` → `{updated, unread}`.
    pub async fn mark_read(&self, ids: impl Serialize) -> Result<Value> {
        let body = json!({ "ids": serde_json::to_value(ids)? });
        self.client
            .request_json(
                Method::POST,
                "/api/me/notifications/read",
                "session",
                Some(body),
            )
            .await
    }

    /// Mark the whole feed read — `POST /api/me/notifications/read` with
    /// `{all: true}` → `{updated, unread}`.
    pub async fn mark_all_read(&self) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/me/notifications/read",
                "session",
                Some(json!({ "all": true })),
            )
            .await
    }

    /// Linked delivery-channel identities plus linkable channel ids —
    /// `GET /api/me/channels` → `{identities, available_channels}`.
    pub async fn channels(&self) -> Result<Value> {
        self.client
            .get_json("/api/me/channels", "session", None)
            .await
    }

    /// Start linking a channel — `POST /api/me/channels` with
    /// `{channel, address, display?}`. The verification code is delivered
    /// through the channel itself (30-min expiry) →
    /// `{status:'verification_sent', channel}`. Bot channels with an empty
    /// `address` get a one-time link token / deep link instead →
    /// `{status:'link_ready', channel, code, deep_link?, expires_minutes}`.
    pub async fn link_channel(&self, request: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/me/channels",
                "session",
                Some(serde_json::to_value(request)?),
            )
            .await
    }

    /// Complete channel verification with the delivered code —
    /// `POST /api/me/channels/verify` → `{status:'verified', channel}`
    /// (400 on an invalid or expired code).
    pub async fn verify_channel(&self, channel: &str, code: &str) -> Result<Value> {
        let body = json!({ "channel": channel, "code": code });
        self.client
            .request_json(
                Method::POST,
                "/api/me/channels/verify",
                "session",
                Some(body),
            )
            .await
    }

    /// Unlink/revoke a channel identity — `DELETE /api/me/channels/{channel}`
    /// → `{status:'revoked', channel}`.
    pub async fn unlink_channel(&self, channel: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/api/me/channels/{}", enc(channel)),
                "session",
                None,
            )
            .await
    }
}
