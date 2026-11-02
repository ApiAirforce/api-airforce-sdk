"""Model catalog / discovery resources."""

from __future__ import annotations

from typing import Any, List

from ._base import AsyncAPIResource, SyncAPIResource, enc


def _model_path(model: str) -> str:
    """``/v1/models/{model}`` with each ``/``-separated segment percent-encoded, so slashes
    stay path separators while ``?``, ``#``, ``%`` or spaces cannot change the request."""
    return "/v1/models/" + "/".join(enc(part) for part in model.split("/"))


class Models(SyncAPIResource):
    def list(self, *, channels: bool = False, **kw: Any) -> List[Any]:
        params = {"channels": 1} if channels else None
        res = self._transport.request("GET", "/v1/models", auth="none", params=params, **kw)
        return res.get("data", []) if isinstance(res, dict) else res

    def retrieve(self, model: str, **kw: Any) -> Any:
        """One model, the same entry ``list`` returns for it (``GET /v1/models/{model}``).

        IDs with slashes (``BAAI/bge-reranker-v2-m3``) keep their slashes; each segment is
        percent-encoded. An unknown
        id raises the API's 404 error.
        """
        return self._transport.request("GET", _model_path(model), auth="none", **kw)

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

    async def retrieve(self, model: str, **kw: Any) -> Any:
        return await self._transport.request("GET", _model_path(model), auth="none", **kw)

    async def detail(self, model: str, **kw: Any) -> Any:
        return await self._transport.request("GET", f"/api/models/{model}/detail", auth="none", **kw)

    async def allowed_params(self, model: str, **kw: Any) -> Any:
        return await self._transport.request("GET", f"/api/models/{model}/allowed-params", auth="none", **kw)

    async def classes(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/v1/playground/model-classes", auth="none", **kw)
