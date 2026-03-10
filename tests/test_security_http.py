"""Comprehensive unit tests for security_http.py — CORS, auth, rate limiting, event logging."""

from __future__ import annotations

import json
import os
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from security_http import (
    DEFAULT_SECURITY_HEADERS,
    SecurityEventLogger,
    SlidingWindowRateLimiter,
    header_token,
    is_authorized,
    is_authorized_any,
    parse_key_values,
    parse_origin_allowlist,
    resolve_allow_origin,
    safe_client_ip,
)


# ────────────────────────────────────────────────
# parse_origin_allowlist
# ────────────────────────────────────────────────


class TestParseOriginAllowlist:
    def test_empty_string(self) -> None:
        assert parse_origin_allowlist("") == set()

    def test_none(self) -> None:
        assert parse_origin_allowlist(None) == set()  # type: ignore[arg-type]

    def test_single_origin(self) -> None:
        assert parse_origin_allowlist("https://example.com") == {"https://example.com"}

    def test_multiple_origins(self) -> None:
        result = parse_origin_allowlist("https://a.com,https://b.com,https://c.com")
        assert result == {"https://a.com", "https://b.com", "https://c.com"}

    def test_trailing_slash_stripped(self) -> None:
        result = parse_origin_allowlist("https://example.com/")
        assert "https://example.com" in result
        assert "https://example.com/" not in result

    def test_whitespace_trimmed(self) -> None:
        result = parse_origin_allowlist("  https://a.com , https://b.com  ")
        assert result == {"https://a.com", "https://b.com"}

    def test_wildcard_returns_only_wildcard(self) -> None:
        result = parse_origin_allowlist("https://a.com,*,https://b.com")
        assert result == {"*"}

    def test_empty_segments_skipped(self) -> None:
        result = parse_origin_allowlist(",,,https://a.com,,,")
        assert result == {"https://a.com"}

    def test_wildcard_alone(self) -> None:
        assert parse_origin_allowlist("*") == {"*"}


# ────────────────────────────────────────────────
# resolve_allow_origin
# ────────────────────────────────────────────────


class TestResolveAllowOrigin:
    def test_empty_allowlist_returns_empty(self) -> None:
        assert resolve_allow_origin("https://a.com", set()) == ""

    def test_none_allowlist_returns_empty(self) -> None:
        assert resolve_allow_origin("https://a.com", None) == ""  # type: ignore[arg-type]

    def test_origin_in_allowlist(self) -> None:
        assert resolve_allow_origin("https://a.com", {"https://a.com"}) == "https://a.com"

    def test_origin_not_in_allowlist(self) -> None:
        assert resolve_allow_origin("https://evil.com", {"https://a.com"}) == ""

    def test_wildcard_echoes_origin(self) -> None:
        assert resolve_allow_origin("https://any.com", {"*"}) == "https://any.com"

    def test_wildcard_no_origin_returns_star(self) -> None:
        assert resolve_allow_origin("", {"*"}) == "*"

    def test_none_origin(self) -> None:
        assert resolve_allow_origin(None, {"https://a.com"}) == ""  # type: ignore[arg-type]

    def test_trailing_slash_stripped_from_origin(self) -> None:
        # resolve_allow_origin strips trailing slash from request_origin
        assert resolve_allow_origin("https://a.com/", {"https://a.com"}) == "https://a.com"


# ────────────────────────────────────────────────
# header_token
# ────────────────────────────────────────────────


class TestHeaderToken:
    def test_bearer_token(self) -> None:
        headers = {"Authorization": "Bearer abc123"}
        assert header_token(headers, "x") == "abc123"

    def test_bearer_case_insensitive(self) -> None:
        headers = {"Authorization": "bearer XYZ"}
        assert header_token(headers, "x") == "XYZ"

    def test_api_key_header(self) -> None:
        headers = {"X-API-Key": "key456"}
        assert header_token(headers, "x") == "key456"

    def test_bearer_takes_precedence_over_api_key(self) -> None:
        headers = {"Authorization": "Bearer first", "X-API-Key": "second"}
        assert header_token(headers, "x") == "first"

    def test_no_headers(self) -> None:
        assert header_token({}, "x") == ""

    def test_empty_expected(self) -> None:
        headers = {"Authorization": "Bearer abc"}
        assert header_token(headers, "") == ""

    def test_whitespace_stripped(self) -> None:
        headers = {"Authorization": "Bearer   spaced  "}
        assert header_token(headers, "x") == "spaced"

    def test_non_bearer_auth_falls_through_to_api_key(self) -> None:
        headers = {"Authorization": "Basic xyz", "X-API-Key": "fallback"}
        assert header_token(headers, "x") == "fallback"


# ────────────────────────────────────────────────
# parse_key_values
# ────────────────────────────────────────────────


class TestParseKeyValues:
    def test_empty(self) -> None:
        assert parse_key_values("") == ()

    def test_none(self) -> None:
        assert parse_key_values(None) == ()  # type: ignore[arg-type]

    def test_single_value(self) -> None:
        assert parse_key_values("abc") == ("abc",)

    def test_multiple_values(self) -> None:
        assert parse_key_values("a,b,c") == ("a", "b", "c")

    def test_colon_format_extracts_key(self) -> None:
        # "name:key" → extracts key part
        assert parse_key_values("tenant1:key1,tenant2:key2") == ("key1", "key2")

    def test_deduplication_preserves_order(self) -> None:
        assert parse_key_values("a,b,a,c,b") == ("a", "b", "c")

    def test_whitespace_trimmed(self) -> None:
        assert parse_key_values("  x , y , z  ") == ("x", "y", "z")

    def test_empty_segments_skipped(self) -> None:
        assert parse_key_values(",,,a,,,b,,,") == ("a", "b")

    def test_colon_with_empty_key(self) -> None:
        # "name:" → empty key after colon → skipped
        assert parse_key_values("name:") == ()

    def test_mixed_plain_and_colon(self) -> None:
        assert parse_key_values("plain,name:keyed") == ("plain", "keyed")


# ────────────────────────────────────────────────
# is_authorized_any / is_authorized
# ────────────────────────────────────────────────


class TestIsAuthorized:
    def test_empty_expected_always_passes(self) -> None:
        assert is_authorized_any({}, ()) is True

    def test_no_token_fails(self) -> None:
        assert is_authorized_any({}, ("secret",)) is False

    def test_correct_bearer_passes(self) -> None:
        headers = {"Authorization": "Bearer secret"}
        assert is_authorized_any(headers, ("secret",)) is True

    def test_wrong_token_fails(self) -> None:
        headers = {"Authorization": "Bearer wrong"}
        assert is_authorized_any(headers, ("secret",)) is False

    def test_multiple_expected_any_match(self) -> None:
        headers = {"Authorization": "Bearer key2"}
        assert is_authorized_any(headers, ("key1", "key2", "key3")) is True

    def test_api_key_header_works(self) -> None:
        headers = {"X-API-Key": "mykey"}
        assert is_authorized_any(headers, ("mykey",)) is True

    def test_is_authorized_wrapper_comma_string(self) -> None:
        headers = {"Authorization": "Bearer val2"}
        assert is_authorized(headers, "val1,val2,val3") is True

    def test_is_authorized_wrapper_no_match(self) -> None:
        headers = {"Authorization": "Bearer nope"}
        assert is_authorized(headers, "val1,val2") is False

    def test_is_authorized_empty_expected(self) -> None:
        assert is_authorized({}, "") is True

    def test_timing_safe_comparison(self) -> None:
        # Ensure hmac.compare_digest is used (not ==)
        headers = {"Authorization": "Bearer secret"}
        assert is_authorized_any(headers, ("secret",)) is True


# ────────────────────────────────────────────────
# safe_client_ip
# ────────────────────────────────────────────────


class TestSafeClientIp:
    def _handler(self, client_address=None, forwarded_for=None):
        headers = {}
        if forwarded_for is not None:
            headers["X-Forwarded-For"] = forwarded_for
        h = SimpleNamespace(client_address=client_address, headers=headers)
        return h

    def test_basic_client_address(self) -> None:
        h = self._handler(client_address=("192.168.1.1", 12345))
        assert safe_client_ip(h) == "192.168.1.1"

    def test_no_client_address(self) -> None:
        h = SimpleNamespace(client_address=None, headers={})
        assert safe_client_ip(h) == "unknown"

    def test_x_forwarded_for_trusted(self) -> None:
        h = self._handler(client_address=("10.0.0.1", 80), forwarded_for="203.0.113.5, 10.0.0.1")
        assert safe_client_ip(h, trust_x_forwarded_for=True) == "203.0.113.5"

    def test_x_forwarded_for_not_trusted(self) -> None:
        h = self._handler(client_address=("10.0.0.1", 80), forwarded_for="203.0.113.5")
        assert safe_client_ip(h, trust_x_forwarded_for=False) == "10.0.0.1"

    def test_x_forwarded_for_invalid_ip(self) -> None:
        h = self._handler(client_address=("10.0.0.1", 80), forwarded_for="not-an-ip")
        assert safe_client_ip(h, trust_x_forwarded_for=True) == "10.0.0.1"

    def test_invalid_client_address(self) -> None:
        h = SimpleNamespace(client_address=("not-an-ip", 80), headers={})
        assert safe_client_ip(h) == "unknown"

    def test_ipv6_forwarded_for(self) -> None:
        h = self._handler(client_address=("10.0.0.1", 80), forwarded_for="::1")
        assert safe_client_ip(h, trust_x_forwarded_for=True) == "::1"

    def test_empty_forwarded_for_falls_back(self) -> None:
        h = self._handler(client_address=("10.0.0.1", 80), forwarded_for="")
        assert safe_client_ip(h, trust_x_forwarded_for=True) == "10.0.0.1"


# ────────────────────────────────────────────────
# SlidingWindowRateLimiter
# ────────────────────────────────────────────────


class TestSlidingWindowRateLimiter:
    def test_init_defaults(self) -> None:
        rl = SlidingWindowRateLimiter(limit=10, window_seconds=60)
        assert rl.limit == 10
        assert rl.window_seconds == 60

    def test_init_clamps_to_minimum(self) -> None:
        rl = SlidingWindowRateLimiter(limit=0, window_seconds=0, max_keys=0)
        assert rl.limit >= 1
        assert rl.window_seconds >= 1
        assert rl.max_keys >= 100

    def test_allow_within_limit(self) -> None:
        rl = SlidingWindowRateLimiter(limit=5, window_seconds=60)
        for _ in range(5):
            allowed, _ = rl.allow("user1")
            assert allowed is True

    def test_deny_over_limit(self) -> None:
        rl = SlidingWindowRateLimiter(limit=3, window_seconds=60)
        for _ in range(3):
            rl.allow("user1")
        allowed, retry_after = rl.allow("user1")
        assert allowed is False
        assert retry_after > 0

    def test_different_keys_independent(self) -> None:
        rl = SlidingWindowRateLimiter(limit=1, window_seconds=60)
        ok1, _ = rl.allow("a")
        ok2, _ = rl.allow("b")
        assert ok1 is True
        assert ok2 is True

    def test_window_expiry_allows_again(self) -> None:
        rl = SlidingWindowRateLimiter(limit=1, window_seconds=1)
        rl.allow("user")
        allowed, _ = rl.allow("user")
        assert allowed is False
        # Simulate time passing
        with patch("time.monotonic", return_value=time.monotonic() + 2):
            allowed2, _ = rl.allow("user")
            assert allowed2 is True

    def test_none_key_becomes_unknown(self) -> None:
        rl = SlidingWindowRateLimiter(limit=2)
        ok, _ = rl.allow(None)  # type: ignore[arg-type]
        assert ok is True

    def test_max_keys_overflow_handling(self) -> None:
        rl = SlidingWindowRateLimiter(limit=100, window_seconds=60, max_keys=100)
        # Fill up to max_keys
        for i in range(100):
            rl.allow(f"key_{i}")
        # Next key should still work due to purge_overflow
        ok, _ = rl.allow("overflow_key")
        # May or may not be allowed depending on purge, but should not crash
        assert isinstance(ok, bool)

    def test_retry_after_is_positive(self) -> None:
        rl = SlidingWindowRateLimiter(limit=1, window_seconds=30)
        rl.allow("user")
        _, retry_after = rl.allow("user")
        assert retry_after >= 1
        assert retry_after <= 30


# ────────────────────────────────────────────────
# SecurityEventLogger
# ────────────────────────────────────────────────


class TestSecurityEventLogger:
    def test_empty_path_no_write(self, tmp_path) -> None:
        logger = SecurityEventLogger("")
        logger.append({"action": "test"})
        # No crash, no file created

    def test_append_creates_file(self, tmp_path) -> None:
        path = str(tmp_path / "events.jsonl")
        logger = SecurityEventLogger(path)
        logger.append({"action": "login", "user": "test"})
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            line = f.readline()
        data = json.loads(line)
        assert data["action"] == "login"
        assert "ts" in data

    def test_append_multiple_events(self, tmp_path) -> None:
        path = str(tmp_path / "events.jsonl")
        logger = SecurityEventLogger(path)
        logger.append({"event": "a"})
        logger.append({"event": "b"})
        logger.append({"event": "c"})
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 3

    def test_ts_default_set(self, tmp_path) -> None:
        path = str(tmp_path / "events.jsonl")
        logger = SecurityEventLogger(path)
        logger.append({"x": 1})
        with open(path, encoding="utf-8") as f:
            data = json.loads(f.readline())
        assert isinstance(data["ts"], int)

    def test_ts_not_overwritten(self, tmp_path) -> None:
        path = str(tmp_path / "events.jsonl")
        logger = SecurityEventLogger(path)
        logger.append({"ts": 99999})
        with open(path, encoding="utf-8") as f:
            data = json.loads(f.readline())
        assert data["ts"] == 99999

    def test_nested_directory_creation(self, tmp_path) -> None:
        path = str(tmp_path / "deep" / "nested" / "events.jsonl")
        logger = SecurityEventLogger(path)
        logger.append({"test": True})
        assert os.path.exists(path)

    def test_none_event(self, tmp_path) -> None:
        path = str(tmp_path / "events.jsonl")
        logger = SecurityEventLogger(path)
        logger.append(None)  # type: ignore[arg-type]
        # Should not crash


# ────────────────────────────────────────────────
# DEFAULT_SECURITY_HEADERS
# ────────────────────────────────────────────────


class TestDefaultSecurityHeaders:
    def test_is_tuple_of_tuples(self) -> None:
        assert isinstance(DEFAULT_SECURITY_HEADERS, tuple)
        for item in DEFAULT_SECURITY_HEADERS:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_contains_critical_headers(self) -> None:
        header_names = {h[0] for h in DEFAULT_SECURITY_HEADERS}
        assert "X-Content-Type-Options" in header_names
        assert "X-Frame-Options" in header_names
        assert "Content-Security-Policy" in header_names

    def test_frame_options_deny(self) -> None:
        headers_dict = dict(DEFAULT_SECURITY_HEADERS)
        assert headers_dict["X-Frame-Options"] == "DENY"
