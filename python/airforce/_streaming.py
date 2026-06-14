"""Server-Sent Events parsing and sync/async stream wrappers."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Iterator, List, Optional

import httpx

_DONE = "[DONE]"


class _SSEDecoder:
    """Incremental SSE line decoder. Feed it text; get back data payloads."""

    def __init__(self) -> None:
        self._buffer = ""
        self._data: List[str] = []

    def feed(self, chunk: str) -> List[str]:
        self._buffer += chunk.replace("\r\n", "\n").replace("\r", "\n")
        out: List[str] = []
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            event = self._feed_line(line)
            if event is not None:
                out.append(event)
        return out

    def flush(self) -> Optional[str]:
        return self._emit() if self._data else None

    def _feed_line(self, line: str) -> Optional[str]:
        if line == "":
            return self._emit() if self._data else None
        if line.startswith(":"):
            return None
        field, _, value = line.partition(":")
        if value.startswith(" "):
            value = value[1:]
        if field == "data":
            self._data.append(value)
        return None

    def _emit(self) -> str:
        data = "\n".join(self._data)
        self._data = []
        return data


def _parse(data: str) -> Optional[Any]:
    """Parse one SSE data payload; return None for the terminal sentinel."""
    if data == _DONE or data == "":
        return None
    return json.loads(data)


class Stream:
    """A synchronous, iterable stream of parsed SSE events."""

    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self._decoder = _SSEDecoder()

    def __iter__(self) -> Iterator[Any]:
        try:
            for chunk in self._response.iter_text():
                for data in self._decoder.feed(chunk):
                    if data == _DONE:
                        return
                    parsed = _parse(data)
                    if parsed is not None:
                        yield parsed
        finally:
            self.close()

    def close(self) -> None:
        self._response.close()

    def __enter__(self) -> "Stream":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class AsyncStream:
    """An asynchronous, async-iterable stream of parsed SSE events."""

    def __init__(self, response: httpx.Response) -> None:
        self._response = response
        self._decoder = _SSEDecoder()

    async def __aiter__(self) -> AsyncIterator[Any]:
        try:
            async for chunk in self._response.aiter_text():
                for data in self._decoder.feed(chunk):
                    if data == _DONE:
                        return
                    parsed = _parse(data)
                    if parsed is not None:
                        yield parsed
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        await self._response.aclose()

    async def __aenter__(self) -> "AsyncStream":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()
