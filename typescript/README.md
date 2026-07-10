# @api-airforce/sdk

Official TypeScript / JavaScript SDK for the [api.airforce](https://api.airforce)
AI gateway — one OpenAI-compatible API in front of many model providers.

- OpenAI **and** Anthropic **and** Gemini compatible inference, plus embeddings
- Streaming via async iterators
- Image, audio (TTS / music / SFX / transcription / dubbing), video and 3D generation
- Account, organizations, notifications, billing, API-key provisioning, 2FA and
  OAuth surfaces
- Typed, dependency-free (native `fetch`), ESM + CJS, Node 18+ / browsers / edge

## Install

The package is **not yet published to npm** — install it from the Git repository.
The SDK lives in the `typescript/` subdirectory of the monorepo, so clone, build,
and install from the local path:

```bash
git clone https://github.com/ApiAirforce/api-airforce-sdk.git
cd api-airforce-sdk/typescript
npm install && npm run build

# then, from your project:
npm install /path/to/api-airforce-sdk/typescript
```

Once published, this becomes `npm install @api-airforce/sdk`.

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

## Reasoning output shaping

Reasoning models return their chain of thought wrapped in `<think>…</think>`
inside `content` by default. The `reasoning` request field reshapes that
**response-side** (it is consumed by the gateway, never forwarded upstream):

```ts
const res = await airforce.chat.create({
  model: "deepseek-r1",
  messages: [{ role: "user", content: "Why is the sky blue?" }],
  reasoning: { format: "separate" }, // move it to message.reasoning / delta.reasoning
});

console.log(res.choices[0]?.message.reasoning); // the chain of thought
console.log(res.choices[0]?.message.content);   // the clean answer

// or drop reasoning from the response entirely:
// reasoning: { exclude: true }
```

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

## Embeddings

```ts
const emb = await airforce.embeddings.create({
  model: "text-embedding-3-small",
  input: ["first text", "second text"],
});
console.log(emb.data[0]?.embedding); // number[] (or base64 with encoding_format)
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

// 3D (async task; artifact downloadable once has_result is true)
const task = await airforce.threed.generateAndWait({
  model: "shape-1",
  image_urls: ["https://example.com/toy.png"],
  resolution: "high",
});
const glb = await airforce.threed.downloadContent(task.task_id); // ArrayBuffer
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

### Routing preferences

Per-model routing is self-serve (API-key authenticated): pin a single channel,
pick a routing category, or define your own ordered fallback chain — a model is
governed by exactly one of the three.

```ts
await airforce.account.setRoutingCategoryPrefs({ "claude-opus-4.8": "cheapest" });
await airforce.account.setChannelOrderPrefs({
  "claude-opus-4.8": { order: ["economy", "standard"], auto_fallback: true },
});
const { categories } = await airforce.account.routingCategories("claude-opus-4.8");
```

### Account closure

```ts
// Soft-close (re-auth in the body; totp_code required when 2FA is enrolled).
await airforce.account.closeAccount({ password, forfeit_balance_ack: false });

// Undo within the 14-day grace window (public — uses the former email):
await airforce.auth.reactivate({ email, password });
```

## Organizations

Team self-service under `/api/org/*` (session token). Roles: owner ⊃ admin ⊃ member.

```ts
const { org, role } = await airforce.org.get();
const members = await airforce.org.listMembers();

// Invite a teammate (invite_url is the reliable path; mail is best-effort):
const { invite_url } = await airforce.org.createInvite({ email: "dev@acme.com" });

// Issue an org key for a member (full key shown once; bills the org owner):
const key = await airforce.org.createKey({ member_user_id: "u_123", label: "ci" });

// Usage rollup (cents), filterable by member / key / time window:
const usage = await airforce.org.usage({ member_user_id: "u_123" });
```

## Notifications

Preferences, the in-app feed, and delivery-channel linking (session token).

```ts
const { items, unread } = await airforce.notifications.list({ limit: 20 });
await airforce.notifications.markRead({ all: true });

await airforce.notifications.updatePrefs({
  digest_frequency: "daily",
  price_drop: { enabled: true, scope: "watchlist_only" },
});

// Link a delivery channel (the verification code arrives through the channel):
await airforce.notifications.linkChannel({ channel: "email", address: "me@acme.com" });
await airforce.notifications.verifyChannel({ channel: "email", code: "123456" });
```

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
