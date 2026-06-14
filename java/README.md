# airforce-api (Java)

Official Java SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. Built on `java.net.http` (JDK 11+)
with Jackson for JSON.

## Install (Maven)

```xml
<dependency>
  <groupId>com.airforce</groupId>
  <artifactId>airforce-api</artifactId>
  <version>0.0.1</version>
</dependency>
```

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
```

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
