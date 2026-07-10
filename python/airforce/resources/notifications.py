"""Notification preferences, the in-app feed, and delivery-channel linking."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._base import AsyncAPIResource, SyncAPIResource, clean, enc

_SESSION = "session"


class Notifications(SyncAPIResource):
    def get_prefs(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/me/notification-prefs", auth=_SESSION, **kw)

    def update_prefs(self, prefs: Dict[str, Any], **kw: Any) -> Any:
        """Partially update notification preferences. The dict is sent verbatim:
        absent fields stay unchanged and ``{"quiet_hours": None}`` clears quiet
        hours. Unknown channel ids in ``routing`` are dropped server-side."""
        return self._transport.request("PATCH", "/api/me/notification-prefs", auth=_SESSION, json=prefs, **kw)

    def list(self, *, limit: Optional[int] = None, before: Optional[str] = None, **kw: Any) -> Any:
        """In-app feed, newest first → ``{items: [FeedItem], unread}``. ``limit`` is
        1-100 (default 30); ``before`` is a ``created_at`` cursor for paging."""
        return self._transport.request("GET", "/api/me/notifications", auth=_SESSION,
                                       params=clean(limit=limit, before=before), **kw)

    def mark_read(self, ids: Optional[List[str]] = None, *, mark_all: Optional[bool] = None, **kw: Any) -> Any:
        """Mark feed items read — by ``ids`` or all of them (``mark_all=True``)."""
        return self._transport.request("POST", "/api/me/notifications/read", auth=_SESSION,
                                       json=clean(ids=ids, all=mark_all), **kw)

    def channels(self, **kw: Any) -> Any:
        """Linked delivery-channel identities + linkable channel ids →
        ``{identities: [ChannelIdentity], available_channels}``."""
        return self._transport.request("GET", "/api/me/channels", auth=_SESSION, **kw)

    def link_channel(self, *, channel: str, address: str = "", display: Optional[str] = None, **kw: Any) -> Any:
        """Start linking a channel; the verification code is delivered through the
        channel itself (30-minute expiry). Bot channels accept an empty ``address``
        and return a one-time link code / deep link instead."""
        return self._transport.request("POST", "/api/me/channels", auth=_SESSION,
                                       json=clean(channel=channel, address=address, display=display), **kw)

    def verify_channel(self, *, channel: str, code: str, **kw: Any) -> Any:
        """Complete channel verification with the delivered code (400 on an invalid
        or expired code)."""
        return self._transport.request("POST", "/api/me/channels/verify", auth=_SESSION,
                                       json={"channel": channel, "code": code}, **kw)

    def unlink_channel(self, channel: str, **kw: Any) -> Any:
        return self._transport.request("DELETE", f"/api/me/channels/{enc(channel)}", auth=_SESSION, **kw)


class AsyncNotifications(AsyncAPIResource):
    async def get_prefs(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/me/notification-prefs", auth=_SESSION, **kw)

    async def update_prefs(self, prefs: Dict[str, Any], **kw: Any) -> Any:
        return await self._transport.request("PATCH", "/api/me/notification-prefs", auth=_SESSION, json=prefs, **kw)

    async def list(self, *, limit: Optional[int] = None, before: Optional[str] = None, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/me/notifications", auth=_SESSION,
                                             params=clean(limit=limit, before=before), **kw)

    async def mark_read(self, ids: Optional[List[str]] = None, *, mark_all: Optional[bool] = None, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/me/notifications/read", auth=_SESSION,
                                             json=clean(ids=ids, all=mark_all), **kw)

    async def channels(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/me/channels", auth=_SESSION, **kw)

    async def link_channel(self, *, channel: str, address: str = "", display: Optional[str] = None, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/me/channels", auth=_SESSION,
                                             json=clean(channel=channel, address=address, display=display), **kw)

    async def verify_channel(self, *, channel: str, code: str, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/me/channels/verify", auth=_SESSION,
                                             json={"channel": channel, "code": code}, **kw)

    async def unlink_channel(self, channel: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/api/me/channels/{enc(channel)}", auth=_SESSION, **kw)
