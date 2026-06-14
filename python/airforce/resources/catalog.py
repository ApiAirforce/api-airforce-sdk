"""Model catalog / discovery resources."""

from __future__ import annotations

from typing import Any, List

from ._base import AsyncAPIResource, SyncAPIResource


class Models(SyncAPIResource):
    def list(self, *, channels: bool = False, **kw: Any) -> List[Any]:
        params = {"channels": 1} if channels else None
        res = self._transport.request("GET", "/v1/models", auth="none", params=params, **kw)
        return res.get("data", []) if isinstance(res, dict) else res

    def detail(self, model: str, **kw: Any) -> Any:
        return self._transport.request("GET", f"/api/models/{model}/detail", auth="none", **kw)

    def allowed_params(self, model: str, **kw: Any) -> Any:
        return self._transport.request("GET", f"/api/models/{model}/allowed-params", auth="none", **kw)

    def classes(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/v1/playground/model-classes", auth="none", **kw)


class AsyncModels(AsyncAPIResource):
    async def list(self, *, channels: bool = False, **kw: Any) -> List[Any]:
        params = {"channels": 1} if channels else None
        res = await self._transport.request("GET", "/v1/models", auth="none", params=params, **kw)
        return res.get("data", []) if isinstance(res, dict) else res

    async def detail(self, model: str, **kw: Any) -> Any:
        return await self._transport.request("GET", f"/api/models/{model}/detail", auth="none", **kw)

    async def allowed_params(self, model: str, **kw: Any) -> Any:
        return await self._transport.request("GET", f"/api/models/{model}/allowed-params", auth="none", **kw)

    async def classes(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/v1/playground/model-classes", auth="none", **kw)
