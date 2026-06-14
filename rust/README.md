# airforce (Rust)

Official Rust SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. Async (Tokio + reqwest), with
`serde_json::Value` request/response bodies so every field is reachable.

## Install

```toml
[dependencies]
airforce = "0.0.1"
tokio = { version = "1", features = ["full"] }
serde_json = "1"
futures = "0.3"
```

## Quick start

```rust
use airforce::Client;
use serde_json::json;

#[tokio::main]
async fn main() -> airforce::Result<()> {
    let client = Client::from_api_key("sk-air-..."); // or AIRFORCE_API_KEY env

    let res = client.chat().create(json!({
        "model": "claude-opus-4.8",
        "messages": [{ "role": "user", "content": "Write a haiku about airplanes." }],
    })).await?;

    println!("{}", res["choices"][0]["message"]["content"]);
    Ok(())
}
```

## Streaming

```rust
use futures::StreamExt;

let stream = client.chat().create_stream(json!({
    "model": "claude-opus-4.8",
    "messages": [{ "role": "user", "content": "Count to five." }],
})).await?;
futures::pin_mut!(stream);

while let Some(event) = stream.next().await {
    let event = event?;
    if let Some(c) = event["choices"][0]["delta"]["content"].as_str() {
        print!("{c}");
    }
}
```

## Fallback models

```rust
client.chat().create(json!({
    "model": "claude-opus-4.8",
    "models": ["claude-opus-4.8", "gpt-5.4", "gemini-2.5-pro"], // first healthy one wins
    "messages": [{ "role": "user", "content": "hi" }],
})).await?;
```

## Media

```rust
// Image
let img = client.images().generate(json!({ "model": "image-1", "prompt": "a red biplane" })).await?;

// Text-to-speech → bytes
let audio = client.audio().speech(json!({
    "model": "eleven-v3", "voice": "21m00Tcm4TlvDq8ikWAM", "input": "Cleared for takeoff.",
})).await?;
std::fs::write("out.mp3", audio)?;

// Video (async — poll until done)
use std::time::Duration;
let video = client.video()
    .generate_and_wait(json!({ "model": "veo-3", "prompt": "a paper plane over a city" }),
        Duration::from_millis(2500), Duration::from_secs(600)).await?;
println!("{}", video["result_url"]);
```

## Account, keys & billing

Account/billing endpoints use a **session token** (JWT). Logging in adopts it
automatically:

```rust
client.auth().login("username", "password", "captcha_token").await?;
let me = client.account().me().await?;
println!("balance (cents): {}", me["balance"]);

let key = client.keys().create(json!({ "label": "ci", "rpm_limit": 60 })).await?;
```

You can also pass a token: `Client::builder().session_token(jwt).build()` or
`client.set_session_token(Some(jwt))`.

## OAuth (third-party integrators)

```rust
use airforce::{AuthorizeParams, create_pkce_pair};

let pkce = create_pkce_pair();
let url = client.oauth().authorize_url(AuthorizeParams {
    client_id: "airforce_...",
    redirect_uri: "https://app.example.com/callback",
    scope: &["profile", "chat"],
    code_challenge: Some(&pkce.challenge),
    ..Default::default()
});
// ...after the redirect:
let token = client.oauth().exchange_token(&[
    ("code", &code),
    ("redirect_uri", "https://app.example.com/callback"),
    ("client_id", "airforce_..."),
    ("code_verifier", &pkce.verifier),
]).await?;
```

## Errors

Failures return `airforce::Error`:

```rust
match client.chat().create(request).await {
    Ok(res) => { /* ... */ }
    Err(e) if e.is_rate_limited() => println!("retry after {}", e.retry_after()),
    Err(e) => return Err(e),
}
```

`Error::MissingCredential`, `Error::Connection` and `Error::Timeout` cover the non-HTTP
failure modes.

## Configuration

```rust
use std::time::Duration;

Client::builder()
    .api_key("sk-air-...")
    .session_token("...")          // for account/billing endpoints
    .base_url("https://api.airforce")
    .timeout(Duration::from_secs(60))
    .max_retries(2)                // retried on 429 / 5xx / network errors
    .header("x-custom", "value")
    .build();
```

## License

MIT
