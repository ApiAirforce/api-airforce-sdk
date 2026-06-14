//! Resource accessors. Each is a thin borrow of the [`Client`](crate::Client).

mod account;
mod auth;
mod catalog;
mod inference;
mod media;

pub use account::{Account, Billing, Keys};
pub use auth::{create_pkce_pair, Auth, AuthorizeParams, OAuth, PkcePair, TwoFactor};
pub use catalog::Models;
pub use inference::{Chat, Gemini, Messages, Responses};
pub use media::{Audio, Images, Video, Voices};

use crate::error::Result;
use serde::Serialize;
use serde_json::Value;

/// Serialize a request and overlay the `stream` flag (for an object body).
pub(crate) fn with_stream(request: impl Serialize, stream: bool) -> Result<Value> {
    let mut value = serde_json::to_value(request)?;
    if let Value::Object(ref mut map) = value {
        map.insert("stream".into(), Value::Bool(stream));
    }
    Ok(value)
}

/// Percent-encode a dynamic path segment (RFC 3986 unreserved set).
pub(crate) fn enc(segment: &str) -> String {
    let mut out = String::with_capacity(segment.len());
    for b in segment.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                out.push(b as char)
            }
            _ => out.push_str(&format!("%{b:02X}")),
        }
    }
    out
}

/// Build a `multipart/form-data` body and its content-type.
pub(crate) fn build_multipart(
    fields: &[(&str, String)],
    files: &[(&str, &str, &[u8])],
) -> (Vec<u8>, String) {
    let boundary = format!("airforceBoundary{:016x}", rand::random::<u64>());
    let mut body: Vec<u8> = Vec::new();
    for (name, value) in fields {
        body.extend_from_slice(
            format!("--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n").as_bytes(),
        );
    }
    for (field, filename, data) in files {
        body.extend_from_slice(
            format!(
                "--{boundary}\r\nContent-Disposition: form-data; name=\"{field}\"; filename=\"{filename}\"\r\nContent-Type: application/octet-stream\r\n\r\n"
            )
            .as_bytes(),
        );
        body.extend_from_slice(data);
        body.extend_from_slice(b"\r\n");
    }
    body.extend_from_slice(format!("--{boundary}--\r\n").as_bytes());
    (body, format!("multipart/form-data; boundary={boundary}"))
}
