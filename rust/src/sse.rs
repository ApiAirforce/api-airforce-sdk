//! Server-Sent Events parsing into a stream of JSON values.

use crate::error::{Error, Result};
use futures::Stream;
use futures::StreamExt;
use serde_json::Value;

/// Turn an SSE HTTP response into a stream of parsed JSON events. Iteration stops
/// at the `[DONE]` sentinel.
pub(crate) fn parse_sse(resp: reqwest::Response) -> impl Stream<Item = Result<Value>> {
    async_stream::try_stream! {
        let mut bytes = resp.bytes_stream();
        let mut buf = String::new();
        let mut data: Vec<String> = Vec::new();

        while let Some(chunk) = bytes.next().await {
            let chunk = chunk.map_err(|e| Error::Connection(e.to_string()))?;
            buf.push_str(&String::from_utf8_lossy(&chunk));
            buf = buf.replace("\r\n", "\n").replace('\r', "\n");

            while let Some(idx) = buf.find('\n') {
                let line: String = buf.drain(..=idx).collect();
                let line = line.trim_end_matches('\n');

                if line.is_empty() {
                    if data.is_empty() {
                        continue;
                    }
                    let payload = std::mem::take(&mut data).join("\n");
                    if payload == "[DONE]" {
                        return;
                    }
                    let value: Value = serde_json::from_str(&payload)?;
                    yield value;
                } else if line.starts_with(':') {
                    // comment / keep-alive
                } else if let Some(rest) = line.strip_prefix("data:") {
                    data.push(rest.strip_prefix(' ').unwrap_or(rest).to_string());
                }
            }
        }

        if !data.is_empty() {
            let payload = data.join("\n");
            if payload != "[DONE]" {
                let value: Value = serde_json::from_str(&payload)?;
                yield value;
            }
        }
    }
}
