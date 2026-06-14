use super::enc;
use crate::client::Client;
use crate::error::Result;
use base64::Engine as _;
use reqwest::Method;
use serde::Serialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};

const B64URL: base64::engine::GeneralPurpose = base64::engine::general_purpose::URL_SAFE_NO_PAD;

/// A PKCE verifier/challenge pair.
pub struct PkcePair {
    pub verifier: String,
    pub challenge: String,
    pub method: String,
}

/// Generate a PKCE verifier/challenge pair (S256).
pub fn create_pkce_pair() -> PkcePair {
    let bytes: [u8; 32] = rand::random();
    let verifier = B64URL.encode(bytes);
    let challenge = B64URL.encode(Sha256::digest(verifier.as_bytes()));
    PkcePair {
        verifier,
        challenge,
        method: "S256".to_string(),
    }
}

/// Two-factor authentication — `/api/2fa/*`.
pub struct TwoFactor<'a> {
    pub(crate) client: &'a Client,
}

impl TwoFactor<'_> {
    pub async fn setup_init(&self) -> Result<Value> {
        self.client
            .request_json(Method::POST, "/api/2fa/setup-init", "session", None)
            .await
    }
    pub async fn setup_verify(&self, code: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/2fa/setup-verify",
                "session",
                Some(json!({ "code": code })),
            )
            .await
    }
    pub async fn disable(&self, password: &str, code: &str) -> Result<Value> {
        let body = json!({ "password": password, "code": code });
        self.client
            .request_json(Method::POST, "/api/2fa/disable", "session", Some(body))
            .await
    }
    pub async fn regenerate_backup_codes(&self, code: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/2fa/regenerate-backup-codes",
                "session",
                Some(json!({ "code": code })),
            )
            .await
    }
    pub async fn verify_step_up(&self, code: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/2fa/verify-step-up",
                "session",
                Some(json!({ "code": code })),
            )
            .await
    }
    pub async fn step_up_status(&self) -> Result<Value> {
        self.client
            .get_json("/api/2fa/step-up-status", "session", None)
            .await
    }
}

/// Authentication — `/auth/*`. Login/signup adopt the session token automatically.
pub struct Auth<'a> {
    pub(crate) client: &'a Client,
}

impl Auth<'_> {
    async fn submit(
        &self,
        path: &str,
        body: Value,
        headers: Option<&[(String, String)]>,
    ) -> Result<Value> {
        let (mut json, cookie) = self
            .client
            .submit_with_cookie(path, Some(body), headers)
            .await?;
        if let Some(c) = cookie {
            self.client.set_session_token(Some(c.clone()));
            if let Value::Object(ref mut map) = json {
                map.insert("session_token".into(), Value::String(c));
            }
        }
        Ok(json)
    }

    pub async fn signup(&self, request: impl Serialize) -> Result<Value> {
        self.submit("/auth/signup", serde_json::to_value(request)?, None)
            .await
    }

    pub async fn signup_precheck(&self, request: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/auth/signup/precheck",
                "none",
                Some(serde_json::to_value(request)?),
            )
            .await
    }

    pub async fn login(
        &self,
        username: &str,
        password: &str,
        captcha_token: &str,
    ) -> Result<Value> {
        let body =
            json!({ "username": username, "password": password, "captcha_token": captcha_token });
        self.submit("/auth/login", body, None).await
    }

    pub async fn verify_2fa(
        &self,
        challenge_token: &str,
        code: &str,
        backup_code: Option<&str>,
    ) -> Result<Value> {
        let mut body = json!({ "code": code });
        if let Some(bc) = backup_code {
            body["backup_code"] = json!(bc);
        }
        let headers = [(
            "authorization".to_string(),
            format!("Bearer {challenge_token}"),
        )];
        self.submit("/auth/2fa/verify", body, Some(&headers)).await
    }

    pub async fn verify_email(&self, token: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/auth/verify",
                "none",
                Some(json!({ "token": token })),
            )
            .await
    }

    pub async fn resend_verification(&self, identifier: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/auth/resend-verification",
                "none",
                Some(json!({ "identifier": identifier })),
            )
            .await
    }

    pub async fn logout(&self) -> Result<Value> {
        let result = self
            .client
            .request_json(Method::POST, "/auth/logout", "session", None)
            .await?;
        self.client.set_session_token(None);
        Ok(result)
    }
}

/// Inputs to [`OAuth::authorize_url`].
#[derive(Default)]
pub struct AuthorizeParams<'a> {
    pub client_id: &'a str,
    pub redirect_uri: &'a str,
    pub scope: &'a [&'a str],
    pub state: Option<&'a str>,
    pub code_challenge: Option<&'a str>,
    pub code_challenge_method: Option<&'a str>,
}

/// OAuth 2.0 provider flow + self-service app management.
pub struct OAuth<'a> {
    pub(crate) client: &'a Client,
}

impl OAuth<'_> {
    pub fn authorize_url(&self, params: AuthorizeParams) -> String {
        let mut query = vec![
            "response_type=code".to_string(),
            format!("client_id={}", enc(params.client_id)),
            format!("redirect_uri={}", enc(params.redirect_uri)),
        ];
        if !params.scope.is_empty() {
            query.push(format!("scope={}", enc(&params.scope.join(" "))));
        }
        if let Some(s) = params.state {
            query.push(format!("state={}", enc(s)));
        }
        if let Some(c) = params.code_challenge {
            query.push(format!("code_challenge={}", enc(c)));
            query.push(format!(
                "code_challenge_method={}",
                enc(params.code_challenge_method.unwrap_or("S256"))
            ));
        }
        format!(
            "{}/oauth/authorize?{}",
            self.client.base_url(),
            query.join("&")
        )
    }

    pub async fn exchange_token(&self, params: &[(&str, &str)]) -> Result<Value> {
        let mut form = vec![("grant_type", "authorization_code")];
        form.extend_from_slice(params);
        let encoded = form
            .iter()
            .map(|(k, v)| format!("{}={}", enc(k), enc(v)))
            .collect::<Vec<_>>()
            .join("&");
        self.client.form("/oauth/token", encoded).await
    }

    pub async fn user_info(&self, access_token: &str) -> Result<Value> {
        self.client
            .get_with_header(
                "/oauth/userinfo",
                (
                    "authorization".to_string(),
                    format!("Bearer {access_token}"),
                ),
            )
            .await
    }

    pub async fn revoke_token(&self, token: &str) -> Result<Value> {
        self.client
            .form("/oauth/revoke", format!("token={}", enc(token)))
            .await
    }

    pub async fn list_apps(&self) -> Result<Value> {
        self.client
            .get_json("/api/me/oauth-apps", "session", None)
            .await
    }
    pub async fn create_app(&self, request: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                "/api/me/oauth-apps",
                "session",
                Some(serde_json::to_value(request)?),
            )
            .await
    }
    pub async fn get_app(&self, client_id: &str) -> Result<Value> {
        self.client
            .get_json(
                &format!("/api/me/oauth-apps/{}", enc(client_id)),
                "session",
                None,
            )
            .await
    }
    pub async fn update_app(&self, client_id: &str, patch: impl Serialize) -> Result<Value> {
        self.client
            .request_json(
                Method::PATCH,
                &format!("/api/me/oauth-apps/{}", enc(client_id)),
                "session",
                Some(serde_json::to_value(patch)?),
            )
            .await
    }
    pub async fn delete_app(&self, client_id: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/api/me/oauth-apps/{}", enc(client_id)),
                "session",
                None,
            )
            .await
    }
    pub async fn rotate_secret(&self, client_id: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::POST,
                &format!("/api/me/oauth-apps/{}/rotate-secret", enc(client_id)),
                "session",
                None,
            )
            .await
    }
    pub async fn connected_apps(&self) -> Result<Value> {
        self.client
            .get_json("/api/me/connected-apps", "session", None)
            .await
    }
    pub async fn revoke_connected_app(&self, client_id: &str) -> Result<Value> {
        self.client
            .request_json(
                Method::DELETE,
                &format!("/api/me/connected-apps/{}", enc(client_id)),
                "session",
                None,
            )
            .await
    }
}
