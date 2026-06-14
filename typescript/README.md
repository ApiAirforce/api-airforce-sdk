# @api-airforce/sdk

Official TypeScript / JavaScript SDK for the [api.airforce](https://api.airforce)
AI gateway — one OpenAI-compatible API in front of many model providers.

- OpenAI **and** Anthropic **and** Gemini compatible inference
- Streaming via async iterators
- Image, audio (TTS / music / SFX / transcription / dubbing) and video generation
- Account, billing, API-key provisioning, 2FA and OAuth surfaces
- Typed, dependency-free (native `fetch`), ESM + CJS, Node 18+ / browsers / edge

## Install

```bash
npm install @api-airforce/sdk
```

## Quick start

```ts
import { Airforce } from "@api-airforce/sdk";

const airforce = new Airforce({ apiKey: process.env.AIRFORCE_API_KEY });

const res = await airforce.chat.create({
  model: "claude-opus-4.8",
  messages: [{ role: "user", content: "Write a haiku about airplanes." }],
});

console.log(res.choices[0]?.message.content);
console.log("cost (credits):", res.usage?.cost);
```

The API key is read from the `apiKey` option or the `AIRFORCE_API_KEY` environment
variable.

## Streaming

```ts
const stream = await airforce.chat.create({
  model: "claude-opus-4.8",
  messages: [{ role: "user", content: "Count to five." }],
  stream: true,
});

for await (const chunk of stream) {
  process.stdout.write(chunk.choices[0]?.delta.content ?? "");
}
```

Abort a stream with `stream.abort()` or by passing an `AbortSignal` in the options.

## Fallback models

A request can list several models; the gateway routes to the first healthy one and
bills only the model that answers.

```ts
await airforce.chat.create({
  model: "claude-opus-4.8",
  models: ["claude-opus-4.8", "gpt-5.4", "gemini-2.5-pro"],
  messages: [{ role: "user", content: "hi" }],
});
```

## Anthropic & Gemini shapes

```ts
const msg = await airforce.messages.create({
  model: "claude-opus-4.8",
  max_tokens: 1024,
  messages: [{ role: "user", content: "Hello, Claude." }],
});
```

## Media

```ts
// Image
const img = await airforce.images.generate({ model: "image-1", prompt: "a red biplane" });

// Text-to-speech (returns ArrayBuffer)
const audio = await airforce.audio.speech({
  model: "eleven-v3",
  voice: "21m00Tcm4TlvDq8ikWAM",
  input: "Cleared for takeoff.",
});

// Video (async — poll or await completion)
const video = await airforce.video.generateAndWait({
  model: "veo-3",
  prompt: "a paper plane gliding over a city",
});
console.log(video.result_url);
```

## Models

```ts
const models = await airforce.models.list();
const detail = await airforce.models.detail("claude-opus-4.8");
```

## Account, keys & billing

Account, billing and 2FA endpoints use a **session token** (a JWT). Logging in adopts
it automatically:

```ts
await airforce.auth.login({ username, password, captcha_token });
const me = await airforce.account.me();
console.log("balance (cents):", me.balance);

// Provision a scoped secondary API key (uses your primary key):
const key = await airforce.keys.create({ label: "ci", rpm_limit: 60 });
```

You can also pass an existing token: `new Airforce({ apiKey, sessionToken })` or
`client.setSessionToken(jwt)`.

## OAuth (third-party integrators)

```ts
const pkce = await OAuth.createPkcePair();
const url = airforce.oauth.authorizeUrl({
  client_id: "airforce_…",
  redirect_uri: "https://app.example.com/callback",
  scope: ["profile", "chat"],
  code_challenge: pkce.challenge,
});
// …after the redirect:
const token = await airforce.oauth.exchangeToken({
  code,
  redirect_uri: "https://app.example.com/callback",
  client_id: "airforce_…",
  code_verifier: pkce.verifier,
});
```

## Configuration

```ts
new Airforce({
  apiKey: "sk-air-…",
  sessionToken: "…",        // for account/billing endpoints
  baseURL: "https://api.airforce",
  timeout: 60_000,           // ms
  maxRetries: 2,             // retried on 429 / 5xx / network errors
  defaultHeaders: {},
  fetch: customFetch,        // optional
});
```

## Errors

All failures throw an `AirforceError` subclass: `AuthenticationError` (401),
`InsufficientBalanceError` (402), `PermissionDeniedError` (403), `NotFoundError` (404),
`ConflictError` (409), `RateLimitError` (429), `InternalServerError` (5xx),
`AirforceConnectionError` and `AirforceTimeoutError`.

```ts
import { RateLimitError } from "@api-airforce/sdk";

try {
  await airforce.chat.create({ /* … */ });
} catch (err) {
  if (err instanceof RateLimitError) console.log("retry after", err.retryAfter);
}
```

## License

MIT
