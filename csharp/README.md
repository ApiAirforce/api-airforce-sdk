# Airforce (C# / .NET)

Official C# SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. Built on `HttpClient` and
`System.Text.Json` (no external dependencies), async throughout with
`CancellationToken` support.

## Install

The package is not published to NuGet yet — consume the project straight from the git
repository (requires .NET 8.0+):

```bash
git clone https://github.com/ApiAirforce/api-airforce-sdk
dotnet add YourApp.csproj reference api-airforce-sdk/csharp/Airforce/Airforce.csproj
```

Or add the repo as a submodule and reference `csharp/Airforce/Airforce.csproj` the same
way.

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

## Reasoning output

Reasoning models wrap their thinking in `<think>…</think>` inside `content` by default.
The optional `reasoning` request field reshapes that server-side (it is never forwarded
upstream): `format = "separate"` moves it into `message.reasoning` (`delta.reasoning`
when streaming), `exclude = true` drops it entirely.

```csharp
var res = await client.Chat.CreateAsync(new
{
    model = "deepseek-r1",
    messages = new[] { new { role = "user", content = "Why is the sky blue?" } },
    reasoning = new { format = "separate" },
});
Console.WriteLine(res!["choices"]![0]!["message"]!["reasoning"]);
```

## Embeddings

```csharp
var emb = await client.Embeddings.CreateAsync(new
{
    model = "text-embedding-3-small",
    input = new[] { "first text", "second text" },
});
var vector = emb!["data"]![0]!["embedding"]; // billed on input tokens only
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

// 3D (async — poll until done, then download the model file)
var task = await client.ThreeD.GenerateAndWaitAsync(new
{
    model = "trellis-2",
    image_urls = new[] { "https://example.com/chair.png" },
    resolution = "medium",
});
byte[] glb = await client.ThreeD.DownloadAsync(task!["task_id"]!.GetValue<string>());
await File.WriteAllBytesAsync("chair.glb", glb);
```

3D tasks are billed only once a worker claims them (failures are refunded) and expire —
together with their artifacts — after 24 hours.

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

### Routing preferences

Per-user routing controls (API-key-authenticated) live on `client.Account`:

```csharp
await client.Account.SetRoutingCategoryPrefsAsync(new Dictionary<string, string>
{
    ["claude-opus-4.8"] = "fast-lane",
});
await client.Account.SetChannelOrderPrefsAsync(new Dictionary<string, object>
{
    ["claude-opus-4.8"] = new { order = new[] { "alpha", "beta" }, auto_fallback = true },
});
var categories = await client.Account.RoutingCategoriesAsync("claude-opus-4.8");
await client.Account.SetCustomCategoriesAsync(myCategories); // max 20
```

Custom provider models (bring your own endpoint, session-authenticated):

```csharp
await client.Account.CreateCustomModelAsync(new { fake_name = "my-model", endpoint = "https://my-host/v1/chat/completions" });
await client.Account.UpdateCustomModelAsync("my-model", new { endpoint = "https://other-host/v1/chat/completions" });
await client.Account.DeleteCustomModelAsync("my-model");
```

### Account closure

```csharp
// Soft-close: re-authenticates in the body; revokes sessions/OAuth tokens, rotates the
// primary key, disables secondary keys, cancels subscriptions. Idempotent.
await client.Account.CloseAccountAsync("password", totpCode: "123456");

// Undo within the 14-day grace window (public endpoint, former email + password):
await client.Auth.ReactivateAsync("me@example.com", "password");
```

## Notifications

Preferences, the in-app feed, and delivery-channel linking (session token):

```csharp
var prefs = await client.Notifications.GetPrefsAsync();
await client.Notifications.UpdatePrefsAsync(new { digest_frequency = "daily" });

var feed = await client.Notifications.ListAsync(limit: 50);
await client.Notifications.MarkAllReadAsync();

await client.Notifications.LinkChannelAsync("email", "me@example.com");
await client.Notifications.VerifyChannelAsync("email", "123456");
await client.Notifications.UnlinkChannelAsync("email");
```

## Organizations

Team self-service under `/api/org/*` (session token; the org context comes from the
caller's membership). Roles: owner > admin > member.

```csharp
var org = await client.Org.GetAsync();                 // {org, role}
var members = await client.Org.MembersAsync();

var invite = await client.Org.CreateInviteAsync("dev@example.com", role: "member");
Console.WriteLine(invite!["invite_url"]);              // reliable delivery path

// Org keys bill the org owner's wallet; the full key is shown once at create.
var created = await client.Org.CreateKeyAsync(new { member_user_id = "u_123", label = "ci" });
var keys = await client.Org.KeysAsync();               // masked

var usage = await client.Org.UsageAsync(from: 1750000000, to: 1750604800);
Console.WriteLine(usage!["total"]!["cost_cents"]);     // cents
```

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
