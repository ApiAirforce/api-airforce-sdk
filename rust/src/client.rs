//! The Airforce client, builder and HTTP transport.

use crate::error::{Error, Result};
use crate::resources::*;
use reqwest::Method;
use serde_json::Value;
use std::sync::{Arc, RwLock};
use std::time::Duration;

pub(crate) const VERSION: &str = "0.0.1";
const DEFAULT_BASE_URL: &str = "https://api.airforce";
// 409 is intentionally excluded: a terminal business conflict, not transient.
const RETRYABLE: &[u16] = &[408, 429, 500, 502, 503, 504];

struct Inner {
    http: reqwest::Client,
    api_key: Option<String>,
    session_token: RwLock<Option<String>>,
    base_url: String,
    timeout: Duration,
    max_retries: u32,
    default_headers: Vec<(String, String)>,
}

/// The api.airforce API client. Cheap to clone (shares one connection pool).
#[derive(Clone)]
pub struct Client {
    inner: Arc<Inner>,
}

/// Builder for [`Client`].
pub struct ClientBuilder {
    api_key: Option<String>,
    session_token: Option<String>,
    base_url: Option<String>,
    timeout: Duration,
    max_retries: u32,
    default_headers: Vec<(String, String)>,
    http: Option<reqwest::Client>,
}

impl Default for ClientBuilder {
    fn default() -> Self {
        ClientBuilder {
            api_key: None,
            session_token: None,
            base_url: None,
            timeout: Duration::from_secs(60),
            max_retries: 2,
            default_headers: Vec::new(),
            http: None,
        }
    }
}

impl ClientBuilder {
    pub fn api_key(mut self, key: impl Into<String>) -> Self {
        self.api_key = Some(key.into());
        self
    }
    pub fn session_token(mut self, token: impl Into<String>) -> Self {
        self.session_token = Some(token.into());
        self
    }
    pub fn base_url(mut self, url: impl Into<String>) -> Self {
        self.base_url = Some(url.into());
        self
    }
    pub fn timeout(mut self, timeout: Duration) -> Self {
        self.timeout = timeout;
        self
    }
    pub fn max_retries(mut self, n: u32) -> Self {
        self.max_retries = n;
        self
    }
    pub fn header(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.default_headers.push((key.into(), value.into()));
        self
    }
    pub fn http_client(mut self, client: reqwest::Client) -> Self {
        self.http = Some(client);
        self
    }

    pub fn build(self) -> Client {
        let api_key = self
            .api_key
            .or_else(|| std::env::var("AIRFORCE_API_KEY").ok());
        let session = self
            .session_token
            .or_else(|| std::env::var("AIRFORCE_SESSION_TOKEN").ok());
        let base_url = self
            .base_url
            .or_else(|| std::env::var("AIRFORCE_BASE_URL").ok())
            .unwrap_or_else(|| DEFAULT_BASE_URL.to_string());
        Client {
            inner: Arc::new(Inner {
                http: self.http.unwrap_or_default(),
                api_key,
                session_token: RwLock::new(session),
                base_url: base_url.trim_end_matches('/').to_string(),
                timeout: self.timeout,
                max_retries: self.max_retries,
                default_headers: self.default_headers,
            }),
        }
    }
}

impl Client {
    pub fn builder() -> ClientBuilder {
        ClientBuilder::default()
    }

    /// Create a client from the environment (AIRFORCE_API_KEY etc.).
    pub fn new() -> Self {
        ClientBuilder::default().build()
    }

    pub fn from_api_key(key: impl Into<String>) -> Self {
        ClientBuilder::default().api_key(key).build()
    }

    pub fn base_url(&self) -> &str {
        &self.inner.base_url
    }

    pub fn set_session_token(&self, token: Option<String>) {
        *self.inner.session_token.write().unwrap() = token;
    }

    // --- resource accessors --------------------------------------------------

    pub fn chat(&self) -> Chat<'_> {
        Chat { client: self }
    }
    pub fn messages(&self) -> Messages<'_> {
        Messages { client: self }
    }
    pub fn responses(&self) -> Responses<'_> {
        Responses { client: self }
    }
    pub fn gemini(&self) -> Gemini<'_> {
        Gemini { client: self }
    }
    pub fn models(&self) -> Models<'_> {
        Models { client: self }
    }
    pub fn images(&self) -> Images<'_> {
        Images { client: self }
    }
    pub fn audio(&self) -> Audio<'_> {
        Audio { client: self }
    }
    pub fn video(&self) -> Video<'_> {
        Video { client: self }
    }
    pub fn voices(&self) -> Voices<'_> {
        Voices { client: self }
    }
    pub fn account(&self) -> Account<'_> {
        Account { client: self }
    }
    pub fn keys(&self) -> Keys<'_> {
        Keys { client: self }
    }
    pub fn billing(&self) -> Billing<'_> {
        Billing { client: self }
    }
    pub fn two_factor(&self) -> TwoFactor<'_> {
        TwoFactor { client: self }
    }
    pub fn auth(&self) -> Auth<'_> {
        Auth { client: self }
    }
    pub fn oauth(&self) -> OAuth<'_> {
        OAuth { client: self }
    }

    // --- transport -----------------------------------------------------------

    fn resolve_token(&self, auth: &str) -> Result<Option<String>> {
        match auth {
            "none" => Ok(None),
            "session" => match self.inner.session_token.read().unwrap().clone() {
                Some(t) => Ok(Some(t)),
                // Session endpoints require a session JWT — never substitute an API key.
                None => Err(Error::MissingCredential(
                    "This endpoint requires a session token (set session_token / auth().login())."
                        .into(),
                )),
            },
            _ => {
                let token = self
                    .inner
                    .api_key
                    .clone()
                    .or_else(|| self.inner.session_token.read().unwrap().clone());
                match token {
                    Some(t) => Ok(Some(t)),
                    None => Err(Error::MissingCredential(
                        "This endpoint requires an API key (set api_key).".into(),
                    )),
                }
            }
        }
    }

    #[allow(clippy::too_many_arguments)]
    async fn send(
        &self,
        method: Method,
        path: &str,
        auth: &str,
        body: Option<Vec<u8>>,
        content_type: Option<&str>,
        query: Option<&[(String, String)]>,
        extra_headers: Option<&[(String, String)]>,
        stream: bool,
    ) -> Result<reqwest::Response> {
        let token = self.resolve_token(auth)?;
        let url = if path.starts_with('/') {
            format!("{}{}", self.inner.base_url, path)
        } else {
            format!("{}/{}", self.inner.base_url, path)
        };

        let mut attempt = 0u32;
        loop {
            let mut rb = self
                .inner
                .http
                .request(method.clone(), &url)
                .timeout(self.inner.timeout)
                .header("user-agent", format!("airforce-sdk-rust/{VERSION}"))
                .header("x-airforce-sdk", format!("rust/{VERSION}"))
                .header(
                    reqwest::header::ACCEPT,
                    if stream {
                        "text/event-stream"
                    } else {
                        "application/json"
                    },
                );
            if let Some(q) = query {
                rb = rb.query(q);
            }
            if let Some(t) = &token {
                rb = rb.header(reqwest::header::AUTHORIZATION, format!("Bearer {t}"));
            }
            for (k, v) in &self.inner.default_headers {
                rb = rb.header(k, v);
            }
            if let Some(hs) = extra_headers {
                for (k, v) in hs {
                    rb = rb.header(k, v);
                }
            }
            if let Some(b) = &body {
                if let Some(ct) = content_type {
                    rb = rb.header(reqwest::header::CONTENT_TYPE, ct);
                }
                rb = rb.body(b.clone());
            }

            match rb.send().await {
                Ok(resp) => {
                    let status = resp.status();
                    if status.is_success() {
                        return Ok(resp);
                    }
                    let code = status.as_u16();
                    let ra = retry_after(&resp);
                    if RETRYABLE.contains(&code) && attempt < self.inner.max_retries {
                        attempt += 1;
                        sleep_backoff(attempt, ra).await;
                        continue;
                    }
                    let request_id = resp
                        .headers()
                        .get("x-request-id")
                        .and_then(|v| v.to_str().ok())
                        .map(String::from);
                    let text = resp.text().await.unwrap_or_default();
                    return Err(Error::from_response(code, &text, request_id, ra));
                }
                Err(e) => {
                    // A transport error leaves a POST's outcome unknown — retrying could
                    // double-charge a billable request. Only retry idempotent methods.
                    if attempt < self.inner.max_retries && method != Method::POST {
                        attempt += 1;
                        sleep_backoff(attempt, 0.0).await;
                        continue;
                    }
                    if e.is_timeout() {
                        return Err(Error::Timeout(format!("request to {path} timed out")));
                    }
                    return Err(Error::Connection(format!("request to {path} failed: {e}")));
                }
            }
        }
    }

    async fn read_json(resp: reqwest::Response) -> Result<Value> {
        let data = resp
            .bytes()
            .await
            .map_err(|e| Error::Connection(e.to_string()))?;
        if data.is_empty() {
            Ok(Value::Null)
        } else {
            Ok(serde_json::from_slice(&data)?)
        }
    }

    pub(crate) async fn request_json(
        &self,
        method: Method,
        path: &str,
        auth: &str,
        body: Option<Value>,
    ) -> Result<Value> {
        let bytes = body.as_ref().map(serde_json::to_vec).transpose()?;
        let ct = bytes.as_ref().map(|_| "application/json");
        let resp = self
            .send(method, path, auth, bytes, ct, None, None, false)
            .await?;
        Self::read_json(resp).await
    }

    pub(crate) async fn get_json(
        &self,
        path: &str,
        auth: &str,
        query: Option<&[(String, String)]>,
    ) -> Result<Value> {
        let resp = self
            .send(Method::GET, path, auth, None, None, query, None, false)
            .await?;
        Self::read_json(resp).await
    }

    pub(crate) async fn request_bytes(
        &self,
        method: Method,
        path: &str,
        auth: &str,
        body: Option<Value>,
    ) -> Result<Vec<u8>> {
        let bytes = body.as_ref().map(serde_json::to_vec).transpose()?;
        let ct = bytes.as_ref().map(|_| "application/json");
        let resp = self
            .send(method, path, auth, bytes, ct, None, None, false)
            .await?;
        Ok(resp
            .bytes()
            .await
            .map_err(|e| Error::Connection(e.to_string()))?
            .to_vec())
    }

    pub(crate) async fn multipart_json(
        &self,
        path: &str,
        auth: &str,
        body: Vec<u8>,
        content_type: &str,
    ) -> Result<Value> {
        let resp = self
            .send(
                Method::POST,
                path,
                auth,
                Some(body),
                Some(content_type),
                None,
                None,
                false,
            )
            .await?;
        Self::read_json(resp).await
    }

    pub(crate) async fn multipart_bytes(
        &self,
        path: &str,
        auth: &str,
        body: Vec<u8>,
        content_type: &str,
    ) -> Result<Vec<u8>> {
        let resp = self
            .send(
                Method::POST,
                path,
                auth,
                Some(body),
                Some(content_type),
                None,
                None,
                false,
            )
            .await?;
        Ok(resp
            .bytes()
            .await
            .map_err(|e| Error::Connection(e.to_string()))?
            .to_vec())
    }

    pub(crate) async fn form(&self, path: &str, encoded: String) -> Result<Value> {
        let resp = self
            .send(
                Method::POST,
                path,
                "none",
                Some(encoded.into_bytes()),
                Some("application/x-www-form-urlencoded"),
                None,
                None,
                false,
            )
            .await?;
        Self::read_json(resp).await
    }

    pub(crate) async fn get_with_header(
        &self,
        path: &str,
        header: (String, String),
    ) -> Result<Value> {
        let resp = self
            .send(
                Method::GET,
                path,
                "none",
                None,
                None,
                None,
                Some(&[header]),
                false,
            )
            .await?;
        Self::read_json(resp).await
    }

    pub(crate) async fn open_stream(
        &self,
        method: Method,
        path: &str,
        auth: &str,
        body: Option<Value>,
    ) -> Result<reqwest::Response> {
        let bytes = body.as_ref().map(serde_json::to_vec).transpose()?;
        let ct = bytes.as_ref().map(|_| "application/json");
        self.send(method, path, auth, bytes, ct, None, None, true)
            .await
    }

    pub(crate) async fn submit_with_cookie(
        &self,
        path: &str,
        body: Option<Value>,
        headers: Option<&[(String, String)]>,
    ) -> Result<(Value, Option<String>)> {
        let bytes = body.as_ref().map(serde_json::to_vec).transpose()?;
        let ct = bytes.as_ref().map(|_| "application/json");
        let resp = self
            .send(Method::POST, path, "none", bytes, ct, None, headers, false)
            .await?;
        let cookie = resp
            .headers()
            .get_all(reqwest::header::SET_COOKIE)
            .iter()
            .filter_map(|v| v.to_str().ok())
            .find_map(|c| {
                let idx = c.find("airforce_session=")?;
                let rest = &c[idx + "airforce_session=".len()..];
                Some(rest.split(';').next().unwrap_or(rest).to_string())
            });
        let json = Self::read_json(resp).await?;
        Ok((json, cookie))
    }
}

impl Default for Client {
    fn default() -> Self {
        Client::new()
    }
}

fn retry_after(resp: &reqwest::Response) -> f64 {
    resp.headers()
        .get(reqwest::header::RETRY_AFTER)
        .and_then(|v| v.to_str().ok())
        .and_then(|s| s.parse::<f64>().ok())
        .unwrap_or(0.0)
}

async fn sleep_backoff(attempt: u32, retry_after: f64) {
    let base = if retry_after > 0.0 {
        retry_after
    } else {
        2f64.powi(attempt as i32 - 1).min(8.0)
    };
    let jitter = base * 0.25 * rand::random::<f64>();
    tokio::time::sleep(Duration::from_secs_f64(base + jitter)).await;
}
