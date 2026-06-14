//! Error types for the Airforce SDK.

use serde_json::Value;

pub type Result<T> = std::result::Result<T, Error>;

/// Details of a non-2xx HTTP error response.
#[derive(Debug)]
pub struct ApiError {
    pub status: u16,
    pub code: Option<String>,
    pub kind: Option<String>,
    pub message: String,
    pub request_id: Option<String>,
    /// Seconds to wait before retrying (429 responses); 0 if absent.
    pub retry_after: f64,
    pub body: String,
}

#[derive(Debug, thiserror::Error)]
pub enum Error {
    /// A non-2xx HTTP response.
    #[error("airforce: HTTP {}: {}", .0.status, .0.message)]
    Api(Box<ApiError>),
    /// A required credential (API key or session token) was not configured.
    #[error("airforce: {0}")]
    MissingCredential(String),
    /// No HTTP response was received (DNS, TCP, TLS, transport failure).
    #[error("airforce: connection error: {0}")]
    Connection(String),
    /// The request exceeded the configured timeout.
    #[error("airforce: request timed out: {0}")]
    Timeout(String),
    /// Response could not be decoded as JSON.
    #[error("airforce: json error: {0}")]
    Json(String),
}

impl Error {
    pub fn status(&self) -> Option<u16> {
        if let Error::Api(e) = self {
            Some(e.status)
        } else {
            None
        }
    }

    pub fn code(&self) -> Option<&str> {
        if let Error::Api(e) = self {
            e.code.as_deref()
        } else {
            None
        }
    }

    pub fn retry_after(&self) -> f64 {
        if let Error::Api(e) = self {
            e.retry_after
        } else {
            0.0
        }
    }

    pub fn is_status(&self, s: u16) -> bool {
        self.status() == Some(s)
    }
    pub fn is_authentication(&self) -> bool {
        self.is_status(401)
    }
    pub fn is_insufficient_balance(&self) -> bool {
        self.is_status(402)
    }
    pub fn is_permission_denied(&self) -> bool {
        self.is_status(403)
    }
    pub fn is_not_found(&self) -> bool {
        self.is_status(404)
    }
    pub fn is_conflict(&self) -> bool {
        self.is_status(409)
    }
    pub fn is_rate_limited(&self) -> bool {
        self.is_status(429)
    }
    pub fn is_server_error(&self) -> bool {
        matches!(self.status(), Some(s) if s >= 500)
    }

    pub(crate) fn custom(code: &str, message: String) -> Self {
        Error::Api(Box::new(ApiError {
            status: 0,
            code: Some(code.to_string()),
            kind: None,
            message,
            request_id: None,
            retry_after: 0.0,
            body: String::new(),
        }))
    }

    pub(crate) fn from_response(
        status: u16,
        body: &str,
        request_id: Option<String>,
        retry_after: f64,
    ) -> Self {
        let (mut message, mut code, mut kind) = (None, None, None);
        if let Ok(root) = serde_json::from_str::<Value>(body) {
            match root.get("error") {
                Some(Value::Object(_)) => {
                    let err = &root["error"];
                    message = err.get("message").and_then(Value::as_str).map(String::from);
                    code = err.get("code").and_then(Value::as_str).map(String::from);
                    kind = err.get("type").and_then(Value::as_str).map(String::from);
                }
                Some(Value::String(s)) => message = Some(s.clone()),
                _ => {
                    message = root
                        .get("message")
                        .and_then(Value::as_str)
                        .map(String::from);
                    code = root.get("code").and_then(Value::as_str).map(String::from);
                    kind = root.get("type").and_then(Value::as_str).map(String::from);
                }
            }
        }
        Error::Api(Box::new(ApiError {
            status,
            code,
            kind,
            message: message.unwrap_or_else(|| format!("Airforce API error (HTTP {status})")),
            request_id,
            retry_after,
            body: body.to_string(),
        }))
    }
}

impl From<serde_json::Error> for Error {
    fn from(e: serde_json::Error) -> Self {
        Error::Json(e.to_string())
    }
}
