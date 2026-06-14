# Airforce (C# / .NET)

Official C# SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. Built on `HttpClient` and
`System.Text.Json` (no external dependencies), async throughout with
`CancellationToken` support.

## Install

```bash
dotnet add package Airforce
```

## Quick start

```csharp
using Airforce;

using var client = new AirforceClient("sk-air-..."); // or AIRFORCE_API_KEY env

var res = await client.Chat.CreateAsync(new
{
    model = "claude-opus-4.8",
    messages = new[] { new { role = "user", content = "Write a haiku about airplanes." } },
});

Console.WriteLine(res!["choices"]![0]!["message"]!["content"]!.GetValue<string>());
```

Request bodies are plain objects (anonymous types, dictionaries, or `JsonObject`);
responses are `System.Text.Json.Nodes.JsonNode`, so every field is reachable.

## Streaming

```csharp
await foreach (var chunk in client.Chat.CreateStreamAsync(new
{
    model = "claude-opus-4.8",
    messages = new[] { new { role = "user", content = "Count to five." } },
}))
{
    Console.Write(chunk["choices"]?[0]?["delta"]?["content"]?.GetValue<string>());
}
```

## Fallback models

```csharp
await client.Chat.CreateAsync(new
{
    model = "claude-opus-4.8",
    models = new[] { "claude-opus-4.8", "gpt-5.4", "gemini-2.5-pro" }, // first healthy one wins
    messages = new[] { new { role = "user", content = "hi" } },
});
```

## Media

```csharp
// Image
var img = await client.Images.GenerateAsync(new { model = "image-1", prompt = "a red biplane" });

// Text-to-speech → bytes
byte[] audio = await client.Audio.SpeechAsync(new
{
    model = "eleven-v3", voice = "21m00Tcm4TlvDq8ikWAM", input = "Cleared for takeoff.",
});
await File.WriteAllBytesAsync("out.mp3", audio);

// Video (async — poll until done)
var video = await client.Video.GenerateAndWaitAsync(new { model = "veo-3", prompt = "a paper plane over a city" });
Console.WriteLine(video!["result_url"]!.GetValue<string>());
```

## Account, keys & billing

Account/billing endpoints use a **session token** (JWT). Logging in adopts it
automatically:

```csharp
await client.Auth.LoginAsync("username", "password", "captcha_token");
var me = await client.Account.MeAsync();
Console.WriteLine($"balance (cents): {me!["balance"]!.GetValue<int>()}");

var key = await client.Keys.CreateAsync(new { label = "ci", rpm_limit = 60 });
```

You can also pass a token: `new ClientOptions { SessionToken = jwt }` or
`client.SetSessionToken(jwt)`.

## OAuth (third-party integrators)

```csharp
var (verifier, challenge, _) = OAuthResource.CreatePkcePair();
var url = client.OAuth.AuthorizeUrl(
    clientId: "airforce_...",
    redirectUri: "https://app.example.com/callback",
    scope: new[] { "profile", "chat" },
    codeChallenge: challenge);
// ...after the redirect:
var token = await client.OAuth.ExchangeTokenAsync(new Dictionary<string, string>
{
    ["code"] = code,
    ["redirect_uri"] = "https://app.example.com/callback",
    ["client_id"] = "airforce_...",
    ["code_verifier"] = verifier,
});
```

## Errors

Failures throw an `AirforceException` carrying the status:

```csharp
try
{
    await client.Chat.CreateAsync(request);
}
catch (AirforceException ex) when (ex.IsRateLimited)
{
    Console.WriteLine($"retry after {ex.RetryAfter}");
}
```

`MissingCredentialException`, `ApiConnectionException` and `ApiTimeoutException` cover the
non-HTTP failure modes.

## Configuration

```csharp
new AirforceClient(new ClientOptions
{
    ApiKey = "sk-air-...",
    SessionToken = "...",               // for account/billing endpoints
    BaseUrl = "https://api.airforce",
    Timeout = TimeSpan.FromSeconds(60),
    MaxRetries = 2,                     // retried on 429 / 5xx / network errors
    HttpMessageHandler = customHandler,
});
```

## License

MIT
