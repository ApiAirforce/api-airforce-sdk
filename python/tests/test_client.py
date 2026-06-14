from __future__ import annotations

import httpx
import pytest

from airforce import Airforce, AsyncAirforce, MissingCredentialError

COMPLETION = {
    "id": "cmpl_1",
    "object": "chat.completion",
    "created": 0,
    "model": "claude-opus-4.8",
    "choices": [
        {"index": 0, "message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}
    ],
}


def client_with(handler) -> Airforce:
    return Airforce(api_key="sk-air-test", http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_sends_bearer_and_parses_response():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        seen["url"] = str(request.url)
        return httpx.Response(200, json=COMPLETION)

    client = client_with(handler)
    res = client.chat.create(model="claude-opus-4.8", messages=[{"role": "user", "content": "hello"}])
    assert res["choices"][0]["message"]["content"] == "hi"
    assert seen["auth"] == "Bearer sk-air-test"
    assert seen["url"] == "https://api.airforce/v1/chat/completions"


def test_missing_api_key_raises():
    client = Airforce(http_client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))))
    with pytest.raises(MissingCredentialError):
        client.chat.create(model="m", messages=[{"role": "user", "content": "x"}])


def test_public_endpoint_has_no_auth():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"object": "list", "data": []})

    client = Airforce(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    client.models.list()
    assert seen["auth"] is None


def test_retries_on_429_then_succeeds():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, headers={"retry-after": "0"}, json={"error": "slow"})
        return httpx.Response(200, json=COMPLETION)

    client = client_with(handler)
    res = client.chat.create(model="m", messages=[{"role": "user", "content": "x"}])
    assert res["id"] == "cmpl_1"
    assert calls["n"] == 2


def test_streaming_chat():
    sse = (
        b'data: {"choices":[{"index":0,"delta":{"content":"he"},"finish_reason":null}]}\n\n'
        b'data: {"choices":[{"index":0,"delta":{"content":"llo"},"finish_reason":"stop"}]}\n\n'
        b"data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=sse)

    client = client_with(handler)
    stream = client.chat.create(model="m", messages=[{"role": "user", "content": "x"}], stream=True)
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in stream)
    assert text == "hello"


def test_session_endpoint_requires_session_token():
    # account.me is a session endpoint; an API key must NOT be substituted.
    client = Airforce(api_key="sk-air-test", http_client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))))
    from airforce import MissingCredentialError
    with pytest.raises(MissingCredentialError):
        client.account.me()


async def test_async_chat():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=COMPLETION)

    client = AsyncAirforce(api_key="sk-air-test", http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    res = await client.chat.create(model="m", messages=[{"role": "user", "content": "x"}])
    assert res["choices"][0]["message"]["content"] == "hi"
    await client.aclose()
