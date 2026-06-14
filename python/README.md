# airforce-api

Official Python SDK for the [api.airforce](https://api.airforce) AI gateway — one
OpenAI-compatible API in front of many model providers. Sync **and** async, built on
[httpx](https://www.python-httpx.org/).

## Install

```bash
pip install airforce-api
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
