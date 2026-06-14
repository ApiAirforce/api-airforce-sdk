# airforce-sdk (Go)

Official Go SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. Standard library only, with
`context.Context` throughout.

## Install

```bash
go get github.com/ApiAirforce/api-airforce-sdk/go
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
```

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
