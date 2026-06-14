"""Resource base classes and helpers."""

from __future__ import annotations

from typing import Any, Dict
from urllib.parse import quote


def clean(**kwargs: Any) -> Dict[str, Any]:
    """Drop keys whose value is ``None`` (so optional params are omitted)."""
    return {k: v for k, v in kwargs.items() if v is not None}


def enc(segment: str) -> str:
    """Percent-encode a dynamic path segment (e.g. a user-chosen alias)."""
    return quote(str(segment), safe="")


class SyncAPIResource:
    def __init__(self, transport: Any) -> None:
        self._transport = transport


class AsyncAPIResource:
    def __init__(self, transport: Any) -> None:
        self._transport = transport
