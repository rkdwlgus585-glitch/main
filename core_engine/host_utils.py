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


def sanitize_endpoint(url: str) -> str:
    """Sanitize a URL for safe embedding in HTML output.

    Allows only ``http(s)`` and relative paths.  Blocks ``javascript:``,
    ``data:``, loopback, link-local and unspecified addresses (SSRF defense).
    """
    src = str(url or "").strip()
    if not src:
        return ""
    lowered = src.lower()
    # Protocol whitelist — only http(s) and relative paths allowed
    if ":" in lowered.split("/")[0] and not (
        lowered.startswith("https:") or lowered.startswith("http:")
    ):
        return ""
    # Block loopback, link-local, and unspecified addresses (SSRF defense)
    if "localhost" in lowered or "127.0.0.1" in lowered or "::1" in lowered:
        return ""
    if "0.0.0.0" in lowered or "169.254." in lowered:
        return ""
    return src


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
