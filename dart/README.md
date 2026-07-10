# airforce (Dart)

Official Dart SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. Works on the Dart VM and Flutter.

## Install

The package is not published on pub.dev yet — depend on it straight from Git:

```yaml
dependencies:
  airforce:
    git:
      url: https://github.com/ApiAirforce/api-airforce-sdk.git
      path: dart
```

## Quick start

```dart
import 'package:airforce/airforce.dart';

final client = AirforceClient(apiKey: 'sk-air-...');

final res = await client.chat.create({
  'model': 'claude-opus-4.8',
  'messages': [
    {'role': 'user', 'content': 'Write a haiku about airplanes.'}
  ],
});
print(res['choices'][0]['message']['content']);
```

Request bodies are plain `Map`s; responses are decoded JSON (`Map`/`List`).

## Streaming

```dart
final stream = client.chat.createStream({
  'model': 'claude-opus-4.8',
  'messages': [
    {'role': 'user', 'content': 'Count to five.'}
  ],
});
await for (final chunk in stream) {
  stdout.write(chunk['choices'][0]['delta']['content'] ?? '');
}
```

## Fallback models

```dart
await client.chat.create({
  'model': 'claude-opus-4.8',
  'models': ['claude-opus-4.8', 'gpt-5.4', 'gemini-2.5-pro'], // first healthy one wins
  'messages': [{'role': 'user', 'content': 'hi'}],
});
```

## Reasoning output

Reasoning models return their thinking inline in `content`
(`<think>…</think>`) by default. The optional `reasoning` parameter reshapes
the response server-side (it is never forwarded upstream):

```dart
final res = await client.chat.create({
  'model': 'deepseek-r1',
  'messages': [{'role': 'user', 'content': 'hi'}],
  'reasoning': {'format': 'separate'}, // move it into message.reasoning
  // 'reasoning': {'exclude': true},   // ...or drop it entirely
});
print(res['choices'][0]['message']['reasoning']);
```

## Embeddings

```dart
final res = await client.embeddings.create({
  'model': 'text-embedding-3-small',
  'input': ['first text', 'second text'],
});
print(res['data'][0]['embedding']);
```

## Media

```dart
// Image
final img = await client.images.generate({'model': 'image-1', 'prompt': 'a red biplane'});

// Text-to-speech → bytes
final audio = await client.audio.speech({
  'model': 'eleven-v3', 'voice': '21m00Tcm4TlvDq8ikWAM', 'input': 'Cleared for takeoff.',
});
await File('out.mp3').writeAsBytes(audio);

// Video (async — poll until done)
final video = await client.video.generateAndWait({'model': 'veo-3', 'prompt': 'a paper plane over a city'});
print(video['result_url']);

// 3D (async — poll until done, then download the artifact)
final task = await client.threeD.generateAndWait({
  'model': '3d-1', 'image_urls': ['https://example.com/toy.png'],
});
await File('model.glb').writeAsBytes(await client.threeD.content(task['task_id']));
```

## Account, keys & billing

Account/billing endpoints use a **session token** (JWT). Logging in adopts it
automatically:

```dart
await client.auth.login('username', 'password', 'captcha_token');
final me = await client.account.me();
print('balance (cents): ${me['balance']}');

final key = await client.keys.create({'label': 'ci', 'rpm_limit': 60});
```

You can also pass a token: `AirforceClient(sessionToken: jwt)` or
`client.setSessionToken(jwt)`.

The `account` resource also covers routing preferences (`setRoutingCategoryPrefs`,
`setChannelOrderPrefs`, `getCustomCategories`/`setCustomCategories`,
`getRoutingCategories`) and custom provider models (`addCustomModel`,
`updateCustomModel`, `deleteCustomModel`).

## Organizations

Org endpoints use the session token too; the org context is implicit via your
membership:

```dart
final overview = await client.org.get(); // {org, role}
final members = await client.org.members();
final invite = await client.org.createInvite('teammate@example.com');
final key = await client.org.createKey({'member_user_id': 'u_123', 'label': 'ci'});
final usage = await client.org.usage();
```

## Notifications

```dart
final feed = await client.notifications.list(limit: 20); // {items, unread}
await client.notifications.markRead(all: true);
await client.notifications.updatePrefs({
  'price_drop': {'enabled': true, 'threshold_pct': 10},
});

// Link a delivery channel (code arrives through the channel itself)
await client.notifications.addChannel('email', 'me@example.com');
await client.notifications.verifyChannel('email', '123456');
```

## Account closure

```dart
await client.account.closeAccount(password: 'pw', totpCode: '123456');
// changed your mind? (within the 14-day grace window; no session needed)
await client.auth.reactivate('me@example.com', 'pw');
```

## OAuth (third-party integrators)

```dart
final pkce = createPkcePair();
final url = client.oauth.authorizeUrl(
  clientId: 'airforce_...',
  redirectUri: 'https://app.example.com/callback',
  scope: ['profile', 'chat'],
  codeChallenge: pkce.challenge,
);
// ...after the redirect:
final token = await client.oauth.exchangeToken({
  'code': code,
  'redirect_uri': 'https://app.example.com/callback',
  'client_id': 'airforce_...',
  'code_verifier': pkce.verifier,
});
```

## Errors

Failures throw an `AirforceException`:

```dart
try {
  await client.chat.create(request);
} on AirforceException catch (e) {
  if (e.isRateLimited) print('retry after ${e.retryAfter}');
}
```

`MissingCredentialException`, `ApiConnectionException` and `ApiTimeoutException` cover the
non-HTTP failure modes.

## Configuration

```dart
AirforceClient(
  apiKey: 'sk-air-...',
  sessionToken: '...',            // for account/billing endpoints
  baseUrl: 'https://api.airforce',
  timeout: Duration(seconds: 60),
  maxRetries: 2,                  // retried on 429 / 5xx / network errors
  httpClient: customClient,
);
```

## License

MIT
