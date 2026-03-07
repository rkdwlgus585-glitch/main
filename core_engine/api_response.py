from __future__ import annotations

from typing import Any, Dict


def _compact(value: Any, limit: int = 2000) -> str:
    text = " ".join(str(value or "").split()).strip()
    if limit > 0 and len(text) > limit:
        return text[:limit].rstrip()
    return text


def build_response_envelope(
    payload: Dict[str, Any] | None,
    *,
    service: str,
    api_version: str,
    request_id: str,
    channel_id: str = "",
    tenant_plan: str = "",
    response_tier: str = "",
) -> Dict[str, Any]:
    business_payload = dict(payload or {})
    response_payload = dict(business_payload)
    ok = bool(response_payload.get("ok"))
    policy = response_payload.get("response_policy") if isinstance(response_payload.get("response_policy"), dict) else {}
    resolved_tier = _compact(response_tier or policy.get("tier"), 40)
    resolved_plan = _compact(tenant_plan or policy.get("tenant_plan"), 60)
    resolved_channel = _compact(channel_id or response_payload.get("channel_id"), 80)

    response_payload.setdefault("service", str(service))
    response_payload.setdefault("api_version", str(api_version))
    response_payload.setdefault("request_id", str(request_id))
    if resolved_channel and "channel_id" not in response_payload:
        response_payload["channel_id"] = resolved_channel
    if "data" not in response_payload:
        response_payload["data"] = dict(business_payload)

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
