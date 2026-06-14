//! Official Rust SDK for the [api.airforce](https://api.airforce) AI gateway — one
//! OpenAI-compatible API in front of many model providers.
//!
//! ```no_run
//! use airforce::Client;
//! use serde_json::json;
//!
//! # async fn run() -> airforce::Result<()> {
//! let client = Client::from_api_key("sk-air-...");
//! let res = client.chat().create(json!({
//!     "model": "claude-opus-4.8",
//!     "messages": [{ "role": "user", "content": "Hello!" }],
//! })).await?;
//! println!("{}", res["choices"][0]["message"]["content"]);
//! # Ok(())
//! # }
//! ```

mod client;
mod error;
mod resources;
mod sse;

pub use client::{Client, ClientBuilder};
pub use error::{ApiError, Error, Result};
pub use resources::{
    create_pkce_pair, Account, Audio, Auth, AuthorizeParams, Billing, Chat, Gemini, Images, Keys,
    Messages, Models, OAuth, PkcePair, Responses, TwoFactor, Video, Voices,
};
