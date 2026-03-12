from __future__ import annotations

import hmac
import ipaddress
import json
import os
import time
from collections import deque
from collections.abc import Iterable, Sequence
from threading import Lock
from typing import Any

__all__ = [
    "DEFAULT_SECURITY_HEADERS",
    "parse_origin_allowlist",
    "resolve_allow_origin",
    "header_token",
    "parse_key_values",
    "is_authorized_any",
    "is_authorized",
    "safe_client_ip",
    "SlidingWindowRateLimiter",
    "SecurityEventLogger",
]


DEFAULT_SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Permissions-Policy", "geolocation=(), microphone=(), camera=()"),
    ("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"),
)


def parse_origin_allowlist(raw: str) -> set[str]:
    """Parse a comma-separated CORS origin allowlist into a set of normalised origins.

    Returns ``{"*"}`` immediately if the wildcard is present.  Trailing
    slashes are stripped so ``https://example.com/`` matches ``https://example.com``.
    """
    out: set[str] = set()
    for piece in str(raw or "").split(","):
        origin = str(piece or "").strip().rstrip("/")
        if not origin:
            continue
        if origin == "*":
            return {"*"}
        out.add(origin)
    return out


def resolve_allow_origin(request_origin: str, allowlist: Iterable[str]) -> str:
    """Return the origin to echo in ``Access-Control-Allow-Origin``, or ``""`` to deny.

    If the allowlist contains ``"*"``, any non-empty origin is allowed.
    """
    origin = str(request_origin or "").strip().rstrip("/")
    allowed = set(allowlist or set())
    if not allowed:
        return ""
    if "*" in allowed:
        return origin or "*"
    if origin in allowed:
        return origin
    return ""


def header_token(headers: Any, expected: str) -> str:
    """Extract the bearer token or API key from request headers.

    Checks ``Authorization: Bearer <token>`` first, then ``X-API-Key``.
    Returns ``""`` when *expected* is falsy (auth disabled).
    """
    if not expected:
        return ""
    auth = str(headers.get("Authorization", "") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return str(headers.get("X-API-Key", "") or "").strip()


def parse_key_values(raw: str) -> tuple[str, ...]:
    """Parse a comma-separated list of API keys into a deduplicated tuple.

    Supports ``name:key`` format (the ``name:`` prefix is stripped).
    Order is preserved; duplicates are removed.
    """
    out = []
    for piece in str(raw or "").split(","):
        token = str(piece or "").strip()
        if not token:
            continue
        # allow "name:key" format for tenant-aware lists
        if ":" in token:
            token = token.split(":", 1)[1].strip()
        if token:
            out.append(token)
    # preserve order, drop duplicates
    uniq = []
    seen = set()
    for item in out:
        if item in seen:
            continue
        seen.add(item)
        uniq.append(item)
    return tuple(uniq)


def is_authorized_any(headers: Any, expected_values: Sequence[str]) -> bool:
    """Return ``True`` if the request carries a token matching any value in *expected_values*.

    Uses ``hmac.compare_digest`` for constant-time comparison.
    An empty *expected_values* means auth is disabled (always returns ``True``).
    """
    if not expected_values:
        return True
    candidate = header_token(headers, "x")
    if not candidate:
        return False
    for expected in expected_values:
        if expected and hmac.compare_digest(candidate, expected):
            return True
    return False


def is_authorized(headers: Any, expected: str) -> bool:
    """Convenience wrapper: parse *expected* as a comma-separated key list and authorize."""
    return is_authorized_any(headers, parse_key_values(str(expected or "")))


def safe_client_ip(handler: Any, trust_x_forwarded_for: bool = False) -> str:
    """Extract the client IP from *handler*, validating it with :mod:`ipaddress`.

    When *trust_x_forwarded_for* is ``True``, the first entry in
    ``X-Forwarded-For`` is preferred (suitable behind a trusted reverse proxy).
    Returns ``"unknown"`` when no valid IP can be determined.
    """
    if trust_x_forwarded_for:
        forwarded = str(handler.headers.get("X-Forwarded-For", "") or "").strip()
        if forwarded:
            first = forwarded.split(",", 1)[0].strip()
            try:
                ipaddress.ip_address(first)
                return first
            except ValueError:
                pass
    remote = ""
    if getattr(handler, "client_address", None):
        remote = str(handler.client_address[0] or "").strip()
    if not remote:
        return "unknown"
    try:
        ipaddress.ip_address(remote)
        return remote
    except ValueError:
        return "unknown"


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter keyed by arbitrary strings (e.g. client IP).

    Tracks per-key hit timestamps in a :class:`~collections.deque` and evicts
    stale entries each call.  Automatically purges the oldest keys when the
    key count exceeds *max_keys* to bound memory usage.
    """

    def __init__(self, limit: int, window_seconds: int = 60, max_keys: int = 10000) -> None:
        """Initialise with *limit* hits per *window_seconds* per key."""
        self.limit = max(1, int(limit or 1))
        self.window_seconds = max(1, int(window_seconds or 60))
        self.max_keys = max(100, int(max_keys or 10000))
        self._lock = Lock()
        self._hits: dict[str, deque[float]] = {}

    def _purge_key(self, now: float, key: str) -> None:
        """Remove timestamps older than the sliding window for *key*."""
        bucket = self._hits.get(key)
        if not bucket:
            return
        floor = now - float(self.window_seconds)
        while bucket and bucket[0] < floor:
            bucket.popleft()
        if not bucket:
            self._hits.pop(key, None)

    def _purge_overflow(self, now: float) -> None:
        """Evict oldest keys when the map exceeds *max_keys* (memory bound)."""
        if len(self._hits) <= self.max_keys:
            return
        for key in list(self._hits.keys())[: max(1, len(self._hits) // 8)]:
            self._purge_key(now, key)
            if len(self._hits) <= self.max_keys:
                break

    def allow(self, key: str) -> tuple[bool, int]:
        """Check whether *key* is within the rate limit.

        Returns ``(True, 0)`` when allowed, or ``(False, retry_after_seconds)``
        when the limit has been exceeded.
        """
        token = str(key or "unknown")
        now = time.monotonic()
        with self._lock:
            self._purge_key(now, token)
            self._purge_overflow(now)
            bucket = self._hits.get(token)
            if bucket is None:
                if len(self._hits) >= self.max_keys:
                    return False, self.window_seconds
                bucket = deque()
                self._hits[token] = bucket

            if len(bucket) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
                return False, retry_after

            bucket.append(now)
            return True, 0


class SecurityEventLogger:
    """Append-only JSON-lines logger for security events (auth failures, rate-limit hits, etc.).

    Each event is written as a single JSON line with an auto-added ``ts`` field.
    Thread-safe via an internal lock.  No-ops silently when *path* is empty.
    """

    def __init__(self, path: str) -> None:
        """Create a logger writing to *path*.  Parent directories are auto-created."""
        self.path = str(path or "").strip()
        self._lock = Lock()
        if self.path:
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)

    def append(self, event: dict[str, object]) -> None:
        """Write *event* as a JSON line.  Adds ``ts`` (epoch seconds) if missing.

        Silently degrades to stderr on I/O failure so that logging never
        crashes the request handler.
        """
        if not self.path:
            return
        row = dict(event or {})
        row.setdefault("ts", int(time.time()))
        line = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        try:
            with self._lock:
                with open(self.path, "a", encoding="utf-8") as fp:
                    fp.write(line)
        except OSError:
            # Disk full, permissions, unmounted — degrade to stderr
            import sys
            print(f"[security_event_logger] write failed: {self.path}", file=sys.stderr)
