# airforce-api

Official Python SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. Sync **and** async, built on
[httpx](https://www.python-httpx.org/).

## Install

The package is not published to PyPI yet — install it straight from GitHub:

```bash
pip install "git+https://github.com/ApiAirforce/api-airforce-sdk.git#subdirectory=python"
```

Or from a local checkout:

```bash
pip install ./python
```

## Quick start

```python
from airforce import Airforce

client = Airforce(api_key="sk-air-...")  # or AIRFORCE_API_KEY env var

res = client.chat.create(
    model="claude-opus-4.8",
    messages=[{"role": "user", "content": "Write a haiku about airplanes."}],
)
print(res["choices"][0]["message"]["content"])
print("cost (credits):", res["usage"].get("cost"))
```

## Async

```python
import asyncio
from airforce import AsyncAirforce

async def main():
    async with AsyncAirforce(api_key="sk-air-...") as client:
        res = await client.chat.create(
            model="claude-opus-4.8",
            messages=[{"role": "user", "content": "hi"}],
        )
        print(res["choices"][0]["message"]["content"])

asyncio.run(main())
```

## Streaming

```python
stream = client.chat.create(
    model="claude-opus-4.8",
    messages=[{"role": "user", "content": "Count to five."}],
    stream=True,
)
for chunk in stream:
    delta = chunk["choices"][0]["delta"].get("content", "")
    print(delta, end="", flush=True)
```

Async streaming uses `async for chunk in await client.chat.create(..., stream=True)`.

## Reasoning output

For reasoning models, the optional `reasoning` parameter shapes where the reasoning
text lands in the *response*. It is consumed server-side and never forwarded upstream:

```python
res = client.chat.create(
    model="deepseek-r1",
    messages=[{"role": "user", "content": "hi"}],
    reasoning={"format": "separate"},  # or {"exclude": True} to drop it entirely
)
print(res["choices"][0]["message"].get("reasoning"))  # reasoning, stripped from content
```

Without `reasoning` (or with `{"format": "inline"}`) the reasoning stays inline in
`content`, wrapped in `<think>...</think>`. In streaming mode `"separate"` delivers it
via `delta["reasoning"]`.

## Embeddings

```python
res = client.embeddings.create(model="embed-1", input=["hello", "world"])
vectors = [d["embedding"] for d in res["data"]]
```

`input` accepts a string, a list of strings, or (arrays of) token ids. Billed on input
tokens only.

## Fallback models

```python
client.chat.create(
    model="claude-opus-4.8",
    models=["claude-opus-4.8", "gpt-5.4", "gemini-2.5-pro"],  # first healthy one wins
    messages=[{"role": "user", "content": "hi"}],
)
```

## Media

```python
# Image
img = client.images.generate(model="image-1", prompt="a red biplane")

# Text-to-speech → bytes
audio = client.audio.speech(model="eleven-v3", voice="21m00Tcm4TlvDq8ikWAM",
                            input="Cleared for takeoff.")
open("out.mp3", "wb").write(audio)

# Transcription (multipart)
with open("clip.mp3", "rb") as f:
    text = client.audio.transcriptions(model="scribe-v1", file=f.read(), filename="clip.mp3")

# Video (async task — poll until done)
video = client.video.generate_and_wait(model="veo-3", prompt="a paper plane over a city")
print(video["result_url"])

# 3D generation (async task — poll, then download the artifact)
task = client.three_d.generate_and_wait(
    model="shape-1",
    image_urls=["https://example.com/toy.png"],  # image-to-3D models need >= 1
    resolution="high",
)
blob = client.three_d.content(task["task_id"])   # glb/ply bytes (24h TTL)
open(f"model.{task.get('format', 'glb')}", "wb").write(blob)
```

## Account, keys & billing

Account/billing/2FA endpoints use a **session token** (JWT). Logging in adopts it
automatically (the cookie jar is reused), so subsequent calls just work:

```python
client.auth.login(username="me", password="...", captcha_token="...")
me = client.account.me()
print("balance (cents):", me["balance"])

key = client.keys.create(label="ci", rpm_limit=60)
```

You can also pass an existing token: `Airforce(api_key=..., session_token=jwt)` or
`client.set_session_token(jwt)`.

Routing preferences (API-key authenticated) let you steer smart routing per model:

```python
client.account.set_channel_order_prefs({"gpt-5.4": {"order": ["fast", "cheap"], "auto_fallback": True}})
client.account.set_routing_category_prefs({"gpt-5.4": "my-category"})
client.account.set_custom_categories([{"id": "my-category", "name": "My category"}])

# Bring-your-own provider model (session authenticated)
client.account.create_custom_model(fake_name="my-model", endpoint="https://api.example.com/v1", api_key="...")
```

### Account closure

```python
client.account.delete_account(password="...", forfeit_balance_ack=True)  # soft-close
# ...within the 14-day grace window:
client.account.reactivate(email="old@example.com", password="...")
```

## Notifications

Session-authenticated: preferences, the in-app feed, and delivery-channel linking.

```python
prefs = client.notifications.get_prefs()
client.notifications.update_prefs({"digest_frequency": "daily", "quiet_hours": None})  # None clears

feed = client.notifications.list(limit=50)
client.notifications.mark_read([item["id"] for item in feed["items"]])  # or mark_all=True

client.notifications.link_channel(channel="email", address="me@example.com")
client.notifications.verify_channel(channel="email", code="123456")
```

## Organizations

Session-authenticated team management (`client.org`): the org itself, members,
invites, org-scoped API keys, and usage.

```python
org = client.org.get()                      # {"org": {...}, "role": "owner"}
members = client.org.members()

invite = client.org.create_invite(email="dev@example.com", role="member")
print(invite["invite_url"])

key = client.org.create_key(member_user_id="u123", label="ci", credit_allowance=500)
print(key["item"]["key"])                   # full key is shown only once

usage = client.org.usage(from_=1750000000)  # unix seconds; cost values are cents
```

## OAuth (third-party integrators)

```python
from airforce import create_pkce_pair

pkce = create_pkce_pair()
url = client.oauth.authorize_url(
    client_id="airforce_...",
    redirect_uri="https://app.example.com/callback",
    scope=["profile", "chat"],
    code_challenge=pkce["challenge"],
)
# ...after the redirect:
token = client.oauth.exchange_token(
    code=code,
    redirect_uri="https://app.example.com/callback",
    client_id="airforce_...",
    code_verifier=pkce["verifier"],
)
```

## Errors

Failures raise an `AirforceError` subclass: `AuthenticationError` (401),
`InsufficientBalanceError` (402), `PermissionDeniedError` (403), `NotFoundError` (404),
`ConflictError` (409), `RateLimitError` (429), `InternalServerError` (5xx),
`AirforceConnectionError`, `AirforceTimeoutError`.

```python
from airforce import RateLimitError

try:
    client.chat.create(model="m", messages=[{"role": "user", "content": "hi"}])
except RateLimitError as err:
    print("retry after", err.retry_after)
```

## Configuration

```python
Airforce(
    api_key="sk-air-...",
    session_token="...",       # for account/billing endpoints
    base_url="https://api.airforce",
    timeout=60.0,
    max_retries=2,             # retried on 429 / 5xx / network errors
    default_headers={},
    http_client=None,          # inject a custom httpx.Client
)
```

## License

MIT
