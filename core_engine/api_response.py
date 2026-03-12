from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from typing import Any

__all__ = ["now_iso", "safe_json_for_script", "build_response_envelope"]


def now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (seconds precision)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def safe_json_for_script(data: Any) -> str:
    """Serialize *data* to a JSON string safe for embedding in ``<script>``."""
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return (
        text.replace("</", "<\\/")
        .replace("<!--", "<\\!--")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _compact(value: Any, limit: int = 2000) -> str:
    """Normalise whitespace and truncate *value* to *limit* characters."""
    text = " ".join(("" if value is None else str(value)).split()).strip()
    if limit > 0 and len(text) > limit:
        return text[:limit].rstrip()
    return text


def build_response_envelope(
    payload: dict[str, Any] | None,
    *,
    service: str,
    api_version: str,
    request_id: str,
    channel_id: str = "",
    tenant_plan: str = "",
    response_tier: str = "",
) -> dict[str, Any]:
    """Wrap a business *payload* in a standard API response envelope.

    Attach ``response_meta`` (service, version, request_id, channel, plan,
    tier, status) and deep-copy the payload into a ``data`` key for data
    isolation.
    """
    business_payload = dict(payload or {})
    response_payload = dict(business_payload)
    ok = bool(response_payload.get("ok"))
    raw_policy = response_payload.get("response_policy")
    policy: dict[str, Any] = raw_policy if isinstance(raw_policy, dict) else {}
    resolved_tier = _compact(response_tier or policy.get("tier"), 40)
    resolved_plan = _compact(tenant_plan or policy.get("tenant_plan"), 60)
    resolved_channel = _compact(channel_id or response_payload.get("channel_id"), 80)

    response_payload.setdefault("service", str(service))
    response_payload.setdefault("api_version", str(api_version))
    response_payload.setdefault("request_id", str(request_id))
    if resolved_channel and "channel_id" not in response_payload:
        response_payload["channel_id"] = resolved_channel
    if "data" not in response_payload:
        response_payload["data"] = copy.deepcopy(business_payload)

    response_payload["response_meta"] = {
        "service": str(service),
        "api_version": str(api_version),
        "request_id": str(request_id),
        "channel_id": resolved_channel,
        "tenant_plan": resolved_plan,
        "response_tier": resolved_tier,
        "status": "ok" if ok else "error",
    }
    return response_payload
