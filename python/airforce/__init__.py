"""Official Python SDK for the api.airforce AI gateway."""

from __future__ import annotations

from ._client import Airforce, AsyncAirforce
from ._exceptions import (
    AirforceConnectionError,
    AirforceError,
    AirforceTimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InsufficientBalanceError,
    InternalServerError,
    MissingCredentialError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from ._streaming import AsyncStream, Stream
from ._version import __version__
from .resources import create_pkce_pair

__all__ = [
    "Airforce",
    "AsyncAirforce",
    "Stream",
    "AsyncStream",
    "create_pkce_pair",
    "__version__",
    "AirforceError",
    "BadRequestError",
    "AuthenticationError",
    "InsufficientBalanceError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "UnprocessableEntityError",
    "RateLimitError",
    "InternalServerError",
    "AirforceConnectionError",
    "AirforceTimeoutError",
    "MissingCredentialError",
]
