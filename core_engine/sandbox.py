"""Sandbox / demo mode responses for partner integration testing.

Partners can activate sandbox mode via:
    - ``X-Sandbox: true`` request header
    - API key prefixed with ``sandbox_``

Sandbox responses mirror the real API schema but contain static sample data
so partners can verify their integration without triggering real engine
computations or consuming usage quota.
"""
from __future__ import annotations

from typing import Any

from core_engine.api_response import now_iso

__all__ = ["is_sandbox_request", "sandbox_permit_response", "sandbox_yangdo_response"]


_PERMIT_SANDBOX_RESPONSE: dict[str, Any] = {
    "ok": True,
    "sandbox": True,
    "result": {
        "verdict": "conditional_pass",
        "service_code": "4111",
        "service_name": "토목건축공사업",
        "industry_name": "일반건설업",
        "rule_id": "sandbox-rule-4111",
        "criteria_summary": {
            "capital": {"required": "5억원 이상", "status": "pass", "detail": "입력 자본금 충족"},
            "technicians": {"required": "5인 이상", "status": "pass", "detail": "기술인력 기준 충족"},
            "office": {"required": "사무실 보유", "status": "manual_review", "detail": "현장 확인 필요"},
        },
        "overall_score": 85,
        "shortfall_items": [],
        "manual_review_items": ["사무실 보유 여부"],
        "recommendation": "등록기준 대부분 충족. 사무실 관련 서류 보완 후 신청 가능.",
        "confidence": "high",
    },
}

_YANGDO_SANDBOX_RESPONSE: dict[str, Any] = {
    "ok": True,
    "sandbox": True,
    "result": {
        "license_type": "토목건축공사업",
        "center_eok": 3.2,
        "range_low_eok": 2.5,
        "range_high_eok": 4.0,
        "confidence": 72,
        "confidence_label": "보통",
        "data_count": 15,
        "methodology": "AI 양도가 산정 (sandbox sample)",
        "factors": {
            "performance_trend": "상승",
            "capital_adequacy": "충분",
            "market_activity": "활발",
        },
        "neighbors": [
            {
                "rank": 1,
                "license": "토목건축공사업",
                "score": 92,
                "match_reason": "실적 규모 유사, 업종 일치",
            },
            {
                "rank": 2,
                "license": "토목건축공사업",
                "score": 85,
                "match_reason": "자본금 규모 유사",
            },
        ],
    },
}


def is_sandbox_request(
    headers: Any,
    api_key: str = "",
) -> bool:
    """Determine if the current request is a sandbox/demo request.

    Parameters
    ----------
    headers:
        HTTP headers object (must support ``.get()``).
    api_key:
        The API key used for the request, if any.

    Returns
    -------
    bool
        ``True`` if sandbox mode should be used.
    """
    if headers is not None:
        sandbox_hdr = str(getattr(headers, "get", lambda k, d="": d)("X-Sandbox", "") or "").strip().lower()
        if sandbox_hdr in {"true", "1", "yes"}:
            return True
    if api_key and str(api_key).startswith("sandbox_"):
        return True
    return False


def sandbox_permit_response() -> dict[str, Any]:
    """Return a static permit precheck response for sandbox mode."""
    resp = dict(_PERMIT_SANDBOX_RESPONSE)
    resp["timestamp"] = now_iso()
    resp["result"] = dict(resp["result"])  # shallow copy
    return resp


def sandbox_yangdo_response() -> dict[str, Any]:
    """Return a static yangdo estimate response for sandbox mode."""
    resp = dict(_YANGDO_SANDBOX_RESPONSE)
    resp["timestamp"] = now_iso()
    resp["result"] = dict(resp["result"])  # shallow copy
    return resp
