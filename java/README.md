# airforce-api (Java)

Official Java SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. Built on `java.net.http` (JDK 11+)
with Jackson for JSON.

## Install

The package is not published to Maven Central yet. Install it from git into your local
Maven repository:

```bash
git clone https://github.com/ApiAirforce/api-airforce-sdk.git
mvn -f api-airforce-sdk/java/pom.xml install
```

Then depend on it as usual:

```xml
<dependency>
  <groupId>com.airforce</groupId>
  <artifactId>airforce-api</artifactId>
  <version>0.0.1</version>
</dependency>
```

Gradle users can add the jar the same way (`mavenLocal()` repository +
`implementation 'com.airforce:airforce-api:0.0.1'`).

## Quick start

```java
import com.airforce.Airforce;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.List;
import java.util.Map;

Airforce client = Airforce.builder().apiKey("sk-air-...").build(); // or AIRFORCE_API_KEY env

JsonNode res = client.chat().create(Map.of(
    "model", "claude-opus-4.8",
    "messages", List.of(Map.of("role", "user", "content", "Write a haiku about airplanes."))));

System.out.println(res.get("choices").get(0).get("message").get("content").asText());
```

Requests are plain `Map<String, Object>` and responses are Jackson `JsonNode`, so every
field of the API is reachable without bespoke model classes.

## Streaming

```java
try (Stream stream = client.chat().createStream(Map.of(
        "model", "claude-opus-4.8",
        "messages", List.of(Map.of("role", "user", "content", "Count to five."))))) {
    for (JsonNode chunk : stream) {
        JsonNode delta = chunk.get("choices").get(0).get("delta").get("content");
        if (delta != null) System.out.print(delta.asText());
    }
}
```

## Fallback models

```java
client.chat().create(Map.of(
    "model", "claude-opus-4.8",
    "models", List.of("claude-opus-4.8", "gpt-5.4", "gemini-2.5-pro"), // first healthy one wins
    "messages", List.of(Map.of("role", "user", "content", "hi"))));
```

## Reasoning output shaping

Reasoning models wrap their reasoning in `<think>...</think>` inside `content` by default.
The `reasoning` request field reshapes that server-side (it is never forwarded upstream):

```java
client.chat().create(Map.of(
    "model", "deepseek-r1",
    "reasoning", Map.of("format", "separate"), // reasoning → message.reasoning, content stays clean
    "messages", List.of(Map.of("role", "user", "content", "hi"))));
// {"reasoning", Map.of("exclude", true)} drops reasoning from the response entirely
```

## Embeddings

```java
JsonNode emb = client.embeddings().create(Map.of(
    "model", "embed-1",
    "input", List.of("first text", "second text")));
JsonNode vector = emb.get("data").get(0).get("embedding");
```

Billed on input tokens only; `input` accepts a string, string[], int[] or int[][].

## Media

```java
// Image
JsonNode img = client.images().generate(Map.of("model", "image-1", "prompt", "a red biplane"));

// Text-to-speech → bytes
byte[] audio = client.audio().speech(Map.of(
    "model", "eleven-v3", "voice", "21m00Tcm4TlvDq8ikWAM", "input", "Cleared for takeoff."));
Files.write(Path.of("out.mp3"), audio);

// Video (async — poll until done)
JsonNode video = client.video().generateAndWait(
    Map.of("model", "veo-3", "prompt", "a paper plane over a city"), 0, 0);
System.out.println(video.get("result_url").asText());

// 3D (async — poll until done, then download the artifact)
JsonNode task = client.threeD().generateAndWait(Map.of(
    "model", "shape-1",
    "image_urls", List.of("https://example.com/toy.png"),
    "resolution", "high"), 0, 0);
byte[] glb = client.threeD().downloadContent(task.get("task_id").asText());
Files.write(Path.of("model.glb"), glb);
```

3D tasks and their artifacts expire after 24 hours; credits are deducted only when a
worker picks up the task, and failures are refunded.

## Account, keys & billing

Account/billing endpoints use a **session token** (JWT). Logging in adopts it
automatically:

```java
client.auth().login("username", "password", "captcha_token");
JsonNode me = client.account().me();
System.out.println("balance (cents): " + me.get("balance").asInt());

JsonNode key = client.keys().create(Map.of("label", "ci", "rpm_limit", 60));
```

You can also pass a token: `Airforce.builder().sessionToken(jwt)` or
`client.setSessionToken(jwt)`.

Account routing preferences (`setRoutingCategoryPrefs`, `setChannelOrderPrefs`,
`setCustomCategories`, `routingCategories`) and custom provider models
(`createCustomModel` / `updateCustomModel` / `deleteCustomModel`) live on
`client.account()` too.

### Account closure

```java
// Soft-close (re-authenticates in the body; totp_code required when 2FA is enrolled)
client.account().closeAccount(Map.of("password", "...", "forfeit_balance_ack", false));

// Undo within the 14-day grace window (public — a closed account has no session)
client.account().reactivate("former@email.com", "...");
```

## Organizations

Team self-service under `/api/org/*` (session token; the org context is implicit via the
caller's membership):

```java
JsonNode org = client.org().get();                 // {org, role}
JsonNode members = client.org().members();         // owner/admin only
JsonNode invite = client.org().createInvite("dev@example.com", null);
JsonNode key = client.org().createKey(Map.of(     // full key shown once
    "member_user_id", "u_123", "label", "ci", "credit_allowance", 500));
JsonNode usage = client.org().usage(null);         // last 30 days
```

Also available: `update` (rename), `updateSso`, `updateMember` / `removeMember`,
`invites` / `acceptInvite` / `revokeInvite`, `keys` / `updateKey` / `deleteKey`.

## Notifications

Preferences, the in-app feed, and delivery-channel linking (session token):

```java
JsonNode prefs = client.notifications().getPrefs();
client.notifications().updatePrefs(Map.of(
    "price_drop", Map.of("enabled", true, "scope", "watchlist_only")));

JsonNode feed = client.notifications().list(30, null);   // {items, unread}
client.notifications().markAllRead();

client.notifications().linkChannel("email", "me@example.com", null);
client.notifications().verifyChannel("email", "123456");  // code arrives via the channel
```

## OAuth (third-party integrators)

```java
Map<String, String> pkce = OAuthResource.createPkcePair();
String url = client.oauth().authorizeUrl(Map.of(
    "client_id", "airforce_...",
    "redirect_uri", "https://app.example.com/callback",
    "scope", List.of("profile", "chat"),
    "code_challenge", pkce.get("challenge")));
// ...after the redirect:
JsonNode token = client.oauth().exchangeToken(Map.of(
    "code", code,
    "redirect_uri", "https://app.example.com/callback",
    "client_id", "airforce_...",
    "code_verifier", pkce.get("verifier")));
```

## Errors

Non-2xx responses throw an `AirforceException` carrying the status:

```java
try {
    client.chat().create(params);
} catch (AirforceException e) {
    if (e.isRateLimited()) System.out.println("retry after " + e.retryAfter());
}
```

`AirforceException.MissingCredential`, `.ApiConnection` and `.ApiTimeout` cover the
non-HTTP failure modes.

## Configuration

```java
Airforce.builder()
    .apiKey("sk-air-...")
    .sessionToken("...")                 // for account/billing endpoints
    .baseUrl("https://api.airforce")
    .timeout(Duration.ofSeconds(60))
    .maxRetries(2)                       // retried on 429 / 5xx / network errors
    .header("x-custom", "value")
    .httpClient(customClient)
    .build();
```

## License

MIT
