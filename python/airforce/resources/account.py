"""Account self-service, API keys, and billing resources."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ._base import AsyncAPIResource, SyncAPIResource, clean, enc

_SESSION = "session"
_APIKEY = "api_key"


class Account(SyncAPIResource):
    def me(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/me", auth=_SESSION, **kw)

    def usage(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/usage", auth=_SESSION, **kw)

    def my_usage(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/my-usage", auth=_SESSION, **kw)

    def update(self, *, username: Optional[str] = None, email: Optional[str] = None, password: Optional[str] = None, **kw: Any) -> Any:
        return self._transport.request("PUT", "/api/user/update", auth=_SESSION, json=clean(username=username, email=email, password=password), **kw)

    def request_password_reset(self, *, email: str, locale: Optional[str] = None, **kw: Any) -> Any:
        return self._transport.request("POST", "/api/auth/request-password-reset", auth="none", json=clean(email=email, locale=locale), **kw)

    def reset_password(self, *, token: str, new_password: str, **kw: Any) -> Any:
        return self._transport.request("POST", "/api/auth/reset-password", auth="none", json={"token": token, "new_password": new_password}, **kw)

    def referral_code(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/referral/code", auth=_SESSION, **kw)

    def referred_users(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/referral/referred-users", auth=_SESSION, **kw)

    def get_price_caps(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/user/price-caps", auth=_SESSION, **kw)

    def set_price_caps(self, caps: Dict[str, Any], **kw: Any) -> Any:
        return self._transport.request("PUT", "/api/user/price-caps", auth=_SESSION, json={"caps": caps}, **kw)

    def delete_price_cap(self, model: str, **kw: Any) -> Any:
        return self._transport.request("DELETE", f"/api/user/price-caps/{enc(model)}", auth=_SESSION, **kw)

    def get_model_aliases(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/user/model-aliases", auth=_SESSION, **kw)

    def set_model_alias(self, *, alias: str, model: str, **kw: Any) -> Any:
        return self._transport.request("PUT", "/api/user/model-aliases", auth=_SESSION, json={"alias": alias, "model": model}, **kw)

    def set_model_aliases_batch(self, aliases: List[Dict[str, str]], **kw: Any) -> Any:
        return self._transport.request("PUT", "/api/user/model-aliases/batch", auth=_SESSION, json=aliases, **kw)

    def delete_model_alias(self, alias: str, **kw: Any) -> Any:
        return self._transport.request("DELETE", f"/api/user/model-aliases/{enc(alias)}", auth=_SESSION, **kw)

    def get_model_defaults(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/user/model-defaults", auth=_SESSION, **kw)

    def set_model_default(self, model: str, **default: Any) -> Any:
        return self._transport.request("PUT", f"/api/user/model-defaults/{enc(model)}", auth=_SESSION, json=clean(**default))

    def delete_model_default(self, model: str, **kw: Any) -> Any:
        return self._transport.request("DELETE", f"/api/user/model-defaults/{enc(model)}", auth=_SESSION, **kw)

    def get_smart_routing(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/user/smart-routing", auth=_APIKEY, **kw)

    def set_smart_routing(self, groups: Dict[str, Any], **kw: Any) -> Any:
        return self._transport.request("PUT", "/api/user/smart-routing", auth=_APIKEY, json={"groups": groups}, **kw)

    def test_smart_routing(self, model: str, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/user/smart-routing/test", auth=_APIKEY, params={"model": model}, **kw)

    def get_channel_prefs(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/user/channel-prefs", auth=_APIKEY, **kw)

    def set_channel_pins(self, pins: Dict[str, str], **kw: Any) -> Any:
        return self._transport.request("PUT", "/api/user/channel-prefs", auth=_APIKEY, json=pins, **kw)

    def sessions(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/me/sessions", auth=_SESSION, **kw)

    def revoke_session(self, jti: str, **kw: Any) -> Any:
        return self._transport.request("DELETE", f"/api/me/sessions/{enc(jti)}", auth=_SESSION, **kw)

    def revoke_other_sessions(self, **kw: Any) -> Any:
        return self._transport.request("DELETE", "/api/me/sessions", auth=_SESSION, **kw)

    def login_history(self, *, limit: Optional[int] = None, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/me/login-history", auth=_SESSION, params=clean(limit=limit), **kw)

    def reset_api_key(self, **kw: Any) -> Any:
        return self._transport.request("POST", "/api/user/reset-api-key", auth=_SESSION, **kw)

    def set_primary_allowed_ips(self, allowed_ips: List[str], **kw: Any) -> Any:
        return self._transport.request("PUT", "/api/user/primary-allowed-ips", auth=_SESSION, json={"allowed_ips": allowed_ips}, **kw)

    def set_backup_pool_enabled(self, enabled: bool, **kw: Any) -> Any:
        return self._transport.request("PUT", "/api/user/backup-pool-enabled", auth=_APIKEY, json={"enabled": enabled}, **kw)

    def toggle_pay_as_you_go(self, **kw: Any) -> Any:
        return self._transport.request("POST", "/api/pay-as-you-go/toggle", auth=_SESSION, **kw)


class AsyncAccount(AsyncAPIResource):
    async def me(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/me", auth=_SESSION, **kw)

    async def usage(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/usage", auth=_SESSION, **kw)

    async def my_usage(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/my-usage", auth=_SESSION, **kw)

    async def update(self, *, username: Optional[str] = None, email: Optional[str] = None, password: Optional[str] = None, **kw: Any) -> Any:
        return await self._transport.request("PUT", "/api/user/update", auth=_SESSION, json=clean(username=username, email=email, password=password), **kw)

    async def request_password_reset(self, *, email: str, locale: Optional[str] = None, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/auth/request-password-reset", auth="none", json=clean(email=email, locale=locale), **kw)

    async def reset_password(self, *, token: str, new_password: str, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/auth/reset-password", auth="none", json={"token": token, "new_password": new_password}, **kw)

    async def referral_code(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/referral/code", auth=_SESSION, **kw)

    async def referred_users(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/referral/referred-users", auth=_SESSION, **kw)

    async def get_price_caps(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/user/price-caps", auth=_SESSION, **kw)

    async def set_price_caps(self, caps: Dict[str, Any], **kw: Any) -> Any:
        return await self._transport.request("PUT", "/api/user/price-caps", auth=_SESSION, json={"caps": caps}, **kw)

    async def delete_price_cap(self, model: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/api/user/price-caps/{enc(model)}", auth=_SESSION, **kw)

    async def get_model_aliases(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/user/model-aliases", auth=_SESSION, **kw)

    async def set_model_alias(self, *, alias: str, model: str, **kw: Any) -> Any:
        return await self._transport.request("PUT", "/api/user/model-aliases", auth=_SESSION, json={"alias": alias, "model": model}, **kw)

    async def set_model_aliases_batch(self, aliases: List[Dict[str, str]], **kw: Any) -> Any:
        return await self._transport.request("PUT", "/api/user/model-aliases/batch", auth=_SESSION, json=aliases, **kw)

    async def delete_model_alias(self, alias: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/api/user/model-aliases/{enc(alias)}", auth=_SESSION, **kw)

    async def get_model_defaults(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/user/model-defaults", auth=_SESSION, **kw)

    async def set_model_default(self, model: str, **default: Any) -> Any:
        return await self._transport.request("PUT", f"/api/user/model-defaults/{enc(model)}", auth=_SESSION, json=clean(**default))

    async def delete_model_default(self, model: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/api/user/model-defaults/{enc(model)}", auth=_SESSION, **kw)

    async def get_smart_routing(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/user/smart-routing", auth=_APIKEY, **kw)

    async def set_smart_routing(self, groups: Dict[str, Any], **kw: Any) -> Any:
        return await self._transport.request("PUT", "/api/user/smart-routing", auth=_APIKEY, json={"groups": groups}, **kw)

    async def test_smart_routing(self, model: str, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/user/smart-routing/test", auth=_APIKEY, params={"model": model}, **kw)

    async def get_channel_prefs(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/user/channel-prefs", auth=_APIKEY, **kw)

    async def set_channel_pins(self, pins: Dict[str, str], **kw: Any) -> Any:
        return await self._transport.request("PUT", "/api/user/channel-prefs", auth=_APIKEY, json=pins, **kw)

    async def sessions(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/me/sessions", auth=_SESSION, **kw)

    async def revoke_session(self, jti: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/api/me/sessions/{enc(jti)}", auth=_SESSION, **kw)

    async def revoke_other_sessions(self, **kw: Any) -> Any:
        return await self._transport.request("DELETE", "/api/me/sessions", auth=_SESSION, **kw)

    async def login_history(self, *, limit: Optional[int] = None, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/me/login-history", auth=_SESSION, params=clean(limit=limit), **kw)

    async def reset_api_key(self, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/user/reset-api-key", auth=_SESSION, **kw)

    async def set_primary_allowed_ips(self, allowed_ips: List[str], **kw: Any) -> Any:
        return await self._transport.request("PUT", "/api/user/primary-allowed-ips", auth=_SESSION, json={"allowed_ips": allowed_ips}, **kw)

    async def set_backup_pool_enabled(self, enabled: bool, **kw: Any) -> Any:
        return await self._transport.request("PUT", "/api/user/backup-pool-enabled", auth=_APIKEY, json={"enabled": enabled}, **kw)

    async def toggle_pay_as_you_go(self, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/pay-as-you-go/toggle", auth=_SESSION, **kw)


class Keys(SyncAPIResource):
    def create(self, **params: Any) -> Any:
        return self._transport.request("POST", "/v1/keys", json=clean(**params))

    def list(self, **kw: Any) -> List[Any]:
        res = self._transport.request("GET", "/v1/keys", **kw)
        return res.get("keys", []) if isinstance(res, dict) else res

    def update(self, key: str, **params: Any) -> Any:
        return self._transport.request("PATCH", f"/v1/keys/{enc(key)}", json=clean(**params))

    def delete(self, key: str, **kw: Any) -> Any:
        return self._transport.request("DELETE", f"/v1/keys/{enc(key)}", **kw)


class AsyncKeys(AsyncAPIResource):
    async def create(self, **params: Any) -> Any:
        return await self._transport.request("POST", "/v1/keys", json=clean(**params))

    async def list(self, **kw: Any) -> List[Any]:
        res = await self._transport.request("GET", "/v1/keys", **kw)
        return res.get("keys", []) if isinstance(res, dict) else res

    async def update(self, key: str, **params: Any) -> Any:
        return await self._transport.request("PATCH", f"/v1/keys/{enc(key)}", json=clean(**params))

    async def delete(self, key: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/v1/keys/{enc(key)}", **kw)


class Billing(SyncAPIResource):
    def create_checkout(self, *, plan: str, **params: Any) -> Any:
        return self._transport.request("POST", "/api/creem/create-checkout", auth=_SESSION, json={"plan": plan, **clean(**params)})

    def create_crypto_invoice(self, *, plan: str, **params: Any) -> Any:
        return self._transport.request("POST", "/api/create-nowpayments-invoice", auth=_SESSION, json={"plan": plan, **clean(**params)})

    def create_portal_session(self, **kw: Any) -> Any:
        return self._transport.request("POST", "/api/create-portal-session", auth=_SESSION, json={}, **kw)

    def analytics(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/v1/analytics", auth="none", **kw)


class AsyncBilling(AsyncAPIResource):
    async def create_checkout(self, *, plan: str, **params: Any) -> Any:
        return await self._transport.request("POST", "/api/creem/create-checkout", auth=_SESSION, json={"plan": plan, **clean(**params)})

    async def create_crypto_invoice(self, *, plan: str, **params: Any) -> Any:
        return await self._transport.request("POST", "/api/create-nowpayments-invoice", auth=_SESSION, json={"plan": plan, **clean(**params)})

    async def create_portal_session(self, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/create-portal-session", auth=_SESSION, json={}, **kw)

    async def analytics(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/v1/analytics", auth="none", **kw)
