"""HTTP transport: auth/header assembly, retries, and sync/async senders."""

from __future__ import annotations

import asyncio
import random
import time
from typing import Any, Mapping, Optional

import httpx

from ._exceptions import (
    AirforceConnectionError,
    AirforceError,
    AirforceTimeoutError,
    MissingCredentialError,
)
from ._streaming import AsyncStream, Stream
from ._version import __version__

DEFAULT_BASE_URL = "https://api.airforce"
# 409 is excluded: a terminal business conflict (e.g. "already subscribed"), not transient.
_RETRYABLE = {408, 429, 500, 502, 503, 504}


class _BaseTransport:
    def __init__(
        self,
        *,
        api_key: Optional[str],
        session_token: Optional[str],
        base_url: str,
        timeout: float,
        max_retries: int,
        default_headers: Mapping[str, str],
    ) -> None:
        self.api_key = api_key
        self.session_token = session_token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.default_headers = dict(default_headers)

    # --- shared helpers ------------------------------------------------------

    def _resolve_token(self, auth: str) -> Optional[str]:
        if auth == "none":
            return None
        if auth == "session":
            # Session endpoints require a session JWT — never substitute an API key.
            return self.session_token
        return self.api_key or self.session_token

    def _headers(self, auth: str, extra: Optional[Mapping[str, str]]) -> dict:
        headers = {
            "user-agent": f"airforce-sdk-python/{__version__}",
            "x-airforce-sdk": f"python/{__version__}",
            **self.default_headers,
        }
        if auth != "none":
            token = self._resolve_token(auth)
            if not token:
                raise MissingCredentialError(
                    "This endpoint requires a session token (set session_token / auth.login())."
                    if auth == "session"
                    else "This endpoint requires an API key (set api_key)."
                )
            headers["authorization"] = f"Bearer {token}"
        if extra:
            headers.update(extra)
        return headers

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _delay(self, attempt: int, retry_after: Optional[float]) -> float:
        base = retry_after if retry_after is not None else min(2 ** (attempt - 1), 8)
        return base + base * 0.25 * random.random()

    def _retry_after(self, response: httpx.Response) -> Optional[float]:
        value = response.headers.get("retry-after")
        try:
            return float(value) if value is not None else None
        except ValueError:
            return None

    def _raise_for_response(self, status: int, body: Any, request_id: Optional[str]):
        raise AirforceError.from_response(status, body, request_id)

    def _raise_transport(self, exc: httpx.TransportError, path: str, url: str):
        if isinstance(exc, httpx.TimeoutException):
            raise AirforceTimeoutError(f"Request to {path} timed out") from exc
        raise AirforceConnectionError(f"Failed to reach {url}: {exc}") from exc


class SyncTransport(_BaseTransport):
    def __init__(self, *, client: Optional[httpx.Client] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client = client or httpx.Client()

    def request(self, method: str, path: str, **kw: Any) -> Any:
        response = self._send(method, path, stream=False, **kw)
        return _decode(response)

    def request_binary(self, method: str, path: str, **kw: Any) -> bytes:
        return self._send(method, path, stream=False, **kw).content

    def stream(self, method: str, path: str, **kw: Any) -> Stream:
        return Stream(self._send(method, path, stream=True, **kw))

    def get_session_cookie(self) -> Optional[str]:
        return self._client.cookies.get("airforce_session")

    def close(self) -> None:
        self._client.close()

    def _open(self, method: str, url: str, stream: bool, **req: Any) -> httpx.Response:
        if stream:
            return self._client.send(self._client.build_request(method, url, **req), stream=True)
        return self._client.request(method, url, **req)

    def _send(
        self,
        method: str,
        path: str,
        *,
        stream: bool,
        auth: str = "api_key",
        params: Any = None,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> httpx.Response:
        url = self._url(path)
        req = {
            "params": params, "json": json, "data": data, "files": files,
            "headers": self._headers(auth, headers),
            "timeout": self.timeout if timeout is None else timeout,
        }
        retries = self.max_retries if max_retries is None else max_retries
        attempt = 0
        while True:
            try:
                response = self._open(method, url, stream, **req)
            except httpx.TransportError as exc:
                # A transport error leaves a POST's outcome unknown — retrying could
                # double-charge a billable request. Only retry idempotent methods.
                if attempt >= retries or method.upper() == "POST":
                    self._raise_transport(exc, path, url)
                attempt += 1
                time.sleep(self._delay(attempt, None))
                continue

            if response.is_success:
                return response
            if response.status_code in _RETRYABLE and attempt < retries:
                retry_after = self._retry_after(response)
                response.close()
                attempt += 1
                time.sleep(self._delay(attempt, retry_after))
                continue
            if stream:
                response.read()
            self._raise_for_response(
                response.status_code, _safe_json(response), response.headers.get("x-request-id"),
            )


class AsyncTransport(_BaseTransport):
    def __init__(self, *, client: Optional[httpx.AsyncClient] = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client = client or httpx.AsyncClient()

    async def request(self, method: str, path: str, **kw: Any) -> Any:
        response = await self._send(method, path, stream=False, **kw)
        return _decode(response)

    async def request_binary(self, method: str, path: str, **kw: Any) -> bytes:
        response = await self._send(method, path, stream=False, **kw)
        return response.content

    async def stream(self, method: str, path: str, **kw: Any) -> AsyncStream:
        return AsyncStream(await self._send(method, path, stream=True, **kw))

    def get_session_cookie(self) -> Optional[str]:
        return self._client.cookies.get("airforce_session")

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _open(self, method: str, url: str, stream: bool, **req: Any) -> httpx.Response:
        if stream:
            return await self._client.send(self._client.build_request(method, url, **req), stream=True)
        return await self._client.request(method, url, **req)

    async def _send(
        self,
        method: str,
        path: str,
        *,
        stream: bool,
        auth: str = "api_key",
        params: Any = None,
        json: Any = None,
        data: Any = None,
        files: Any = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> httpx.Response:
        url = self._url(path)
        req = {
            "params": params, "json": json, "data": data, "files": files,
            "headers": self._headers(auth, headers),
            "timeout": self.timeout if timeout is None else timeout,
        }
        retries = self.max_retries if max_retries is None else max_retries
        attempt = 0
        while True:
            try:
                response = await self._open(method, url, stream, **req)
            except httpx.TransportError as exc:
                # A transport error leaves a POST's outcome unknown — retrying could
                # double-charge a billable request. Only retry idempotent methods.
                if attempt >= retries or method.upper() == "POST":
                    self._raise_transport(exc, path, url)
                attempt += 1
                await asyncio.sleep(self._delay(attempt, None))
                continue

            if response.is_success:
                return response
            if response.status_code in _RETRYABLE and attempt < retries:
                retry_after = self._retry_after(response)
                await response.aclose()
                attempt += 1
                await asyncio.sleep(self._delay(attempt, retry_after))
                continue
            if stream:
                await response.aread()
            self._raise_for_response(
                response.status_code, _safe_json(response), response.headers.get("x-request-id"),
            )


def _decode(response: httpx.Response) -> Any:
    if response.status_code == 204 or not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return response.text


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text
