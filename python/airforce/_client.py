"""The synchronous and asynchronous Airforce clients."""

from __future__ import annotations

import os
from typing import Mapping, Optional

import httpx

from . import resources as r
from ._transport import DEFAULT_BASE_URL, AsyncTransport, SyncTransport


def _resolve(value: Optional[str], env: str) -> Optional[str]:
    return value if value is not None else os.environ.get(env)


class Airforce:
    """Synchronous client for the api.airforce gateway.

    >>> client = Airforce(api_key="sk-air-...")
    >>> res = client.chat.create(model="claude-opus-4.8",
    ...                          messages=[{"role": "user", "content": "hi"}])
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        session_token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 2,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._transport = SyncTransport(
            client=http_client,
            api_key=_resolve(api_key, "AIRFORCE_API_KEY"),
            session_token=_resolve(session_token, "AIRFORCE_SESSION_TOKEN"),
            base_url=_resolve(base_url, "AIRFORCE_BASE_URL") or DEFAULT_BASE_URL,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers or {},
        )
        self.chat = r.Chat(self._transport)
        self.messages = r.Messages(self._transport)
        self.responses = r.Responses(self._transport)
        self.gemini = r.Gemini(self._transport)
        self.models = r.Models(self._transport)
        self.images = r.Images(self._transport)
        self.audio = r.Audio(self._transport)
        self.video = r.Video(self._transport)
        self.voices = r.Voices(self._transport)
        self.account = r.Account(self._transport)
        self.keys = r.Keys(self._transport)
        self.billing = r.Billing(self._transport)
        self.twofa = r.TwoFactor(self._transport)
        self.auth = r.Auth(self._transport)
        self.oauth = r.OAuth(self._transport)

    @property
    def base_url(self) -> str:
        return self._transport.base_url

    def set_session_token(self, token: Optional[str]) -> None:
        self._transport.session_token = token

    def close(self) -> None:
        self._transport.close()

    def __enter__(self) -> "Airforce":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class AsyncAirforce:
    """Asynchronous client for the api.airforce gateway.

    >>> client = AsyncAirforce(api_key="sk-air-...")
    >>> res = await client.chat.create(model="claude-opus-4.8",
    ...                                messages=[{"role": "user", "content": "hi"}])
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        session_token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 2,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._transport = AsyncTransport(
            client=http_client,
            api_key=_resolve(api_key, "AIRFORCE_API_KEY"),
            session_token=_resolve(session_token, "AIRFORCE_SESSION_TOKEN"),
            base_url=_resolve(base_url, "AIRFORCE_BASE_URL") or DEFAULT_BASE_URL,
            timeout=timeout,
            max_retries=max_retries,
            default_headers=default_headers or {},
        )
        self.chat = r.AsyncChat(self._transport)
        self.messages = r.AsyncMessages(self._transport)
        self.responses = r.AsyncResponses(self._transport)
        self.gemini = r.AsyncGemini(self._transport)
        self.models = r.AsyncModels(self._transport)
        self.images = r.AsyncImages(self._transport)
        self.audio = r.AsyncAudio(self._transport)
        self.video = r.AsyncVideo(self._transport)
        self.voices = r.AsyncVoices(self._transport)
        self.account = r.AsyncAccount(self._transport)
        self.keys = r.AsyncKeys(self._transport)
        self.billing = r.AsyncBilling(self._transport)
        self.twofa = r.AsyncTwoFactor(self._transport)
        self.auth = r.AsyncAuth(self._transport)
        self.oauth = r.AsyncOAuth(self._transport)

    @property
    def base_url(self) -> str:
        return self._transport.base_url

    def set_session_token(self, token: Optional[str]) -> None:
        self._transport.session_token = token

    async def aclose(self) -> None:
        await self._transport.aclose()

    async def __aenter__(self) -> "AsyncAirforce":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
