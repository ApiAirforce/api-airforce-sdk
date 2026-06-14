"""Exception hierarchy for the Airforce SDK."""

from __future__ import annotations

from typing import Any, Optional


def _parse_error_body(body: Any) -> dict:
    """Best-effort extraction of message/code/type from an arbitrary body."""
    if isinstance(body, str):
        return {"message": body}
    if isinstance(body, dict):
        err = body.get("error")
        if isinstance(err, dict):
            return err
        message = err if isinstance(err, str) else body.get("message")
        return {
            "message": message,
            "code": body.get("code"),
            "type": body.get("type"),
        }
    return {}


class AirforceError(Exception):
    """Base class for every error raised by the SDK."""

    def __init__(
        self,
        message: str,
        *,
        status: Optional[int] = None,
        code: Optional[str] = None,
        type: Optional[str] = None,
        param: Optional[str] = None,
        request_id: Optional[str] = None,
        body: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code
        self.type = type
        self.param = param
        self.request_id = request_id
        self.body = body

    @classmethod
    def from_response(
        cls, status: int, body: Any, request_id: Optional[str] = None
    ) -> "AirforceError":
        parsed = _parse_error_body(body)
        message = parsed.get("message") or f"Airforce API error (HTTP {status})"
        kwargs = dict(
            status=status,
            code=parsed.get("code"),
            type=parsed.get("type"),
            param=parsed.get("param"),
            request_id=request_id,
            body=body,
        )
        klass = _STATUS_MAP.get(status)
        if klass is None:
            klass = InternalServerError if status >= 500 else AirforceError
        return klass(message, **kwargs)


class BadRequestError(AirforceError):
    """400 — malformed request."""


class AuthenticationError(AirforceError):
    """401 — missing or invalid credentials."""


class InsufficientBalanceError(AirforceError):
    """402 — not enough balance/credits."""


class PermissionDeniedError(AirforceError):
    """403 — not allowed (includes ``free_tier_gated``)."""


class NotFoundError(AirforceError):
    """404 — resource not found or not owned by the caller."""


class ConflictError(AirforceError):
    """409 — conflict (e.g. already subscribed)."""


class UnprocessableEntityError(AirforceError):
    """422 — semantically invalid request."""


class RateLimitError(AirforceError):
    """429 — rate limited."""

    @property
    def retry_after(self) -> Optional[float]:
        if isinstance(self.body, dict):
            value = self.body.get("retry_after")
            if isinstance(value, (int, float)):
                return float(value)
        return None


class InternalServerError(AirforceError):
    """5xx — upstream/server failure."""


class AirforceConnectionError(AirforceError):
    """No HTTP response was received (DNS, TCP, TLS, transport failure)."""


class AirforceTimeoutError(AirforceError):
    """The request exceeded the configured timeout."""


class MissingCredentialError(AirforceError):
    """A required credential was not configured for the endpoint."""


_STATUS_MAP = {
    400: BadRequestError,
    401: AuthenticationError,
    402: InsufficientBalanceError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    429: RateLimitError,
}
