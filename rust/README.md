# airforce (Rust)

Official Rust SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. Async (Tokio + reqwest), with
`serde_json::Value` request/response bodies so every field is reachable.

## Install

The crate is not yet published to crates.io — install it straight from the Git
repository (Cargo locates the `airforce` package inside the repo automatically):

```toml
[dependencies]
airforce = { git = "https://github.com/ApiAirforce/api-airforce-sdk" }
tokio = { version = "1", features = ["full"] }
serde_json = "1"
futures = "0.3"
```

Pin a revision with `rev = "<commit>"` (or `branch = "main"`) for reproducible
builds.

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

## Reasoning output shaping

By default, models that think emit `<think>…</think>` blocks inline in `content`.
The `reasoning` request field reshapes that server-side (it is never forwarded
upstream):

```rust
client.chat().create(json!({
    "model": "claude-opus-4.8",
    "messages": [{ "role": "user", "content": "Why is the sky blue?" }],
    "reasoning": { "format": "separate" }, // → message.reasoning / delta.reasoning
    // or: "reasoning": { "exclude": true }    // drop reasoning entirely
})).await?;
```

## Embeddings

```rust
let res = client.embeddings().create(json!({
    "model": "text-embed-1",
    "input": ["first text", "second text"], // string | string[] | tokens
})).await?;
println!("{} vectors", res["data"].as_array().unwrap().len());
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

// 3D (async — poll, then download the glb/ply artifact)
let task = client.three_d()
    .generate_and_wait(json!({ "model": "shape-1", "prompt": "a toy biplane" }),
        Duration::from_millis(2500), Duration::from_secs(600)).await?;
let bytes = client.three_d().content(task["task_id"].as_str().unwrap()).await?;
std::fs::write("model.glb", bytes)?;
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

Routing preferences (API-key-authed) live on the same resource:
`set_routing_category_prefs`, `set_channel_order_prefs`,
`get_custom_categories` / `set_custom_categories`, `routing_categories(model)`,
plus custom provider model CRUD (`create_custom_model` / `update_custom_model` /
`delete_custom_model`).

### Account closure

```rust
// Soft-close (re-auth in the body; balance forfeited only when acknowledged)
client.account().close_account("password", Some("123456"), false).await?;

// ...restore within the 14-day grace window (no session minted):
client.auth().reactivate("former@email.com", "password").await?;
```

## Organizations

Team self-service (session JWT; the org context is implicit via membership):

```rust
let org = client.org().get().await?;               // {org, role}
let members = client.org().members().await?;       // owner/admin
client.org().create_invite(json!({ "email": "dev@example.com" })).await?;
let key = client.org().create_key(json!({ "member_user_id": "u_123", "label": "ci" })).await?;
let usage = client.org().usage(&[("from", "1750000000")]).await?;
```

## Notifications

Preferences, the in-app feed, and delivery-channel linking (session JWT):

```rust
let feed = client.notifications().list(Some(30), None).await?; // {items, unread}
client.notifications().mark_all_read().await?;

client.notifications().update_prefs(json!({
    "price_drop": { "enabled": true, "scope": "watchlist_only" },
})).await?;

// Link a delivery channel (code arrives through the channel itself)
client.notifications().link_channel(json!({ "channel": "email", "address": "me@example.com" })).await?;
client.notifications().verify_channel("email", "123456").await?;
```

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
