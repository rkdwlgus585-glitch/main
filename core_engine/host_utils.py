from __future__ import annotations

from urllib.parse import urlparse


def normalize_host(raw: str) -> str:
    src = str(raw or "").strip().lower()
    if not src:
        return ""
    if "//" in src:
        parsed = urlparse(src)
        src = parsed.netloc.lower()
    if "@" in src:
        src = src.split("@", 1)[1]
    if ":" in src:
        src = src.split(":", 1)[0]
    return src.strip()


def host_from_origin(origin: str) -> str:
    src = str(origin or "").strip()
    if not src:
        return ""
    try:
        parsed = urlparse(src)
    except (ValueError, AttributeError):
        return ""
    return normalize_host(parsed.netloc)


def to_bool(value: object, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    src = str(value).strip().lower()
    if src in {"1", "true", "yes", "on", "y"}:
        return True
    if src in {"0", "false", "no", "off", "n"}:
        return False
    return default
