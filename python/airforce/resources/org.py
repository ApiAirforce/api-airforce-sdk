"""Organization self-service resources: org, members, invites, org keys, usage."""

from __future__ import annotations

from typing import Any, List, Optional

from ._base import AsyncAPIResource, SyncAPIResource, clean, enc

_SESSION = "session"


class Org(SyncAPIResource):
    """Team self-service under ``/api/org/*``. All endpoints use a session JWT; the
    org context is implicit via the caller's membership (one org per user). Roles:
    owner > admin > member. ``404 no_org`` when the caller belongs to no org;
    suspended members get ``403 membership_inactive`` everywhere."""

    def get(self, **kw: Any) -> Any:
        """The caller's org + own role → ``{org: Org, role}``."""
        return self._transport.request("GET", "/api/org", auth=_SESSION, **kw)

    def update(self, *, name: Optional[str] = None, **kw: Any) -> Any:
        """Rename the org (owner only; name 1-100 chars)."""
        return self._transport.request("PATCH", "/api/org", auth=_SESSION, json=clean(name=name), **kw)

    def update_sso(self, *, tenant_id: Optional[str] = None, verified_domain: Optional[str] = None, enforced: Optional[bool] = None, **kw: Any) -> Any:
        """Owner-only SSO config. ``''`` clears a field; omitted fields stay
        unchanged. 409 ``tenant_already_claimed``/``domain_already_claimed``."""
        return self._transport.request("PATCH", "/api/org/sso", auth=_SESSION,
                                       json=clean(tenant_id=tenant_id, verified_domain=verified_domain, enforced=enforced), **kw)

    def members(self, **kw: Any) -> List[Any]:
        """List members (owner/admin only)."""
        res = self._transport.request("GET", "/api/org/members", auth=_SESSION, **kw)
        return res.get("members", []) if isinstance(res, dict) else res

    def update_member(self, user_id: str, *, role: Optional[str] = None, status: Optional[str] = None, **kw: Any) -> Any:
        """Change a member's role ('admin'|'member', owner only) and/or status
        ('active'|'suspended'); suspending disables the member's org keys."""
        return self._transport.request("PATCH", f"/api/org/members/{enc(user_id)}", auth=_SESSION,
                                       json=clean(role=role, status=status), **kw)

    def remove_member(self, user_id: str, **kw: Any) -> Any:
        """Remove a member (owner/admin) or leave the org (self)."""
        return self._transport.request("DELETE", f"/api/org/members/{enc(user_id)}", auth=_SESSION, **kw)

    def invites(self, **kw: Any) -> List[Any]:
        """List pending invites (owner/admin only)."""
        res = self._transport.request("GET", "/api/org/invites", auth=_SESSION, **kw)
        return res.get("invites", []) if isinstance(res, dict) else res

    def create_invite(self, *, email: str, role: Optional[str] = None, **kw: Any) -> Any:
        """Invite by email (7-day expiry; admin invites are owner-only). The
        response's ``invite_url`` is the reliable delivery path."""
        return self._transport.request("POST", "/api/org/invites", auth=_SESSION, json=clean(email=email, role=role), **kw)

    def accept_invite(self, token: str, **kw: Any) -> Any:
        """Accept an invite (any logged-in user without an org); the caller's email
        must match the invite and be verified."""
        return self._transport.request("POST", "/api/org/invites/accept", auth=_SESSION, json={"token": token}, **kw)

    def revoke_invite(self, invite_id: str, **kw: Any) -> Any:
        return self._transport.request("DELETE", f"/api/org/invites/{enc(invite_id)}", auth=_SESSION, **kw)

    def keys(self, **kw: Any) -> List[Any]:
        """List org keys — owner/admin: all; member: own only (masked)."""
        res = self._transport.request("GET", "/api/org/keys", auth=_SESSION, **kw)
        return res.get("keys", []) if isinstance(res, dict) else res

    def create_key(self, *, member_user_id: str, **params: Any) -> Any:
        """Create an org key FOR a member (owner/admin); bills the org owner's
        wallet. Optional: label, credit_allowance, limit_reset, rpm_limit,
        allowed/blocked models/makers/classes/channels/methods, allowed_ips.
        The full key is shown only once, in the create response."""
        return self._transport.request("POST", "/api/org/keys", auth=_SESSION,
                                       json={"member_user_id": member_user_id, **clean(**params)})

    def update_key(self, key_id: str, **params: Any) -> Any:
        """Update an org key (owner/admin); same fields as create plus ``disabled``
        (``member_user_id`` is not changeable)."""
        return self._transport.request("PATCH", f"/api/org/keys/{enc(key_id)}", auth=_SESSION, json=clean(**params))

    def delete_key(self, key_id: str, **kw: Any) -> Any:
        return self._transport.request("DELETE", f"/api/org/keys/{enc(key_id)}", auth=_SESSION, **kw)

    def usage(self, *, from_: Optional[int] = None, to: Optional[int] = None,
              member_user_id: Optional[str] = None, key_id: Optional[str] = None, **kw: Any) -> Any:
        """Aggregate + per-member + per-key + daily timeseries usage (member role is
        scoped to self). ``from_``/``to`` are unix seconds (default: last 30 days);
        cost values are cents."""
        params = clean(**{"from": from_, "to": to, "member_user_id": member_user_id, "key_id": key_id})
        return self._transport.request("GET", "/api/org/usage", auth=_SESSION, params=params, **kw)


class AsyncOrg(AsyncAPIResource):
    async def get(self, **kw: Any) -> Any:
        return await self._transport.request("GET", "/api/org", auth=_SESSION, **kw)

    async def update(self, *, name: Optional[str] = None, **kw: Any) -> Any:
        return await self._transport.request("PATCH", "/api/org", auth=_SESSION, json=clean(name=name), **kw)

    async def update_sso(self, *, tenant_id: Optional[str] = None, verified_domain: Optional[str] = None, enforced: Optional[bool] = None, **kw: Any) -> Any:
        return await self._transport.request("PATCH", "/api/org/sso", auth=_SESSION,
                                             json=clean(tenant_id=tenant_id, verified_domain=verified_domain, enforced=enforced), **kw)

    async def members(self, **kw: Any) -> List[Any]:
        res = await self._transport.request("GET", "/api/org/members", auth=_SESSION, **kw)
        return res.get("members", []) if isinstance(res, dict) else res

    async def update_member(self, user_id: str, *, role: Optional[str] = None, status: Optional[str] = None, **kw: Any) -> Any:
        return await self._transport.request("PATCH", f"/api/org/members/{enc(user_id)}", auth=_SESSION,
                                             json=clean(role=role, status=status), **kw)

    async def remove_member(self, user_id: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/api/org/members/{enc(user_id)}", auth=_SESSION, **kw)

    async def invites(self, **kw: Any) -> List[Any]:
        res = await self._transport.request("GET", "/api/org/invites", auth=_SESSION, **kw)
        return res.get("invites", []) if isinstance(res, dict) else res

    async def create_invite(self, *, email: str, role: Optional[str] = None, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/org/invites", auth=_SESSION, json=clean(email=email, role=role), **kw)

    async def accept_invite(self, token: str, **kw: Any) -> Any:
        return await self._transport.request("POST", "/api/org/invites/accept", auth=_SESSION, json={"token": token}, **kw)

    async def revoke_invite(self, invite_id: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/api/org/invites/{enc(invite_id)}", auth=_SESSION, **kw)

    async def keys(self, **kw: Any) -> List[Any]:
        res = await self._transport.request("GET", "/api/org/keys", auth=_SESSION, **kw)
        return res.get("keys", []) if isinstance(res, dict) else res

    async def create_key(self, *, member_user_id: str, **params: Any) -> Any:
        return await self._transport.request("POST", "/api/org/keys", auth=_SESSION,
                                             json={"member_user_id": member_user_id, **clean(**params)})

    async def update_key(self, key_id: str, **params: Any) -> Any:
        return await self._transport.request("PATCH", f"/api/org/keys/{enc(key_id)}", auth=_SESSION, json=clean(**params))

    async def delete_key(self, key_id: str, **kw: Any) -> Any:
        return await self._transport.request("DELETE", f"/api/org/keys/{enc(key_id)}", auth=_SESSION, **kw)

    async def usage(self, *, from_: Optional[int] = None, to: Optional[int] = None,
                    member_user_id: Optional[str] = None, key_id: Optional[str] = None, **kw: Any) -> Any:
        params = clean(**{"from": from_, "to": to, "member_user_id": member_user_id, "key_id": key_id})
        return await self._transport.request("GET", "/api/org/usage", auth=_SESSION, params=params, **kw)
