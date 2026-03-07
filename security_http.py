import hmac
import ipaddress
import json
import os
import time
from collections import deque
from threading import Lock
from typing import Deque, Dict, Iterable, Optional, Sequence, Set, Tuple


DEFAULT_SECURITY_HEADERS: Tuple[Tuple[str, str], ...] = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Permissions-Policy", "geolocation=(), microphone=(), camera=()"),
    ("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"),
)


def parse_origin_allowlist(raw: str) -> Set[str]:
    out: Set[str] = set()
    for piece in str(raw or "").split(","):
        origin = str(piece or "").strip().rstrip("/")
        if not origin:
            continue
        if origin == "*":
            return {"*"}
        out.add(origin)
    return out


def resolve_allow_origin(request_origin: str, allowlist: Iterable[str]) -> str:
    origin = str(request_origin or "").strip().rstrip("/")
    allowed = set(allowlist or set())
    if not allowed:
        return ""
    if "*" in allowed:
        return origin or "*"
    if origin in allowed:
        return origin
    return ""


def header_token(headers, expected: str) -> str:
    if not expected:
        return ""
    auth = str(headers.get("Authorization", "") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return str(headers.get("X-API-Key", "") or "").strip()


def parse_key_values(raw: str) -> Tuple[str, ...]:
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


def is_authorized_any(headers, expected_values: Sequence[str]) -> bool:
    if not expected_values:
        return True
    candidate = header_token(headers, "x")
    if not candidate:
        return False
    for expected in expected_values:
        if expected and hmac.compare_digest(candidate, expected):
            return True
    return False


def is_authorized(headers, expected: str) -> bool:
    return is_authorized_any(headers, parse_key_values(str(expected or "")))


def safe_client_ip(handler, trust_x_forwarded_for: bool = False) -> str:
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
    def __init__(self, limit: int, window_seconds: int = 60, max_keys: int = 10000):
        self.limit = max(1, int(limit or 1))
        self.window_seconds = max(1, int(window_seconds or 60))
        self.max_keys = max(100, int(max_keys or 10000))
        self._lock = Lock()
        self._hits: Dict[str, Deque[float]] = {}

    def _purge_key(self, now: float, key: str) -> None:
        bucket = self._hits.get(key)
        if not bucket:
            return
        floor = now - float(self.window_seconds)
        while bucket and bucket[0] < floor:
            bucket.popleft()
        if not bucket:
            self._hits.pop(key, None)

    def _purge_overflow(self, now: float) -> None:
        if len(self._hits) <= self.max_keys:
            return
        for key in list(self._hits.keys())[: max(1, len(self._hits) // 8)]:
            self._purge_key(now, key)
            if len(self._hits) <= self.max_keys:
                break

    def allow(self, key: str) -> Tuple[bool, int]:
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
    def __init__(self, path: str):
        self.path = str(path or "").strip()
        self._lock = Lock()
        if self.path:
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)

    def append(self, event: Dict[str, object]) -> None:
        if not self.path:
            return
        row = dict(event or {})
        row.setdefault("ts", int(time.time()))
        line = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self._lock:
            with open(self.path, "a", encoding="utf-8") as fp:
                fp.write(line)
