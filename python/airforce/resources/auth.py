"""Authentication, two-factor, and OAuth resources."""

from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Any, Dict, Optional, Sequence, Union
from urllib.parse import urlencode

from ._base import AsyncAPIResource, SyncAPIResource, clean

_SESSION = "session"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def create_pkce_pair() -> Dict[str, str]:
    """Generate a PKCE verifier/challenge pair (S256)."""
    verifier = _b64url(secrets.token_bytes(32))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return {"verifier": verifier, "challenge": challenge, "method": "S256"}


def _authorize_url(base_url: str, *, client_id: str, redirect_uri: str,
                   scope: Union[str, Sequence[str], None] = None, state: Optional[str] = None,
                   code_challenge: Optional[str] = None, code_challenge_method: str = "S256") -> str:
    params = {"response_type": "code", "client_id": client_id, "redirect_uri": redirect_uri}
    if scope is not None:
        params["scope"] = " ".join(scope) if not isinstance(scope, str) else scope
    if state is not None:
        params["state"] = state
    if code_challenge is not None:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = code_challenge_method
    return f"{base_url}/oauth/authorize?{urlencode(params)}"


class TwoFactor(SyncAPIResource):
    def setup_init(self, **kw: Any) -> Any:
        return self._transport.request("POST", "/api/2fa/setup-init", auth=_SESSION, **kw)

    def setup_verify(self, code: str, **kw: Any) -> Any:
        return self._transport.request("POST", "/api/2fa/setup-verify", auth=_SESSION, json={"code": code}, **kw)

    def disable(self, *, password: str, code: str, **kw: Any) -> Any:
        return self._transport.request("POST", "/api/2fa/disable", auth=_SESSION, json={"password": password, "code": code}, **kw)

    def regenerate_backup_codes(self, code: str, **kw: Any) -> Any:
        return self._transport.request("POST", "/api/2fa/regenerate-backup-codes", auth=_SESSION, json={"code": code}, **kw)

    def verify_step_up(self, code: str, **kw: Any) -> Any:
        return self._transport.request("POST", "/api/2fa/verify-step-up", auth=_SESSION, json={"code": code}, **kw)

    def step_up_status(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/2fa/step-up-status", auth=_SESSION, **kw)


class AsyncTwoFactor(AsyncAPIResource):
    async def setup_init(self, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/2fa/setup-init", auth=_SESSION, **kw)

    async def setup_verify(self, code: str, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/2fa/setup-verify", auth=_SESSION, json={"code": code}, **kw)

    async def disable(self, *, password: str, code: str, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/2fa/disable", auth=_SESSION, json={"password": password, "code": code}, **kw)

    async def regenerate_backup_codes(self, code: str, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/2fa/regenerate-backup-codes", auth=_SESSION, json={"code": code}, **kw)

    async def verify_step_up(self, code: str, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/2fa/verify-step-up", auth=_SESSION, json={"code": code}, **kw)

    async def step_up_status(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/2fa/step-up-status", auth=_SESSION, **kw)


class Auth(SyncAPIResource):
    def _adopt_cookie(self, result: Any) -> Any:
        token = self._transport.get_session_cookie()
        if token:
            self._transport.session_token = token
        if isinstance(result, dict):
            return {**result, "session_token": token}
        return result

    def signup(self, **params: Any) -> Any:
        return self._adopt_cookie(self._transport.request("POST", "/auth/signup", auth="none", json=clean(**params)))

    def signup_precheck(self, **params: Any) -> Any:
        return self._transport.request("POST", "/auth/signup/precheck", auth="none", json=clean(**params))

    def login(self, *, username: str, password: str, captcha_token: str, **kw: Any) -> Any:
        return self._adopt_cookie(self._transport.request(
            "POST", "/auth/login", auth="none",
            json={"username": username, "password": password, "captcha_token": captcha_token}, **kw))

    def verify_2fa(self, challenge_token: str, *, code: str, backup_code: Optional[str] = None, **kw: Any) -> Any:
        return self._adopt_cookie(self._transport.request(
            "POST", "/auth/2fa/verify", auth="none",
            headers={"authorization": f"Bearer {challenge_token}"},
            json=clean(code=code, backup_code=backup_code), **kw))

    def verify_email(self, token: str, **kw: Any) -> Any:
        return self._transport.request("POST", "/auth/verify", auth="none", json={"token": token}, **kw)

    def resend_verification(self, identifier: str, **kw: Any) -> Any:
        return self._transport.request("POST", "/auth/resend-verification", auth="none", json={"identifier": identifier}, **kw)

    def logout(self, **kw: Any) -> Any:
        result = self._transport.request("POST", "/auth/logout", auth=_SESSION, **kw)
        self._transport.session_token = None
        return result


class AsyncAuth(AsyncAPIResource):
    def _adopt_cookie(self, result: Any) -> Any:
        token = self._transport.get_session_cookie()
        if token:
            self._transport.session_token = token
        if isinstance(result, dict):
            return {**result, "session_token": token}
        return result

    async def signup(self, **params: Any) -> Any:
        return self._adopt_cookie(await self._transport.request("POST", "/auth/signup", auth="none", json=clean(**params)))

    async def signup_precheck(self, **params: Any) -> Any:
        return await self._transport.request("POST", "/auth/signup/precheck", auth="none", json=clean(**params))

    async def login(self, *, username: str, password: str, captcha_token: str, **kw: Any) -> Any:
        return self._adopt_cookie(await self._transport.request(
            "POST", "/auth/login", auth="none",
            json={"username": username, "password": password, "captcha_token": captcha_token}, **kw))

    async def verify_2fa(self, challenge_token: str, *, code: str, backup_code: Optional[str] = None, **kw: Any) -> Any:
        return self._adopt_cookie(await self._transport.request(
            "POST", "/auth/2fa/verify", auth="none",
            headers={"authorization": f"Bearer {challenge_token}"},
            json=clean(code=code, backup_code=backup_code), **kw))

    async def verify_email(self, token: str, **kw: Any) -> Any:
        return await self._transport.request("POST", "/auth/verify", auth="none", json={"token": token}, **kw)

    async def resend_verification(self, identifier: str, **kw: Any) -> Any:
        return await self._transport.request("POST", "/auth/resend-verification", auth="none", json={"identifier": identifier}, **kw)

    async def logout(self, **kw: Any) -> Any:
        result = await self._transport.request("POST", "/auth/logout", auth=_SESSION, **kw)
        self._transport.session_token = None
        return result


class OAuth(SyncAPIResource):
    create_pkce_pair = staticmethod(create_pkce_pair)

    def authorize_url(self, **params: Any) -> str:
        return _authorize_url(self._transport.base_url, **params)

    def exchange_token(self, *, code: str, redirect_uri: str, client_id: Optional[str] = None,
                       client_secret: Optional[str] = None, code_verifier: Optional[str] = None, **kw: Any) -> Any:
        data = clean(grant_type="authorization_code", code=code, redirect_uri=redirect_uri,
                     client_id=client_id, client_secret=client_secret, code_verifier=code_verifier)
        return self._transport.request("POST", "/oauth/token", auth="none", data=data, **kw)

    def user_info(self, access_token: str, **kw: Any) -> Any:
        return self._transport.request("GET", "/oauth/userinfo", auth="none",
                                       headers={"authorization": f"Bearer {access_token}"}, **kw)

    def revoke_token(self, token: str, **kw: Any) -> Any:
        return self._transport.request("POST", "/oauth/revoke", auth="none", data={"token": token}, **kw)

    def list_apps(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/me/oauth-apps", auth=_SESSION, **kw)

    def create_app(self, **params: Any) -> Any:
        return self._transport.request("POST", "/api/me/oauth-apps", auth=_SESSION, json=clean(**params))

    def get_app(self, client_id: str, **kw: Any) -> Any:
        return self._transport.request("GET", f"/api/me/oauth-apps/{client_id}", auth=_SESSION, **kw)

    def update_app(self, client_id: str, **patch: Any) -> Any:
        return self._transport.request("PATCH", f"/api/me/oauth-apps/{client_id}", auth=_SESSION, json=clean(**patch))

    def delete_app(self, client_id: str, **kw: Any) -> Any:
        return self._transport.request("DELETE", f"/api/me/oauth-apps/{client_id}", auth=_SESSION, **kw)

    def rotate_secret(self, client_id: str, **kw: Any) -> Any:
        return self._transport.request("POST", f"/api/me/oauth-apps/{client_id}/rotate-secret", auth=_SESSION, **kw)

    def connected_apps(self, **kw: Any) -> Any:
        return self._transport.request("GET", "/api/me/connected-apps", auth=_SESSION, **kw)

    def revoke_connected_app(self, client_id: str, **kw: Any) -> Any:
        return self._transport.request("DELETE", f"/api/me/connected-apps/{client_id}", auth=_SESSION, **kw)


class AsyncOAuth(AsyncAPIResource):
    create_pkce_pair = staticmethod(create_pkce_pair)

    def authorize_url(self, **params: Any) -> str:
        return _authorize_url(self._transport.base_url, **params)

    async def exchange_token(self, *, code: str, redirect_uri: str, client_id: Optional[str] = None,
                             client_secret: Optional[str] = None, code_verifier: Optional[str] = None, **kw: Any) -> Any:
        data = clean(grant_type="authorization_code", code=code, redirect_uri=redirect_uri,
                     client_id=client_id, client_secret=client_secret, code_verifier=code_verifier)
        return await self._transport.request("POST", "/oauth/token", auth="none", data=data, **kw)

    async def user_info(self, access_token: str, **kw: Any) -> Any:
        return await self._transport.request("GET", "/oauth/userinfo", auth="none",
                                             headers={"authorization": f"Bearer {access_token}"}, **kw)

    async def revoke_token(self, token: str, **kw: Any) -> Any:
        return await self._transport.request("POST", "/oauth/revoke", auth="none", data={"token": token}, **kw)

    async def list_apps(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/me/oauth-apps", auth=_SESSION, **kw)

    async def create_app(self, **params: Any) -> Any:
        return await self._transport.request("POST", "/api/me/oauth-apps", auth=_SESSION, json=clean(**params))

    async def get_app(self, client_id: str, **kw: Any) -> Any:
        return await self._transport.request("GET", f"/api/me/oauth-apps/{client_id}", auth=_SESSION, **kw)

    async def update_app(self, client_id: str, **patch: Any) -> Any:
        return await self._transport.request("PATCH", f"/api/me/oauth-apps/{client_id}", auth=_SESSION, json=clean(**patch))

    async def delete_app(self, client_id: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/api/me/oauth-apps/{client_id}", auth=_SESSION, **kw)

    async def rotate_secret(self, client_id: str, **kw: Any) -> Any:
        return await self._transport.request("POST", f"/api/me/oauth-apps/{client_id}/rotate-secret", auth=_SESSION, **kw)

    async def connected_apps(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/me/connected-apps", auth=_SESSION, **kw)

    async def revoke_connected_app(self, client_id: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/api/me/connected-apps/{client_id}", auth=_SESSION, **kw)
