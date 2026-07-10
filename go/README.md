# airforce-sdk (Go)

Official Go SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. Standard library only, with
`context.Context` throughout.

## Install

The module is not published with tagged releases yet — it is fetched straight
from the GitHub repository (the module lives in the `go/` subdirectory), so pin
the `main` branch or a specific commit:

```bash
go get github.com/ApiAirforce/api-airforce-sdk/go@main
# or pin a commit:
go get github.com/ApiAirforce/api-airforce-sdk/go@<commit-sha>
```

```go
import airforce "github.com/ApiAirforce/api-airforce-sdk/go"
```

## Quick start

```go
package main

import (
    "context"
    "fmt"

    airforce "github.com/ApiAirforce/api-airforce-sdk/go"
)

func main() {
    client := airforce.New(airforce.WithAPIKey("sk-air-...")) // or AIRFORCE_API_KEY env

    res, err := client.Chat.Create(context.Background(), airforce.ChatCompletionParams{
        Model:    "claude-opus-4.8",
        Messages: []airforce.ChatMessage{{Role: "user", Content: "Write a haiku about airplanes."}},
    })
    if err != nil {
        panic(err)
    }
    fmt.Println(res.Choices[0].Message.Content)
    if res.Usage != nil && res.Usage.Cost != nil {
        fmt.Println("cost (credits):", *res.Usage.Cost)
    }
}
```

## Streaming

```go
stream, err := client.Chat.CreateStream(ctx, airforce.ChatCompletionParams{
    Model:    "claude-opus-4.8",
    Messages: []airforce.ChatMessage{{Role: "user", Content: "Count to five."}},
})
if err != nil {
    panic(err)
}
defer stream.Close()

for stream.Next() {
    for _, c := range stream.Current().Choices {
        fmt.Print(c.Delta.Content)
    }
}
if err := stream.Err(); err != nil {
    panic(err)
}
```

## Fallback models

```go
client.Chat.Create(ctx, airforce.ChatCompletionParams{
    Model:    "claude-opus-4.8",
    Models:   []string{"claude-opus-4.8", "gpt-5.4", "gemini-2.5-pro"}, // first healthy one wins
    Messages: []airforce.ChatMessage{{Role: "user", Content: "hi"}},
})
```

## Reasoning output shaping

For reasoning models the optional `Reasoning` chat parameter controls where the
reasoning ends up in the response. It is consumed server-side and never
forwarded upstream:

```go
res, _ := client.Chat.Create(ctx, airforce.ChatCompletionParams{
    Model:    "claude-opus-4.8",
    Messages: []airforce.ChatMessage{{Role: "user", Content: "Why is the sky blue?"}},
    // "separate" moves reasoning into message.reasoning / delta.reasoning and
    // strips it from content; Exclude: true drops reasoning entirely;
    // absent or "inline" keeps <think>...</think> inline in content.
    Reasoning: &airforce.ReasoningConfig{Format: "separate"},
})
fmt.Println(res.Choices[0].Message.Reasoning) // reasoning, out of band
fmt.Println(res.Choices[0].Message.Content)   // clean answer
```

## Embeddings

```go
emb, _ := client.Embeddings.Create(ctx, airforce.EmbeddingsParams{
    Model: "text-embedding-3-small",
    Input: []string{"first text", "second text"}, // string | []string | []int | [][]int
})
for _, d := range emb.Data {
    fmt.Println(d.Index, d.Embedding)
}
fmt.Println("input tokens:", emb.Usage.PromptTokens) // billed on input tokens only
```

## Media

```go
// Image
img, _ := client.Images.Generate(ctx, airforce.ImageParams{Model: "image-1", Prompt: "a red biplane"})

// Text-to-speech → bytes
audio, _ := client.Audio.Speech(ctx, airforce.SpeechParams{
    Model: "eleven-v3", Voice: "21m00Tcm4TlvDq8ikWAM", Input: "Cleared for takeoff.",
})
os.WriteFile("out.mp3", audio, 0o644)

// Video (async — poll until done)
video, _ := client.Video.GenerateAndWait(ctx,
    airforce.VideoParams{Model: "veo-3", Prompt: "a paper plane over a city"}, 0, 0)
fmt.Println(video.ResultURL)

// 3D (async — poll until done, then download the glb/ply artifact)
task, _ := client.ThreeD.GenerateAndWait(ctx, airforce.ThreeDParams{
    Model:     "some-image-to-3d-model",
    ImageURLs: []string{"https://example.com/toy.png"},
}, 0, 0)
modelBytes, _ := client.ThreeD.Content(ctx, task.TaskID)
os.WriteFile("model."+task.Format, modelBytes, 0o644)
```

Video and 3D tasks are billed only when a worker picks them up; failures are
refunded, and tasks plus their artifacts expire after 24 hours.

## Account, keys & billing

Account/billing endpoints use a **session token** (JWT). Logging in adopts it
automatically:

```go
client.Auth.Login(ctx, "username", "password", "captcha_token")
me, _ := client.Account.Me(ctx)
fmt.Println("balance (cents):", me["balance"])

key, _ := client.Keys.Create(ctx, map[string]any{"label": "ci", "rpm_limit": 60})
fmt.Println(key.Key)
```

You can also pass a token: `airforce.New(airforce.WithSessionToken(jwt))` or
`client.SetSessionToken(jwt)`.

### Routing preferences

Per-user routing preferences (API-key authenticated) live on `Account`:

```go
client.Account.SetRoutingCategoryPrefs(ctx, map[string]string{"claude-opus-4.8": "cat_fast"})
client.Account.SetChannelOrderPrefs(ctx, map[string]any{
    "claude-opus-4.8": map[string]any{"order": []string{"a", "b"}, "auto_fallback": true},
})
cats, _ := client.Account.GetCustomCategories(ctx) // manage with SetCustomCategories (max 20)
_ = cats

// Bring-your-own provider models (session authenticated)
client.Account.CreateCustomModel(ctx, map[string]any{
    "fake_name": "my-model", "endpoint": "https://my-provider.example.com/v1/chat/completions",
})
```

### Account closure

`CloseAccount` soft-closes the account (re-auth in the body; sessions and OAuth
tokens revoked, keys rotated/disabled, subscriptions cancelled). Within the
14-day grace window `Reactivate` reopens it via the former email + password:

```go
client.Account.CloseAccount(ctx, "password", "123456" /* TOTP if enrolled */, false)
// ...up to 14 days later:
client.Account.Reactivate(ctx, "former@example.com", "password")
```

## Organizations

Team self-service (session token; the org context is implicit via membership):

```go
org, _ := client.Org.Get(ctx) // {org, role}
members, _ := client.Org.Members(ctx)
client.Org.CreateInvite(ctx, "teammate@example.com", "member")

// Org keys bill the org owner's wallet; full key material is shown only once.
key, _ := client.Org.CreateKey(ctx, map[string]any{"member_user_id": 7, "label": "ci"})
_ = key

usage, _ := client.Org.Usage(ctx, 0, 0, 0, "") // last 30 days, cost values in cents
_, _, _ = org, members, usage
```

## Notifications

Notification preferences, the in-app feed and delivery-channel linking
(session token):

```go
feed, _ := client.Notifications.List(ctx, 30, "")
fmt.Println("unread:", feed["unread"])
client.Notifications.MarkRead(ctx, nil, true) // mark everything read

client.Notifications.UpdatePrefs(ctx, map[string]any{
    "price_drop": map[string]any{"enabled": true, "threshold_pct": 10},
})

// Link a delivery channel — the verification code arrives through the channel.
client.Notifications.LinkChannel(ctx, "email", "me@example.com", "")
client.Notifications.VerifyChannel(ctx, "email", "123456")
```

## OAuth (third-party integrators)

```go
pkce, _ := airforce.CreatePKCEPair()
url := client.OAuth.AuthorizeURL(airforce.AuthorizeParams{
    ClientID:      "airforce_...",
    RedirectURI:   "https://app.example.com/callback",
    Scope:         []string{"profile", "chat"},
    CodeChallenge: pkce.Challenge,
})
// ...after the redirect:
token, _ := client.OAuth.ExchangeToken(ctx, map[string]string{
    "code":          code,
    "redirect_uri":  "https://app.example.com/callback",
    "client_id":     "airforce_...",
    "code_verifier": pkce.Verifier,
})
```

## Errors

Non-2xx responses return an `*APIError`:

```go
_, err := client.Chat.Create(ctx, params)
var apiErr *airforce.APIError
if errors.As(err, &apiErr) {
    if apiErr.IsRateLimited() {
        fmt.Println("retry after", apiErr.RetryAfter)
    }
}
```

`airforce.ErrMissingCredential` is returned when a credential is required but unset.

## Configuration

```go
airforce.New(
    airforce.WithAPIKey("sk-air-..."),
    airforce.WithSessionToken("..."),         // for account/billing endpoints
    airforce.WithBaseURL("https://api.airforce"),
    airforce.WithTimeout(60*time.Second),
    airforce.WithMaxRetries(2),               // retried on 429 / 5xx / network errors
    airforce.WithHTTPClient(customClient),
)
```

## License

MIT
