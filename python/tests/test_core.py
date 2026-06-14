from __future__ import annotations

from airforce import (
    AuthenticationError,
    ConflictError,
    InsufficientBalanceError,
    InternalServerError,
    RateLimitError,
)
from airforce._exceptions import AirforceError
from airforce._streaming import _SSEDecoder


def test_error_status_mapping():
    assert isinstance(AirforceError.from_response(401, {}), AuthenticationError)
    assert isinstance(AirforceError.from_response(402, {}), InsufficientBalanceError)
    assert isinstance(AirforceError.from_response(409, {}), ConflictError)
    assert isinstance(AirforceError.from_response(429, {}), RateLimitError)
    assert isinstance(AirforceError.from_response(503, {}), InternalServerError)


def test_error_body_parsing():
    err = AirforceError.from_response(
        403, {"error": {"message": "blocked", "code": "free_tier_gated", "type": "forbidden"}}
    )
    assert err.message == "blocked"
    assert err.code == "free_tier_gated"
    assert err.status == 403


def test_flat_error_body():
    err = AirforceError.from_response(400, {"error": "bad"})
    assert err.message == "bad"


def test_rate_limit_retry_after():
    err = AirforceError.from_response(429, {"retry_after": 7})
    assert isinstance(err, RateLimitError)
    assert err.retry_after == 7.0


def test_sse_decoder_splits_events():
    dec = _SSEDecoder()
    out = dec.feed('data: {"i":1}\n\ndata: {"i":2}\n\ndata: [DONE]\n\n')
    assert out == ['{"i":1}', '{"i":2}', "[DONE]"]


def test_sse_decoder_partial_chunks():
    dec = _SSEDecoder()
    assert dec.feed('data: {"hel') == []
    assert dec.feed('lo":1}\n\n') == ['{"hello":1}']


def test_sse_decoder_ignores_comments_and_crlf():
    dec = _SSEDecoder()
    out = dec.feed(": keep-alive\r\ndata: {\"ok\":true}\r\n\r\n")
    assert out == ['{"ok":true}']
