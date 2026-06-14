# api.airforce — Public API Surface

This is the language-agnostic contract every SDK in this repo implements. It covers the
**customer-facing** surface only: inference, media, model discovery, account
self-service, keys, OAuth, and billing. The internal `/admin/*` control plane is **out of
scope** for the SDKs.

> Derived from the backend handlers and the frontend/app call sites. When in doubt, the
> Rust handler is authoritative.

---

## 1. Conventions

### Base URL

```
https://api.airforce
```

Paths beginning with `/v1` are the OpenAI/Anthropic/Gemini-compatible inference + media
surface. Paths beginning with `/api` are the account/billing surface. `/oauth/*` and
`/auth/*` are the auth surfaces.

### Authentication

Two credential types exist; the SDK carries one or both and sends them as headers.

| Credential | Format | Header | Used for |
| --- | --- | --- | --- |
| **API key** | `sk-air-…` (primary) or secondary keys | `Authorization: Bearer <key>` (also `x-api-key` for Anthropic-style, `x-goog-api-key`/`?key=` for Gemini) | All `/v1/*` inference + media, `/v1/keys` provisioning, and the `api_key`-marked `/api/user/*` endpoints |
| **OAuth token** | `airf_oat_…` | `Authorization: Bearer <token>` | Third-party access scoped by OAuth scopes (`chat`, `images`, `keys:read`, `keys:write`, `profile`) |
| **Session JWT** | JWT (7-day) | `Authorization: Bearer <jwt>` or `Cookie: airforce_session=<jwt>` | `session_cookie`-marked `/api/*` account + billing endpoints |

Per-endpoint auth is noted as `api_key`, `oauth_bearer`, `session_cookie`, `public`, or
`none`. Many account endpoints require a **session JWT** (obtained via `/auth/login`), not
an API key — the SDK exposes account/billing methods only when a session token is set.

### Money & units

- All monetary fields are **cents** (USD × 100) unless the field name says otherwise.
  Divide by 100 for display.
- `usage.cost` on inference responses is in **credits (USD)** — already divided.
- Token prices are **cents per 1,000,000 tokens** (`pricepermilliontokens`).
- Image prices are **cents per 1,000 images** (`priceperthousandimages`).
- `customer_price_table` components are in **micro-USD** (`price_micro_usd`).

### Errors

JSON error bodies follow either the OpenAI shape or a simple shape:

```jsonc
{ "error": { "message": "string", "type": "string", "param": null, "code": "string" } }
// or
{ "error": "string", "message": "string" }
```

The SDK should surface a typed `AirforceError` carrying `status`, `code`, `type`,
`message`, and the raw body. Notable codes: `free_tier_gated` (403), `account_temporarily_locked`
(429), `email_verification_required` (403), `consent_stale` (400), `insufficient_balance`/402.

> **Inference quirk:** when *all* providers fail, chat/messages endpoints return **HTTP 200
> with empty assistant content and zero usage** ("zero-completion insurance"), not an HTTP
> error. The SDK must treat an empty completion as a soft failure the caller can inspect.

### Streaming (SSE)

Streaming endpoints return `text/event-stream`. Lines are `data: <json>` terminated by a
blank line; the stream ends with `data: [DONE]`. Each compat layer has its own chunk shape
(documented per endpoint). The SDK exposes streaming as an async iterator of typed events.

### NO-LEAK contract

The public API never exposes internal provider/channel codes or internal `__variant`
model names. `model` in requests and responses is always the **public** name. SDK code and
docs must not hardcode or surface internal codes.

### airforce-specific extensions

- **`models` fallback array** (OpenRouter-style): list up to 3 model names; the gateway
  tries each model's full provider chain in order and bills only the one that answers.
  `response.model` reflects whoever answered.
- **`skill` / `skills`**: server-side skill injection, consumed before upstream (never
  forwarded).
- **`transforms: ["middle-out"]`**: drop middle messages on context overflow.
- **smart routing**: `model` is a public group name; routing picks a concrete variant.
  Per-user channel/category/order preferences influence selection.

### Rate limiting

Per-key for paid/multi-key users, per-IP for free. `429` responses may carry
`retry_after`. The SDK should support bounded retries with backoff on `429`/`5xx`.

---

## 2. Inference

### POST `/v1/chat/completions` — `api_key`/`oauth_bearer(chat)` — streaming ✔

OpenAI-compatible chat completions with smart routing + fallback.

**Request** (JSON):
- `model` *(string, required)*, `messages` *(array, required)* of
  `{role: 'system'|'user'|'assistant'|'tool', content: string | ContentPart[], name?, tool_call_id?}`
- `max_tokens?` (u32), `temperature?` (0–2), `top_p?`, `stop?` (string | string[≤4])
- `stream?` (bool), `tools?` ([{type:'function', function:{name, description, parameters}}]),
  `tool_choice?` (`'auto'|'none'` | `{type:'function', function:{name}}`)
- `response_format?` (`{type:'json_object'}`), `reasoning_effort?` (`'low'|'medium'|'high'`)
- `thinking?` (`'on'|'off'|'auto'` | `{type:'enabled', budget_tokens}`), `thinking_budget?` (u32)
- **airforce:** `models?` (string[≤3] fallback), `skill?` (string), `skills?` (string[]),
  `transforms?` (`['middle-out']`), `ignore_defaults?` (bool)

**Response** (non-stream): `{id, object:'chat.completion', created, model, choices:[{index,
message:{role, content?, reasoning?, tool_calls?}, finish_reason}], usage}` where
`usage = {prompt_tokens, completion_tokens, total_tokens, prompt_tokens_details:{cached_tokens?},
cache_creation_input_tokens?, cache_creation:{ephemeral_5m_input_tokens?, ephemeral_1h_input_tokens?},
completion_tokens_details?, cost?}`.

**Response** (stream): SSE chunks `{id, object:'chat.completion.chunk', created, model,
choices:[{index, delta:{role?, content?, reasoning?, tool_calls?}, finish_reason?}], usage?}`.
`usage` arrives on the final chunk. Terminate on `data: [DONE]`.

### POST `/v1/messages` — `api_key` (also `x-api-key`) / `oauth_bearer(chat)` — streaming ✔

Anthropic-compatible messages; internally re-routed through chat completions.

**Request**: `{model, messages:[{role:'user'|'assistant', content: string | Block[]}], max_tokens,
system?: string | {type:'text', text, cache_control?}[], temperature?, top_p?, top_k?,
stop_sequences?, stream?, tools?:[{type, name, description, input_schema}], tool_choice?:{type:'auto'|'any'|'tool', name?},
thinking?:{type:'enabled', budget_tokens}, fallbacks?:[{model}], models?:string[≤3]}`.

**Response** (non-stream): `{id, type:'message', role:'assistant', content:[{type:'text'|'thinking'|'tool_use', ...}],
model, stop_reason, stop_sequence, usage:{input_tokens, output_tokens, cache_read_input_tokens?,
cache_creation_input_tokens?, cache_creation:{ephemeral_5m_input_tokens?, ephemeral_1h_input_tokens?}, cost?}}`.

**Response** (stream): Anthropic event sequence — `message_start`, `content_block_start`,
`content_block_delta` (`text_delta`/`thinking_delta`/`input_json_delta`), `content_block_stop`,
`message_delta` (+usage), `message_stop`.

### POST `/v1/messages/count_tokens` — `api_key`/`oauth_bearer(chat)`

`{system?, messages, tools?}` → `{input_tokens}`. Local estimate (no upstream call).

### POST `/v1/responses` — `api_key`/`oauth_bearer(chat)` — streaming ✔

OpenAI Responses API shape; translated to chat completions. `{model, instructions?, input:
string | Item[], tools?, tool_choice?, max_output_tokens?, temperature?, top_p?, stream?,
reasoning?:{effort}}`. Stream emits `response.*` events (`response.created`,
`response.output_text.delta`, `response.completed`, …). No `models` fallback support.

### POST `/v1beta/models/{model}:{method}` — `api_key` (`x-goog-api-key`/`?key=`) — streaming ✔

Gemini-compatible. `{method}` is `generateContent` or `streamGenerateContent`.
Request `{systemInstruction?, contents:[{role:'user'|'model', parts:[...]}], tools?, toolConfig?,
generationConfig?:{temperature, maxOutputTokens, topP, stopSequences}}`. Response
`{candidates:[{content, finishReason, index}], usageMetadata, modelVersion}`.

---

## 3. Models (catalog / discovery)

### GET `/v1/models` and GET `/models` — `public` (auth optional)

OpenAI-compatible list: `{object:'list', data: Model[]}`. With a Bearer token the list is
tier-gated to the caller. Query `?channels=1` adds per-channel alias variants.

**`Model`** (large; key fields): `id`, `object:'model'`, `created`, `owned_by`,
`supports_chat`, `supports_images`, `moderated`, `moderated_categories[]`, `multiplier?`,
`tier:'free'|'paid'`, `min_tier?`, `max_tokens`, `status`, `pricepermilliontokens?`,
`output_pricepermilliontokens?`, `official_pricepermilliontokens?`, `price_tiers?[]`,
`priceperthousandimages?`, `latency_ms?`, `ttft_ms?`, `supports_streaming?`,
`supports_tools?`, `supports_vision?`, `supports_reasoning?`, `supports_documents?`,
`supports_web_search?`, `group?`, cache price fields, `supports_caching?`,
`supported_parameters?[]`, `default_parameters?{}`, `media_type?`, `image_caps?`,
`video_caps?`, `audio_caps?`/`speech_caps?`/`sfx_caps?`/`transcription_caps?`/`dubbing_caps?`,
media price fields (`price_per_million_chars_cents?`, `price_per_audio_minute_cents?`,
`price_per_audio_second_cents?`, `price_per_generation_cents?`, …), `catalog_id?`,
`context_length?`, `max_output_tokens?`, `input_modalities?[]`, `output_modalities?[]`,
`knowledge_cutoff?`, `released_unix?`, `customer_price_table?{}`. (60 s cache header.)

### GET `/api/models/{model}/detail` — `public`

24h analytics + per-channel breakdown (brand-neutral). Rejects `__variant` ids (400).
Returns `{model, window_hours, overall, channels:[{label, internal, alias?, status?, tests?,
performance?, methods:[{label, stability?, customer_selectable, sell_in_cmt?, sell_out_cmt?}],
sell_in_cmt?, sell_out_cmt?, requests, errors, success_pct, …}], tests, performance,
official_input_cents_per_1m?, official_output_cents_per_1m?, fidelity?, pricing_options?}`.

### GET `/api/models/{fake_name}/allowed-params` — `public`

Effective param bounds for UI validation: `{model, provider, strict, params:{temperature,
top_p, max_tokens, thinking, reasoning_effort}}`. 404 if unknown.

### GET `/v1/playground/model-classes` — `public`

`{cheapest:string[], smartest:string[], fastest:string[]}` (public model names).

---

## 4. Images

### POST `/v1/images/generations` — `api_key`/`oauth_bearer(images)`

**Request**: `{model, prompt, n?=1, size?, quality?, response_format?='url'|'b64_json',
aspect_ratio?, input_images?:[{url?|b64_json?}], sse?=false, ...extra}`. Extra fields are
forwarded to the provider. Supports `models` fallback + smart routing.

**Response**: `{created?, data:[{url?, b64_json?}]}`. With `sse:true`, streams `data:` JSON
events + `[DONE]`. Billed per image (`billing_unit='image'`, qty `n`), charged on success.

---

## 5. Audio

All under `/v1/audio/*`, `api_key`/`oauth_bearer`. TTS/music/SFX take JSON; transcription,
isolation, voice-changer, dubbing take **multipart/form-data**. Binary endpoints return raw
audio bytes (`audio/mpeg|pcm|ulaw`); errors return JSON.

| Method | Path | Body | Returns | Billing |
| --- | --- | --- | --- | --- |
| POST | `/v1/audio/speech` | JSON `{model, input, voice, response_format?, speed?, voice_settings?, language_code?, seed?, ...}` | audio bytes | per-char |
| POST | `/v1/audio/music` | JSON `{model, prompt, music_length_ms?, response_format?, composition_plan?}` | audio bytes | per-second of output |
| POST | `/v1/audio/sound-effects` | JSON `{model, prompt, duration_seconds?, prompt_influence?, response_format?}` | audio bytes | flat + per-second |
| POST | `/v1/audio/transcriptions` | multipart `{model, file, language?, prompt?, temperature?}` | JSON `{text, language, duration}` | per-minute |
| POST | `/v1/audio/audio-isolation` | multipart `{model, file, output?}` | audio bytes | per-minute |
| POST | `/v1/audio/voice-changer` | multipart `{model, file, voice, voice_settings?}` | audio bytes | per-minute |
| POST | `/v1/audio/dubbing` | multipart `{model, file, target_lang, source_lang?, num_speakers?, watermark?, name?, ...}` | JSON `{dubbing_id, status}` | per-minute (async) |
| GET | `/v1/audio/dubbing/{id}` | — | JSON `{dubbing_id, status, language_pairs, source_duration?, preview_url?}` | none |
| GET | `/v1/audio/dubbing/{id}/audio/{lang}` | — | audio bytes (when completed) | none |
| GET | `/v1/audio/voices` | — | JSON `{voices:[{voice_id, name, preview_url?, category?, language?, ...}]}` | none |

---

## 6. Video (async task model)

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| POST | `/v1/video/generations` | `{model, prompt, mode?='text'|'image'|'reference', duration_seconds?, aspect_ratio?, quality?, input_images?, ...extra}` | `{task_id, status:'queued', model, created, expires_at, cost_cents?}` |
| GET | `/v1/video/tasks/{id}` | — | `{task_id, status:'queued'|'processing'|'completed'|'failed'|'expired', progress?, result_url?, error?, cost_cents?, prompt?, mode?, ...}` |
| GET | `/v1/video/tasks/{id}/stream` | — | SSE: `{event:'state', data:Task}` / `{event:'done', data:'[DONE]'}` / `{event:'error'}` |
| GET | `/v1/video/tasks` | — | `{data:[Task]}` (≤100, newest first) |
| DELETE | `/v1/video/tasks/{id}` | — | `{deleted:true}` |

Credits deducted only when the worker picks up the task. Owner-checked (404 for non-owner).
The SDK should provide a `waitForCompletion` helper (poll or SSE).

---

## 7. Voices (cloning)

| Method | Path | Body | Returns |
| --- | --- | --- | --- |
| GET | `/v1/voices/consent-text` | *(public)* — | `{text, hash}` |
| POST | `/v1/voices/clone` | multipart `{name, description?, consent_hash, labels?, remove_background_noise?, files…}` | `{voice_id, name, status:'active', created_at}` |
| GET | `/v1/voices/library` | — | `{voices:[{provider_voice_id, name, description?, created_at, status, provider, last_error?}]}` |
| PATCH | `/v1/voices/clone/{voice_id}` | `{name?, description?}` | `{updated:true, voice_id}` |
| DELETE | `/v1/voices/clone/{voice_id}` | — | `{deleted:true, voice_id}` |

`consent_hash` must equal the current `/v1/voices/consent-text` hash or the clone is
rejected (`consent_stale`).

---

## 8. Account (self-service)

Mostly `session_cookie` (session JWT). A few are `api_key` (marked).

| Method | Path | Auth | Body → Response |
| --- | --- | --- | --- |
| GET | `/api/me` | session | — → `UserResponse` (see below) |
| GET | `/api/usage` | session | — → `UserResponse` |
| GET | `/api/my-usage` | session | — → `{total_usage, by_model[], by_provider[], usage_log[]}` |
| PUT | `/api/user/update` | session | `{username?, email?, password?}` → `{success, message}` |
| POST | `/api/auth/request-password-reset` | none | `{email, locale?}` → `{success, message}` |
| POST | `/api/auth/reset-password` | none | `{token, new_password}` → `{success, message}` |
| GET | `/api/referral/code` | session | — → `{referral_code}` |
| GET | `/api/referral/referred-users` | session | — → `{referred_users[], referral_count}` |
| GET/PUT | `/api/user/price-caps` | session | `{caps:{model:{max_input_cents_per_m?, max_output_cents_per_m?, ...}}}` |
| DELETE | `/api/user/price-caps/{model}` | session | → `{success}` |
| GET/PUT | `/api/user/model-aliases` | session | GET → `{alias:model}`; PUT `{alias, model}` |
| PUT | `/api/user/model-aliases/batch` | session | `[{alias, model}]` → `{success, count}` |
| DELETE | `/api/user/model-aliases/{alias}` | session | → `{success, removed}` |
| GET/PUT | `/api/user/model-defaults` and `/{model}` | session | `UserModelDefault {temperature?, top_p?, max_tokens?, thinking?, thinking_budget?, reasoning_effort?, stop?}` |
| DELETE | `/api/user/model-defaults/{model}` | session | → `{success, removed}` |
| GET/PUT | `/api/user/smart-routing` | **api_key** | `{groups:{id:{priority_order:string[]}}}` (max 10 groups × 30) |
| GET | `/api/user/smart-routing/test?model=` | api_key | → `{requested, resolved_to?}` |
| GET/PUT | `/api/user/channel-prefs` | api_key | `{model: channel_alias}` (single-pin) |
| PUT | `/api/user/routing-category-prefs` | api_key | `{model: category_id}` |
| PUT | `/api/user/channel-order-prefs` | api_key | `{model:{order:string[], auto_fallback?}}` |
| GET/PUT | `/api/user/custom-categories` | api_key | `RoutingCategory[]` (max 20) |
| GET | `/api/user/routing-categories?model=` | api_key | → `{categories:[…]}` |
| POST/PUT/DELETE | `/api/models` and `/{fake_name}` | session | custom user provider model CRUD (`{fake_name, endpoint, api_key?, …}`, SSRF-validated) |
| GET | `/api/me/sessions` | session | → `{count, current_jti, entries:[{jti, created_at, ip, user_agent, last_seen?}]}` |
| DELETE | `/api/me/sessions/{jti}` and `/api/me/sessions` | session | revoke one / all-others |
| GET | `/api/me/login-history?limit=` | session | → `{count, entries:[{timestamp, ip, user_agent, method}]}` |

**`UserResponse`** (from `/api/me`, `/api/usage`): `{id, username, is_admin, api_key, plan,
subscription_id?, subscription_source, requests_today, tokens_today, total_tokens,
images_generated_today, total_images_generated, balance (cents), pay_as_you_go, email?,
has_password, plan_usage_credits, plan_usage_used, main_quota_remaining_cents,
main_quota_daily_used_cents, main_quota_weekly_used_cents, main_quota_last_daily_reset?,
main_quota_last_weekly_reset?, backup_quota_remaining_cents, backup_pool_enabled,
current_plan_caps?, plan_expiry?, created_at, last_login?, totp_enabled, must_enroll_2fa,
admin_roles[], permissions[], primary_allowed_ips[], is_warm, google_email?, github_email?,
github_username?, discord_username?, discord_phone_verified, has_ever_paid, models[],
model_aliases{}, model_defaults{}}`.

---

## 9. API keys

Two equivalent surfaces: `/v1/keys` (primary-key-authenticated, OpenAI-style) and
`/api/user/keys` (session). The SDK exposes a `keys` resource using `/v1/keys`.

| Method | Path | Auth | Body → Response |
| --- | --- | --- | --- |
| POST | `/v1/keys` | api_key (primary) | `{label?, rpm_limit?, credit_allowance?, tier?:'default'|'premium'|'paygo', allowed_models?[], allowed_ips?[], limit_reset?:'daily'|'weekly'|'monthly'|'none'}` → `ApiKey` w/ **full key (once)** |
| GET | `/v1/keys` | api_key (primary) | → `{keys:[ApiKey masked], total}` |
| PATCH | `/v1/keys/{key}` | api_key (primary) | `{...fields, disabled?}` → `ApiKey (masked)` |
| DELETE | `/v1/keys/{key}` | api_key (primary) | → `{deleted:true}` |
| GET/POST/PUT/DELETE | `/api/user/keys[/{key}]` | session | same model, session-authed |
| POST | `/api/user/reset-api-key` | session | → `{success, api_key}` (rotate primary) |
| PUT | `/api/user/primary-allowed-ips` | session | `{allowed_ips:[]}` |
| PUT | `/api/user/backup-pool-enabled` | api_key | `{enabled}` → `{backup_pool_enabled}` |
| POST | `/api/pay-as-you-go/toggle` | session | — → `{pay_as_you_go}` (toggle) |

**`ApiKey`**: `{key, label?, created_at?, disabled?, tier, rpm_limit?, credit_allowance?,
credits_used?, limit_reset?, allowed_models[], allowed_ips[]}`. Max 100 secondary keys.
Full key material shown only on create; otherwise masked `sk-air-…last4`. Secondary keys
cannot manage other keys. Responses are `Cache-Control: no-store`.

---

## 10. 2FA

All `session_cookie`. `{secret, otpauth_url}` on init; verify returns backup codes.

| Method | Path | Body → Response |
| --- | --- | --- |
| POST | `/api/2fa/setup-init` | — → `{secret, otpauth_url}` |
| POST | `/api/2fa/setup-verify` | `{code}` → `{backup_codes[]}` |
| POST | `/api/2fa/disable` | `{password, code}` → `{success}` |
| POST | `/api/2fa/regenerate-backup-codes` | `{code}` → `{backup_codes[]}` |
| POST | `/api/2fa/verify-step-up` | `{code}` → `{ok, step_up_token}` |
| GET | `/api/2fa/step-up-status` | — → `{verified, expires_at?}` |

---

## 11. OAuth — as a provider (third-party integrators)

Scopes: `profile`, `chat`, `images`, `keys:read`, `keys:write` (sensitive). `response_type=code`
only. PKCE `S256` (mandatory for public clients). Tokens `airf_oat_…`, TTL 1h–90d.

| Method | Path | Auth | Notes |
| --- | --- | --- | --- |
| GET | `/oauth/authorize` | session | consent details (JSON with `Accept: application/json`) or redirect to SPA |
| POST | `/oauth/authorize` | session | `{client_id, redirect_uri, scope?, state?, code_challenge?, code_challenge_method?, decision:'approve'|'deny'}` → `{redirect_to}` |
| POST | `/oauth/token` | client (Basic or body) | `grant_type=authorization_code`, `code`, `redirect_uri`, `client_id?`, `client_secret?`, `code_verifier?` → `{access_token, token_type:'Bearer', expires_in, scope}` |
| GET | `/oauth/userinfo` | `Bearer airf_oat_` (profile) | → `{id, username, plan, is_admin, email?, …linked provider ids}` |
| POST | `/oauth/revoke` | none | `token=<airf_oat_>` → 200 (always) |

### OAuth apps (self-service management) — `session_cookie`

| Method | Path | Body → Response |
| --- | --- | --- |
| GET | `/api/me/oauth-apps` | → `{apps:[OAuthClient], limit, count}` |
| POST | `/api/me/oauth-apps` | `{name, description?, homepage_url?, logo_url?, redirect_uris[], allowed_scopes[], contact_email?, access_token_ttl_secs?}` → `{app, client_secret (once)}` |
| GET/PATCH/DELETE | `/api/me/oauth-apps/{client_id}` | get / update (sensitive edits re-pending) / delete |
| POST | `/api/me/oauth-apps/{client_id}/rotate-secret` | → `{ok, client_secret}` |
| GET | `/api/me/connected-apps` | → `{connected_apps:[{client_id, client_name, scopes[], first_granted_at, last_used_at?}]}` |
| DELETE | `/api/me/connected-apps/{client_id}` | → `{ok, tokens_revoked}` |

**`OAuthClient`**: `{client_id, name, description?, homepage_url?, logo_url?, redirect_uris[],
allowed_scopes[], approval_status:'approved'|'pending'|'rejected', enabled, owner_user_id?,
created_at, access_token_ttl_secs?}`.

---

## 12. Auth (login / signup / verify)

| Method | Path | Auth | Body → Response |
| --- | --- | --- | --- |
| POST | `/auth/signup` | none | `{username, password, email, captcha_token, referral_code?, locale?, utm_*?}` → `{ok}` + cookie, or `{verification_sent, email_masked, expires_in_hours}` |
| POST | `/auth/signup/precheck` | none | `{username?, email?}` → `{strict}` |
| POST | `/auth/login` | none | `{username, password, captcha_token}` → `{ok}` + cookie, or `{requires_2fa, challenge_token}`, or `{ok, must_enroll_2fa}` |
| POST | `/auth/2fa/verify` | `Bearer <challenge_token>` | `{code, backup_code?}` → `{ok}` + cookie |
| POST | `/auth/verify` | none | `{token}` → `{verified, username}` |
| POST | `/auth/resend-verification` | none | `{identifier}` → `{ok}` |
| POST | `/auth/logout` | session | — → `{ok}` + clears cookie |

The session JWT is delivered via `Set-Cookie: airforce_session=<jwt>`. SDKs that support
account/billing methods read the cookie or accept a JWT directly.

---

## 13. Billing & plans

Plans: `starter`, `premium`, `plus`, `pro`, `master`, `elite`, `ultra`, plus `credits`
(top-up). Amounts in USD for checkout, cents elsewhere.

| Method | Path | Auth | Body → Response |
| --- | --- | --- | --- |
| POST | `/api/creem/create-checkout` | session | `{plan, is_onetime?, quantity?, price_amount?}` → `{id, checkout_url, …}` (409 if already subscribed) |
| POST | `/api/create-nowpayments-invoice` | session | `{plan, price_amount?}` → `{id, status, price_amount, …}` |
| POST | `/api/create-portal-session` | session | `{}` → `{url}` (Creem customer portal) |
| GET | `/v1/analytics` | public | → `{total_requests, total_tokens, total_images, uptime_percent, total_users, active_today}` |

`price_amount` applies to the `credits` plan (Creem $1–$1000, NowPayments $10–$1000).
Webhooks (`/api/creem-webhook`, `/api/nowpayments-webhook`) are server-to-server and **not**
part of the SDK.

---

## Out of scope (not in SDKs)

- `/admin/*` — internal control plane (users, pricing, catalog, moderation, fidelity,
  intercept, OAuth-client administration, provider keys, server config, analytics).
- Payment webhooks (`/api/creem-webhook`, `/api/nowpayments-webhook`).
- Internal/ops routes (env-secret gated).
