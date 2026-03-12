from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import sqlite3
import statistics
from pathlib import Path
from typing import Any

from core_engine.api_response import now_iso
from core_engine.yangdo_duplicate_cluster import collapse_duplicate_neighbors
from core_engine.yangdo_listing_recommender import RecommendationOps, build_recommendation_bundle
from scripts.widget_health_contract import load_widget_health_contract

_BASE_PYC = Path(__file__).resolve().parent / "tmp" / "yangdo_blackbox_api_recovery.cpython-314.pyc"
if not _BASE_PYC.exists():
    raise ImportError(f"Recovery bytecode not found: {_BASE_PYC}")

_LOADER = importlib.machinery.SourcelessFileLoader("_yangdo_blackbox_api_recovery", str(_BASE_PYC))
_SPEC = importlib.util.spec_from_loader(_LOADER.name, _LOADER)
if _SPEC is None:
    raise ImportError(f"Unable to create spec for {_BASE_PYC}")

_BASE = importlib.util.module_from_spec(_SPEC)
_LOADER.exec_module(_BASE)

SERVICE_NAME = "yangdo_blackbox_api"
_SERVER_STARTED_AT: str = now_iso()

for _name, _value in vars(_BASE).items():
    if _name in {"__name__", "__file__", "__package__", "__loader__", "__spec__", "__cached__"}:
        continue
    globals()[_name] = _value

core = _BASE.core
_compact = _BASE._compact
_to_float = _BASE._to_float
_relative_closeness = _BASE._relative_closeness
_sales_fit_score = _BASE._sales_fit_score
_yearly_shape_similarity = _BASE._yearly_shape_similarity
_derive_display_range_eok = _BASE._derive_display_range_eok
_listing_number_band = _BASE._listing_number_band
_token_containment = _BASE._token_containment

# ── Output field truncation limits (chars) ───────────────────────────
_LIM_CHANNEL_ID: int = 80
_LIM_TENANT_PLAN: int = 60
_LIM_LICENSE_TEXT: int = 120
_LIM_REC_LABEL: int = 40
_LIM_REC_FOCUS: int = 80
_LIM_PRECISION_TIER: int = 20
_LIM_FIT_SUMMARY: int = 180
_LIM_URL: int = 260

# ── Publication safety thresholds (ICT sector) ──────────────────────
_PUB_SPAN_RATIO_MAX: float = 0.70
_PUB_CENTER_AMOUNT_MIN: float = 0.25
_PUB_CONFIDENCE_MIN: float = 90.0

_SPECIAL_BALANCE_LOAN_UTILIZATION = 0.60
_SPECIAL_SETTLEMENT_SCENARIO_INPUT_MODES: tuple[str, ...] = ("auto", "credit_transfer", "none")
_FIRE_GUARDED_PRIOR_BLEND = 0.55
_FIRE_GUARDED_PRIOR_CAP_QUANTILE = 0.60
_FIRE_GUARDED_PRIOR_CAP_MULT = 1.02
_FIRE_GUARDED_PRIOR_CURRENT_CAP = 1.60
_FIRE_GUARDED_PRIOR_Q25_FLOOR = 0.90
_SPECIAL_BALANCE_AUTO_POLICIES: dict[str, dict[str, Any]] = {
    "전기": {
        "sector": "전기",
        "auto_mode": "loan_withdrawal",
        "loan_utilization": _SPECIAL_BALANCE_LOAN_UTILIZATION,
        "min_auto_balance_share": 0.10,
        "min_auto_balance_eok": 0.05,
        "summary": "전기 업종은 총 거래가와 공제조합 정산을 분리해 보고, 기본값은 조합 융자 인출 후 현금 차감입니다.",
        "reorg_overrides": {
            "분할/합병": {
                "min_auto_balance_share": 0.105,
                "min_auto_balance_eok": 0.05,
            },
        },
    },
    "정보통신": {
        "sector": "정보통신",
        "auto_mode": "loan_withdrawal",
        "loan_utilization": _SPECIAL_BALANCE_LOAN_UTILIZATION,
        "min_auto_balance_share": 0.0625,
        "min_auto_balance_eok": 0.025,
        "summary": "정보통신 업종은 총 거래가와 공제조합 정산을 분리해 보고, 기본값은 조합 융자 인출 후 현금 차감입니다.",
        "reorg_overrides": {
            "분할/합병": {
                "min_auto_balance_share": 0.065,
                "min_auto_balance_eok": 0.025,
            },
        },
    },
    "소방": {
        "sector": "소방",
        "auto_mode": "loan_withdrawal",
        "loan_utilization": _SPECIAL_BALANCE_LOAN_UTILIZATION,
        "min_auto_balance_share": 0.17,
        "min_auto_balance_eok": 0.09,
        "summary": "소방 업종은 총 거래가와 공제조합 정산을 분리해 보고, 기본값은 조합 융자 인출 후 현금 차감입니다.",
        "reorg_overrides": {
            "분할/합병": {
                "min_auto_balance_share": 0.1758,
                "min_auto_balance_eok": 0.09,
            },
        },
    },
}


def _partner_health_payload() -> dict[str, Any]:
    return {
        "ok": True,
        "service": SERVICE_NAME,
        "started_at": _SERVER_STARTED_AT,
        "message": "healthy",
        "health_contract": load_widget_health_contract(),
    }


def _write_partner_health_json(handler: Any, status: int = 200) -> None:
    request_id = ""
    try:
        request_id = str(handler._request_id() or "")
    except (AttributeError, TypeError, ValueError):
        request_id = ""
    if not request_id:
        request_id = "health"
    try:
        channel_id = _compact(_channel_id_value(handler._channel_resolution()), _LIM_CHANNEL_ID)
    except (AttributeError, TypeError, ValueError, KeyError):
        channel_id = ""
    try:
        tenant_plan = _compact(_tenant_plan_key(handler._tenant_resolution()), _LIM_TENANT_PLAN)
    except (AttributeError, TypeError, ValueError, KeyError):
        tenant_plan = ""
    response_payload = build_response_envelope(
        _partner_health_payload(),
        service=SERVICE_NAME,
        api_version="v1",
        request_id=request_id,
        channel_id=channel_id,
        tenant_plan=tenant_plan,
        response_tier="health",
    )
    body = json.dumps(response_payload, ensure_ascii=False).encode("utf-8")
    allow_origin = ""
    try:
        allow_origin = str(handler._allow_origin() or "")
    except (AttributeError, TypeError, ValueError):
        allow_origin = ""
    handler.send_response(int(status))
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Api-Version", "v1")
    handler.send_header("X-Service-Name", SERVICE_NAME)
    handler.send_header("X-Request-Id", request_id)
    handler.send_header("X-Response-Tier", "health")
    try:
        for hk, hv in handler._channel_headers().items():
            handler.send_header(str(hk), str(hv))
    except (AttributeError, TypeError, ValueError, KeyError):
        pass
    for hk, hv in DEFAULT_SECURITY_HEADERS:
        handler.send_header(hk, hv)
    if allow_origin:
        handler.send_header("Access-Control-Allow-Origin", allow_origin)
        handler.send_header("Vary", "Origin")
        handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Key, X-Request-Id, X-Correlation-Id, X-Channel-Id")
        handler.send_header("Access-Control-Expose-Headers", "X-Request-Id")
    handler.end_headers()
    try:
        handler.wfile.write(body)
    except OSError:
        pass


def _round4(value: Any) -> float | None:
    num = _to_float(value)
    if num is None:
        return None
    return float(core._round4(float(num)))


def _plain_quantile(values: list[float], q: float) -> float:
    seq = sorted(float(v) for v in values if _to_float(v) is not None)
    if not seq:
        return 0.0
    if len(seq) == 1:
        return seq[0]
    idx = (len(seq) - 1) * max(0.0, min(1.0, q))
    lo = int(idx)
    hi = min(len(seq) - 1, lo + 1)
    frac = idx - lo
    return (seq[lo] * (1.0 - frac)) + (seq[hi] * frac)


def _trimmed_plain_median(values: list[float], lower_q: float = 0.20, upper_q: float = 0.80) -> float:
    seq = sorted(float(v) for v in values if _to_float(v) is not None)
    if not seq:
        return 0.0
    lo = _plain_quantile(seq, lower_q)
    hi = _plain_quantile(seq, upper_q)
    trimmed = [value for value in seq if lo <= value <= hi]
    return float(statistics.median(trimmed or seq))


def _sector_signal_value(source: dict[str, Any] | None) -> float | None:
    source = dict(source or {})
    sales3 = _to_float(source.get("sales3_eok"))
    specialty = _to_float(source.get("specialty"))
    if sales3 is not None and specialty is not None:
        return (0.65 * float(sales3)) + (0.35 * float(specialty))
    if sales3 is not None:
        return float(sales3)
    if specialty is not None:
        return float(specialty)
    return None


def _single_license_special_sector_rows(records: list[dict[str, Any]], sector_name: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in list(records or []):
        token_list = list(row.get("license_tokens") or [])
        token_set = {str(token or "").strip() for token in token_list if str(token or "").strip()}
        if len(token_set) != 1:
            continue
        if _special_balance_sector_name(token_set or row.get("license_text")) != sector_name:
            continue
        price = _to_float(row.get("current_price_eok"))
        if price is None or price <= 0:
            continue
        out.append(row)
    return out


def _maybe_apply_fire_single_license_guarded_prior(
    *,
    records: list[dict[str, Any]],
    target: dict[str, Any],
    total: float,
    low: float,
    high: float,
    public_total: float | None,
    public_low: float | None,
    public_high: float | None,
) -> dict[str, Any] | None:
    target_tokens = {str(token or "").strip() for token in list(target.get("license_tokens") or []) if str(token or "").strip()}
    if len(target_tokens) != 1:
        return None
    if _special_balance_sector_name(target.get("license_text") or target_tokens) != "소방":
        return None
    current_total = float(_to_float(total) or 0.0)
    if current_total <= 0:
        return None
    target_signal = _sector_signal_value(target)
    if target_signal is None or target_signal <= 0:
        return None
    sector_rows = _single_license_special_sector_rows(records, "소방")
    prices = [float(_to_float(row.get("current_price_eok")) or 0.0) for row in sector_rows if (_to_float(row.get("current_price_eok")) or 0.0) > 0]
    if len(prices) < 8:
        return None
    ratio_samples: list[float] = []
    for row in sector_rows:
        price = _to_float(row.get("current_price_eok"))
        signal = _sector_signal_value(row)
        if price is None or price <= 0 or signal is None or signal <= 0:
            continue
        ratio_samples.append(float(price) / float(signal))
    if len(ratio_samples) < 6:
        return None
    prior_estimate = float(target_signal) * _trimmed_plain_median(ratio_samples)
    q25 = _plain_quantile(prices, 0.25)
    q60 = _plain_quantile(prices, _FIRE_GUARDED_PRIOR_CAP_QUANTILE)
    candidate = current_total + (_FIRE_GUARDED_PRIOR_BLEND * max(0.0, prior_estimate - current_total))
    floor_value = max(current_total, q25 * _FIRE_GUARDED_PRIOR_Q25_FLOOR)
    cap_value = min(q60 * _FIRE_GUARDED_PRIOR_CAP_MULT, current_total * _FIRE_GUARDED_PRIOR_CURRENT_CAP)
    adjusted_total = max(floor_value, min(candidate, cap_value))
    if adjusted_total <= current_total + 0.0005:
        return None
    delta = adjusted_total - current_total
    low_gap = max(0.0, current_total - float(_to_float(low) or current_total))
    high_gap = max(0.0, float(_to_float(high) or current_total) - current_total)
    public_center = float(_to_float(public_total) or current_total)
    public_low_value = float(_to_float(public_low) or float(_to_float(low) or current_total))
    public_high_value = float(_to_float(public_high) or float(_to_float(high) or current_total))
    public_low_gap = max(0.0, public_center - public_low_value)
    public_high_gap = max(0.0, public_high_value - public_center)
    return {
        "mode": "fire_single_license_guarded_prior",
        "reason": "소방 단일면허는 same-sector bounded prior를 제한 반영해 none-mode 과소평가를 줄였습니다.",
        "support_count": len(prices),
        "prior_estimate_eok": _round4(prior_estimate),
        "adjusted_total_transfer_value_eok": _round4(adjusted_total),
        "adjusted_low_eok": _round4(max(0.05, adjusted_total - low_gap)),
        "adjusted_high_eok": _round4(max(adjusted_total - low_gap, adjusted_total + high_gap)),
        "adjusted_public_total_transfer_value_eok": _round4(public_center + delta),
        "adjusted_public_low_eok": _round4(max(0.05, (public_center + delta) - public_low_gap)),
        "adjusted_public_high_eok": _round4(max((public_center + delta) - public_low_gap, (public_center + delta) + public_high_gap)),
    }



def _normalize_license_text(raw: Any) -> str:
    return _compact(raw)



def _license_text_parts(raw: Any) -> list[str]:
    parts: list[str] = []
    if isinstance(raw, dict):
        parts.append(_compact(raw.get("license_text")))
        parts.append(_compact(raw.get("raw_license_key")))
        for token in list(raw.get("license_tokens") or []):
            parts.append(_compact(token))
    elif isinstance(raw, (list, tuple, set)):
        for item in raw:
            parts.append(_compact(item))
    else:
        parts.append(_compact(raw))
    return [part for part in parts if part]



def _special_balance_sector_name(raw: Any) -> str:
    key = " ".join(_license_text_parts(raw)).replace(" ", "")
    if not key:
        return ""
    if "정보통신" in key or "통신" in key:
        return "정보통신"
    if "소방" in key:
        return "소방"
    if "전기" in key:
        return "전기"
    return ""



def _is_special_license_text(raw: Any) -> bool:
    return bool(_special_balance_sector_name(raw))



def _normalize_reorg_mode(raw: Any) -> str:
    txt = _compact(raw).replace(" ", "")
    if not txt:
        return ""
    lowered = txt.lower()
    has_split_merge = any(token in txt for token in ("분할", "합병")) or any(token in lowered for token in ("split", "merge"))
    has_comprehensive = any(token in txt for token in ("포괄", "흡수")) or "comprehensive" in lowered
    if has_split_merge and has_comprehensive:
        return ""
    if has_split_merge:
        return "분할/합병"
    if has_comprehensive:
        return "포괄"
    return txt



def _normalize_balance_usage_mode(raw: Any) -> str:
    txt = _compact(raw).lower().replace(" ", "")
    if not txt:
        return ""
    if txt in {"auto", "자동", "default"}:
        return "auto"
    if any(token in txt for token in ("융자인출", "융자", "대출", "loan", "withdraw")):
        return "loan_withdrawal"
    if any(token in txt for token in ("잔액승계", "잔액인수", "credit", "offset", "1:1", "차감")):
        return "credit_transfer"
    if txt in {"none", "없음", "미반영", "별도정산없음"}:
        return "none"
    return ""



def _normalize_credit_level(raw: Any) -> str:
    txt = _compact(raw).lower().replace(" ", "")
    if not txt:
        return ""
    if any(token in txt for token in ("최상", "우수", "높음", "high", "a+", "aa", "aaa")):
        return "high"
    if any(token in txt for token in ("낮음", "저조", "불량", "low", "ccc", "cc")):
        return "low"
    if any(token in txt for token in ("보통", "중간", "medium", "bb", "bbb", "mid")):
        return "medium"
    return txt



def _normalize_admin_history(raw: Any) -> str:
    txt = _compact(raw).lower().replace(" ", "")
    if not txt:
        return ""
    if any(token in txt for token in ("없음", "none", "clean", "무행정", "무처분")):
        return "none"
    if any(token in txt for token in ("있음", "has", "행정", "처분", "제재", "벌점", "경고")):
        return "has"
    return txt



def _get_special_balance_auto_policy(*, license_text: Any, reorg_mode: Any) -> dict[str, Any]:
    sector = _special_balance_sector_name(license_text)
    normalized_reorg = _normalize_reorg_mode(reorg_mode)
    base = dict(_SPECIAL_BALANCE_AUTO_POLICIES.get(sector) or {})
    reorg_overrides = base.pop("reorg_overrides", {})
    if normalized_reorg and isinstance(reorg_overrides, dict):
        override = reorg_overrides.get(normalized_reorg)
        if isinstance(override, dict):
            base.update(override)
    auto_mode = _compact(base.get("auto_mode") or "loan_withdrawal")
    loan_utilization = float(_to_float(base.get("loan_utilization")) or _SPECIAL_BALANCE_LOAN_UTILIZATION)
    min_auto_balance_share = _to_float(base.get("min_auto_balance_share"))
    if min_auto_balance_share is None:
        min_auto_balance_share = 0.05
    min_auto_balance_eok = _to_float(base.get("min_auto_balance_eok"))
    if min_auto_balance_eok is None:
        min_auto_balance_eok = 0.0
    summary = _compact(base.get("summary"))
    if sector and normalized_reorg == "분할/합병":
        summary = f"{sector} 분할/합병: 총가·공제 정산 분리"
    elif sector:
        summary = f"{sector}: 총가·공제 정산 분리"
    return {
        "sector": sector,
        "reorg_mode": normalized_reorg,
        "auto_mode": auto_mode if sector else "none",
        "loan_utilization": loan_utilization if sector else 0.0,
        "min_auto_balance_share": min_auto_balance_share if sector else 0.0,
        "min_auto_balance_eok": min_auto_balance_eok if sector else 0.0,
        "summary": summary if sector else "",
    }



def _resolve_special_auto_mode(*, policy: dict[str, Any] | None, total_transfer_value_eok: float, raw_balance_input_eok: float) -> dict[str, Any]:
    sector = _compact((policy or {}).get("sector"))
    base_mode = _compact((policy or {}).get("auto_mode") or "loan_withdrawal")
    total = max(0.05, float(_to_float(total_transfer_value_eok) or 0.0))
    raw_balance = max(0.0, float(_to_float(raw_balance_input_eok) or 0.0))
    share = raw_balance / total if total > 0 else 0.0
    min_share = max(0.0, float(_to_float((policy or {}).get("min_auto_balance_share")) or 0.05))
    min_balance = max(0.0, float(_to_float((policy or {}).get("min_auto_balance_eok")) or 0.0))
    reason = _compact((policy or {}).get("summary")) or "총가와 공제 정산을 분리합니다."
    if raw_balance <= 0:
        return {
            "mode": "none",
            "reason": "잔액 입력 없음 -> auto=별도 정산 없음",
            "balance_share": _round4(share),
        }
    if raw_balance <= min_balance or share <= min_share:
        return {
            "mode": "none",
            "reason": "잔액 비중 작음 -> auto=별도 정산 없음",
            "balance_share": _round4(share),
        }
    return {
        "mode": base_mode,
        "reason": f"잔액 비중 충분 -> auto={_settlement_input_mode_label(base_mode)}" if sector else reason,
        "balance_share": _round4(share),
    }



def _resolve_balance_usage_mode(
    *,
    requested_mode: Any,
    seller_withdraws_guarantee_loan: bool,
    buyer_takes_balance_as_credit: bool,
    balance_excluded: bool,
    license_text: Any = "",
    reorg_mode: Any = "",
) -> str:
    normalized = _normalize_balance_usage_mode(requested_mode)
    if normalized and normalized != "auto":
        return normalized
    if buyer_takes_balance_as_credit:
        return "credit_transfer"
    if seller_withdraws_guarantee_loan:
        return "loan_withdrawal"
    if balance_excluded:
        policy = _get_special_balance_auto_policy(license_text=license_text, reorg_mode=reorg_mode)
        return _compact(policy.get("auto_mode") or "loan_withdrawal")
    return "embedded_balance"



def _settlement_mode_label(mode_raw: Any) -> str:
    requested = _normalize_balance_usage_mode(mode_raw)
    raw = _compact(mode_raw)
    if not requested and raw == "embedded_balance":
        return "총 거래가에 반영된 잔액 기여분 분리"
    if not requested or requested == "auto":
        return "기본값(시장 관행 기준)"
    mode = _resolve_balance_usage_mode(
        requested_mode=requested,
        seller_withdraws_guarantee_loan=False,
        buyer_takes_balance_as_credit=False,
        balance_excluded=False,
    )
    if mode == "loan_withdrawal":
        return "양도자 조합 융자 인출 후 현금 차감"
    if mode == "credit_transfer":
        return "양수자 공제잔액 인수 1:1 차감"
    if mode == "embedded_balance":
        return "총 거래가에 반영된 잔액 기여분 분리"
    if mode == "none":
        return "공제조합 잔액 별도 정산 없음"
    return "기본값(시장 관행 기준)"



def _settlement_input_mode_label(mode_raw: Any) -> str:
    mode = _normalize_balance_usage_mode(mode_raw)
    if mode == "credit_transfer":
        return "공제잔액 1:1 차감"
    if mode == "none":
        return "별도 정산 없음"
    if mode == "loan_withdrawal":
        return "융자 인출 후 현금 차감"
    return "기본값(시장 관행 기준)"



def _build_single_settlement_view(
    *,
    total_transfer_value_eok: float,
    total_low_eok: float,
    total_high_eok: float,
    public_total_transfer_value_eok: float | None,
    public_total_low_eok: float | None,
    public_total_high_eok: float | None,
    raw_balance_input_eok: float | None,
    balance_excluded: bool,
    resolved_mode: str,
    effective_balance_rate: float | None,
    special_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    total = max(0.05, float(_to_float(total_transfer_value_eok) or 0.0))
    low = max(0.05, float(_to_float(total_low_eok) or total))
    high = max(low, float(_to_float(total_high_eok) or total))
    public_total = max(0.05, float(_to_float(public_total_transfer_value_eok) or total))
    public_low = max(0.05, float(_to_float(public_total_low_eok) or low))
    public_high = max(public_low, float(_to_float(public_total_high_eok) or high))
    raw_balance = max(0.0, float(_to_float(raw_balance_input_eok) or 0.0))
    mode = _normalize_balance_usage_mode(resolved_mode) or _compact(resolved_mode) or "embedded_balance"
    loan_utilization = float(_to_float((special_policy or {}).get("loan_utilization")) or _SPECIAL_BALANCE_LOAN_UTILIZATION)
    embedded_rate = max(0.0, min(1.0, float(_to_float(effective_balance_rate) or 0.0)))
    realizable_rate = 0.0
    notes: list[str] = []
    if mode == "credit_transfer":
        realizable_rate = 1.0 if raw_balance > 0 else 0.0
        notes.append("1:1 차감 기준")
    elif mode == "loan_withdrawal":
        realizable_rate = loan_utilization if raw_balance > 0 else 0.0
        notes.append("융자 인출 후 현금 차감")
    elif mode == "none":
        realizable_rate = 0.0
        notes.append("별도 정산 없음")
    else:
        mode = "embedded_balance"
        realizable_rate = embedded_rate if raw_balance > 0 else 0.0
        notes.append("총가 반영 잔액 분리")
    realizable_balance = raw_balance * realizable_rate
    cash_due = max(0.05, total - realizable_balance)
    cash_low = max(0.05, low - realizable_balance)
    cash_high = max(cash_low, high - realizable_balance)
    public_cash_due = max(0.05, public_total - realizable_balance)
    public_cash_low = max(0.05, public_low - realizable_balance)
    public_cash_high = max(public_cash_low, public_high - realizable_balance)
    return {
        "mode": mode,
        "mode_label": _settlement_mode_label(mode),
        "raw_balance_input_eok": _round4(raw_balance),
        "realizable_balance_rate": _round4(realizable_rate),
        "realizable_balance_eok": _round4(realizable_balance),
        "total_transfer_value_eok": _round4(total),
        "total_transfer_low_eok": _round4(low),
        "total_transfer_high_eok": _round4(high),
        "estimated_cash_due_eok": _round4(cash_due),
        "estimated_cash_due_low_eok": _round4(cash_low),
        "estimated_cash_due_high_eok": _round4(cash_high),
        "public_estimated_cash_due_eok": _round4(public_cash_due),
        "public_estimated_cash_due_low_eok": _round4(public_cash_low),
        "public_estimated_cash_due_high_eok": _round4(public_cash_high),
        "notes": notes,
    }



def _build_settlement_output(
    *,
    total_transfer_value_eok: float,
    total_low_eok: float,
    total_high_eok: float,
    public_total_transfer_value_eok: float | None,
    public_total_low_eok: float | None,
    public_total_high_eok: float | None,
    raw_balance_input_eok: float | None,
    balance_excluded: bool,
    balance_usage_mode: str,
    effective_balance_rate: float | None,
    split_optional_pricing: bool,
    license_text: Any = "",
    reorg_mode: Any = "",
    requested_balance_usage_mode: Any = "",
) -> dict[str, Any]:
    policy = _get_special_balance_auto_policy(license_text=license_text, reorg_mode=reorg_mode)
    requested_mode_normalized = _normalize_balance_usage_mode(requested_balance_usage_mode)
    mode = _resolve_balance_usage_mode(
        requested_mode=requested_mode_normalized or balance_usage_mode,
        seller_withdraws_guarantee_loan=False,
        buyer_takes_balance_as_credit=False,
        balance_excluded=balance_excluded,
        license_text=license_text,
        reorg_mode=reorg_mode,
    )
    internal_total = max(0.05, float(_to_float(total_transfer_value_eok) or 0.0))
    balance_input = max(0.0, float(_to_float(raw_balance_input_eok) or 0.0))
    auto_decision = (
        _resolve_special_auto_mode(
            policy=policy,
            total_transfer_value_eok=internal_total,
            raw_balance_input_eok=balance_input,
        )
        if balance_excluded
        else {
            "mode": mode,
            "reason": _compact(policy.get("summary")),
            "balance_share": _round4(balance_input / max(0.05, internal_total)),
        }
    )
    if balance_excluded and (not requested_mode_normalized or requested_mode_normalized == "auto"):
        mode = _compact(auto_decision.get("mode") or mode)
    primary = _build_single_settlement_view(
        total_transfer_value_eok=total_transfer_value_eok,
        total_low_eok=total_low_eok,
        total_high_eok=total_high_eok,
        public_total_transfer_value_eok=public_total_transfer_value_eok,
        public_total_low_eok=public_total_low_eok,
        public_total_high_eok=public_total_high_eok,
        raw_balance_input_eok=raw_balance_input_eok,
        balance_excluded=balance_excluded,
        resolved_mode=mode,
        effective_balance_rate=effective_balance_rate,
        special_policy=policy if balance_excluded else None,
    )
    out: dict[str, Any] = {
        "balance_usage_mode": primary.get("mode"),
        "balance_usage_mode_requested": requested_mode_normalized,
        "raw_balance_input_eok": primary.get("raw_balance_input_eok"),
        "balance_reference_eok": primary.get("raw_balance_input_eok"),
        "realizable_balance_rate": primary.get("realizable_balance_rate"),
        "realizable_balance_eok": primary.get("realizable_balance_eok"),
        "total_transfer_value_eok": primary.get("total_transfer_value_eok"),
        "total_transfer_low_eok": primary.get("total_transfer_low_eok"),
        "total_transfer_high_eok": primary.get("total_transfer_high_eok"),
        "estimated_cash_due_eok": primary.get("estimated_cash_due_eok"),
        "estimated_cash_due_low_eok": primary.get("estimated_cash_due_low_eok"),
        "estimated_cash_due_high_eok": primary.get("estimated_cash_due_high_eok"),
        "public_estimated_cash_due_eok": primary.get("public_estimated_cash_due_eok"),
        "public_estimated_cash_due_low_eok": primary.get("public_estimated_cash_due_low_eok"),
        "public_estimated_cash_due_high_eok": primary.get("public_estimated_cash_due_high_eok"),
        "settlement_policy": {
            "sector": _compact(policy.get("sector")),
            "reorg_mode": _compact(policy.get("reorg_mode")),
            "auto_mode": _compact(policy.get("auto_mode")),
            "auto_mode_label": _settlement_mode_label(policy.get("auto_mode")),
            "resolved_auto_mode": _compact(auto_decision.get("mode")),
            "resolved_auto_mode_label": _settlement_mode_label(auto_decision.get("mode")),
            "auto_decision_reason": _compact(auto_decision.get("reason")),
            "balance_share_of_total": _round4(auto_decision.get("balance_share")),
            "loan_utilization": _round4(policy.get("loan_utilization")),
            "min_auto_balance_share": _round4(policy.get("min_auto_balance_share")),
            "min_auto_balance_eok": _round4(policy.get("min_auto_balance_eok")),
            "summary": _compact(policy.get("summary")),
        },
        "settlement_scenarios": [],
        "settlement_breakdown": {
            "model": primary.get("mode"),
            "model_label": primary.get("mode_label"),
            "balance_excluded_from_total": bool(balance_excluded),
            "split_optional_pricing": bool(split_optional_pricing),
            "raw_balance_input_eok": primary.get("raw_balance_input_eok"),
            "realizable_balance_rate": primary.get("realizable_balance_rate"),
            "realizable_balance_eok": primary.get("realizable_balance_eok"),
            "buyer_cash_due_eok": primary.get("estimated_cash_due_eok"),
            "buyer_cash_due_low_eok": primary.get("estimated_cash_due_low_eok"),
            "buyer_cash_due_high_eok": primary.get("estimated_cash_due_high_eok"),
            "notes": list(primary.get("notes") or []),
            "policy": {},
        },
    }
    out["settlement_breakdown"]["policy"] = dict(out["settlement_policy"])
    if balance_excluded and balance_input > 0:
        rows: list[dict[str, Any]] = []
        for idx, input_mode in enumerate(_SPECIAL_SETTLEMENT_SCENARIO_INPUT_MODES):
            resolved_mode = (
                _compact(auto_decision.get("mode") or mode)
                if input_mode == "auto"
                else _resolve_balance_usage_mode(
                    requested_mode=input_mode,
                    seller_withdraws_guarantee_loan=False,
                    buyer_takes_balance_as_credit=False,
                    balance_excluded=True,
                    license_text=license_text,
                    reorg_mode=reorg_mode,
                )
            )
            row = _build_single_settlement_view(
                total_transfer_value_eok=total_transfer_value_eok,
                total_low_eok=total_low_eok,
                total_high_eok=total_high_eok,
                public_total_transfer_value_eok=public_total_transfer_value_eok,
                public_total_low_eok=public_total_low_eok,
                public_total_high_eok=public_total_high_eok,
                raw_balance_input_eok=raw_balance_input_eok,
                balance_excluded=True,
                resolved_mode=resolved_mode,
                effective_balance_rate=effective_balance_rate,
                special_policy=policy,
            )
            if input_mode == "auto":
                selected = (not requested_mode_normalized or requested_mode_normalized == "auto") and _compact(row.get("mode")) == _compact(auto_decision.get("mode") or mode)
            else:
                selected = bool(requested_mode_normalized and requested_mode_normalized != "auto" and _compact(row.get("mode")) == _compact(mode))
            rows.append(
                {
                    "scenario_index": idx,
                    "input_mode": input_mode,
                    "label": "기본값(시장 관행 기준)" if input_mode == "auto" else _settlement_mode_label(input_mode),
                    "resolved_mode": row.get("mode"),
                    "resolved_mode_label": row.get("mode_label"),
                    "is_recommended": input_mode == "auto",
                    "is_selected": selected,
                    "realizable_balance_rate": row.get("realizable_balance_rate"),
                    "realizable_balance_eok": row.get("realizable_balance_eok"),
                    "estimated_cash_due_eok": row.get("estimated_cash_due_eok"),
                    "estimated_cash_due_low_eok": row.get("estimated_cash_due_low_eok"),
                    "estimated_cash_due_high_eok": row.get("estimated_cash_due_high_eok"),
                    "public_estimated_cash_due_eok": row.get("public_estimated_cash_due_eok"),
                    "public_estimated_cash_due_low_eok": row.get("public_estimated_cash_due_low_eok"),
                    "public_estimated_cash_due_high_eok": row.get("public_estimated_cash_due_high_eok"),
                    "notes": list(row.get("notes") or []),
                }
            )
        out["settlement_scenarios"] = rows
    return out



def _tenant_plan_key(resolution: Any) -> str:
    tenant = getattr(resolution, "tenant", None)
    if tenant is None:
        return ""
    return _compact(getattr(tenant, "plan", "")).lower()



def _tenant_id_value(resolution: Any) -> str:
    tenant = getattr(resolution, "tenant", None)
    if tenant is None:
        return ""
    return _compact(getattr(tenant, "tenant_id", ""))



def _tenant_has_feature(server: Any, resolution: Any, feature: str) -> bool:
    if not bool(getattr(server, "tenant_gateway_enabled", False)):
        return True
    return bool(server.tenant_gateway.check_feature(resolution, feature))



def _estimate_response_tier(server: Any, resolution: Any) -> str:
    if not bool(getattr(server, "tenant_gateway_enabled", False)):
        return "internal"
    if _tenant_has_feature(server, resolution, "estimate_internal"):
        return "internal"
    if _tenant_has_feature(server, resolution, "estimate_detail"):
        return "detail"
    plan = _tenant_plan_key(resolution)
    if plan == "pro_internal":
        return "internal"
    if plan == "pro":
        return "detail"
    return "summary"



def _range_pair_from_record(rec: dict[str, Any]) -> tuple[float | None, float | None]:
    low = _to_float(rec.get("display_low_eok"))
    high = _to_float(rec.get("display_high_eok"))
    current_price = _to_float(rec.get("current_price_eok"))
    claim_price = _to_float(rec.get("claim_price_eok"))
    if low is None and high is None:
        derived_low, derived_high = _derive_display_range_eok(
            rec.get("current_price_text"),
            rec.get("claim_price_text"),
            current_price,
            claim_price,
        )
        low = _to_float(derived_low)
        high = _to_float(derived_high)
    if low is None and high is None:
        center = current_price
        if center is None:
            center = _to_float(rec.get("price_eok"))
        return center, center
    if low is None:
        low = high
    if high is None:
        high = low
    if low is not None and high is not None and high < low:
        low, high = high, low
    return low, high



def _prioritize_display_neighbors(target: dict[str, Any], rows: list[tuple[float, dict[str, Any]]]) -> list[tuple[float, dict[str, Any]]]:
    if not rows:
        return []
    ranked: list[tuple[int, int, float, float, float, dict[str, Any]]] = []
    target_has_sales = any((_to_float(target.get(field)) or 0.0) > 0.0 for field in ("sales3_eok", "sales5_eok"))
    for sim, rec in rows:
        rec_obj = rec if isinstance(rec, dict) else {}
        sales_fit = _sales_fit_score(target, rec_obj)
        band = _listing_number_band(rec_obj.get("number"))
        rec_has_sales = any((_to_float(rec_obj.get(field)) or 0.0) > 0.0 for field in ("sales3_eok", "sales5_eok"))
        similar_sales = 1 if (
            sales_fit >= 0.62
            or ((not target_has_sales or not rec_has_sales) and float(_to_float(sim) or 0.0) >= 94.0)
        ) else 0
        ranked.append((similar_sales, band, float(_to_float(sim) or 0.0), sales_fit, float(_to_float(rec_obj.get("number")) or 0.0), rec_obj))
    ranked.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4]), reverse=True)
    return [(entry[2], entry[5]) for entry in ranked]



def _recommendation_ops() -> RecommendationOps:
    estimator_cls = YangdoBlackboxEstimator
    return RecommendationOps(
        canonical_tokens=estimator_cls._canonical_tokens,
        single_token_target_core=estimator_cls._single_token_target_core,
        is_single_token_same_core=estimator_cls._is_single_token_same_core,
        company_type_key=estimator_cls._company_type_key,
        feature_scale_mismatch=estimator_cls._feature_scale_mismatch,
        token_containment=_token_containment,
        relative_closeness=_relative_closeness,
        sales_fit_score=_sales_fit_score,
        yearly_shape_similarity=_yearly_shape_similarity,
        derive_display_range_eok=_derive_display_range_eok,
        listing_number_band=_listing_number_band,
        to_float=_to_float,
        compact=_compact,
        round4=core._round4,
        site_url=str(core.SITE_URL),
    )



def _build_recommendation_result(*, target: dict[str, Any], rows: list[tuple[float, dict[str, Any]]], center: Any, low: Any, high: Any, limit: int = 4) -> dict[str, Any]:
    return build_recommendation_bundle(
        target=target,
        rows=rows,
        center=center,
        low=low,
        high=high,
        ops=_recommendation_ops(),
        limit=limit,
    )



def _build_recommended_listings(*, target: dict[str, Any], rows: list[tuple[float, dict[str, Any]]], center: Any, low: Any, high: Any, limit: int = 4) -> list[dict[str, Any]]:
    result = _build_recommendation_result(target=target, rows=rows, center=center, low=low, high=high, limit=limit)
    recommended = list(result.get("recommended_listings") or [])
    if recommended:
        return recommended
    src = [(float(_to_float(sim) or 0.0), rec) for sim, rec in list(rows or []) if isinstance(rec, dict)]
    fallback_rows = _prioritize_display_neighbors(target, src)[: max(1, min(int(limit or 0), 3))]
    fallback: list[dict[str, Any]] = []
    for sim, rec in fallback_rows:
        display_low, display_high = _range_pair_from_record(rec)
        seoul_no = int(_to_float(rec.get("number")) or 0)
        fallback.append(
            {
                "seoul_no": seoul_no,
                "now_uid": str(rec.get("uid", "")).strip(),
                "license_text": _compact(rec.get("license_text"), _LIM_LICENSE_TEXT),
                "price_eok": _round4(rec.get("current_price_eok")),
                "display_low_eok": _round4(display_low),
                "display_high_eok": _round4(display_high),
                "sales3_eok": _round4(rec.get("sales3_eok")),
                "recommendation_score": _round4(sim),
                "recommendation_label": "보조 검토",
                "recommendation_focus": "면허·가격대 보조 비교",
                "reasons": ["유사 매물 후보입니다."],
                "url": f"{str(core.SITE_URL).rstrip('/')}/mna/{seoul_no}" if seoul_no else "",
            }
        )
    return fallback


def _apply_special_sector_publication_guard(result: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    out = dict(result or {})
    sector_name = _special_balance_sector_name(target.get("license_tokens") or target.get("license_text"))
    if sector_name != "정보통신":
        return out
    if str(out.get("publication_mode") or "").strip() != "full":
        return out

    center = float(_to_float(out.get("estimate_center_eok")) or _to_float(out.get("total_transfer_value_eok")) or 0.0)
    low = float(_to_float(out.get("estimate_low_eok")) or _to_float(out.get("total_transfer_low_eok")) or center)
    high = float(_to_float(out.get("estimate_high_eok")) or _to_float(out.get("total_transfer_high_eok")) or center)
    confidence = float(_to_float(out.get("confidence_percent")) or 0.0)
    span_ratio = ((high - low) / center) if center > 0 else 0.0

    too_wide = span_ratio > _PUB_SPAN_RATIO_MAX
    too_small = center < _PUB_CENTER_AMOUNT_MIN
    insufficient_confidence = confidence < _PUB_CONFIDENCE_MIN
    if not (too_wide or too_small or insufficient_confidence):
        return out

    reason_parts: list[str] = []
    if too_wide:
        reason_parts.append("추정 범위 폭이 넓음")
    if too_small:
        reason_parts.append("절대 금액 구간이 작음")
    if insufficient_confidence:
        reason_parts.append("공개 신뢰도 기준 미달")
    reason = "정보통신 업종은 공개 안전도 기준상 " + ", ".join(reason_parts) + " 경우 기준가 대신 범위부터 안내합니다."

    out["publication_mode"] = "range_only"
    out["publication_label"] = "범위 먼저 안내"
    out["publication_reason"] = reason
    notes = [str(x or "").strip() for x in list(out.get("risk_notes") or []) if str(x or "").strip()]
    if reason not in notes:
        notes.append(reason)
    out["risk_notes"] = notes
    return out



def _project_estimate_result(server, resolution, result: dict[str, Any]) -> dict[str, Any]:
    payload = dict(result or {})
    tier = _estimate_response_tier(server, resolution)
    policy = {
        "tier": tier,
        "detail_included": tier in {"detail", "internal"},
        "internal_meta_included": tier == "internal",
        "tenant_plan": _tenant_plan_key(resolution) or "unscoped",
    }
    if not bool(payload.get("ok")):
        payload["response_policy"] = policy
        return _json_ready(payload)

    def _detail_recommendation_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "seoul_no": int(_to_float(row.get("seoul_no")) or 0),
            "license_text": _compact(row.get("license_text"), _LIM_LICENSE_TEXT),
            "price_eok": _round4(row.get("price_eok")),
            "display_low_eok": _round4(row.get("display_low_eok")),
            "display_high_eok": _round4(row.get("display_high_eok")),
            "sales3_eok": _round4(row.get("sales3_eok")),
            "recommendation_label": _compact(row.get("recommendation_label"), _LIM_REC_LABEL),
            "recommendation_focus": _compact(row.get("recommendation_focus"), _LIM_REC_FOCUS),
            "precision_tier": _compact(row.get("precision_tier"), _LIM_PRECISION_TIER),
            "reasons": [str(x or "").strip() for x in list(row.get("reasons") or [])[:3] if str(x or "").strip()],
            "fit_summary": _compact(row.get("fit_summary"), _LIM_FIT_SUMMARY),
            "matched_axes": [str(x or "").strip() for x in list(row.get("matched_axes") or [])[:4] if str(x or "").strip()],
            "mismatch_flags": [str(x or "").strip() for x in list(row.get("mismatch_flags") or [])[:4] if str(x or "").strip()],
            "url": _compact(row.get("url"), _LIM_URL),
        }

    if tier == "summary":
        summary_recommended = []
        for row in list(payload.get("recommended_listings") or [])[:3]:
            if not isinstance(row, dict):
                continue
            summary_recommended.append(
                {
                    "seoul_no": int(_to_float(row.get("seoul_no")) or 0),
                    "license_text": _compact(row.get("license_text"), _LIM_LICENSE_TEXT),
                    "display_low_eok": _round4(row.get("display_low_eok")),
                    "display_high_eok": _round4(row.get("display_high_eok")),
                    "recommendation_label": _compact(row.get("recommendation_label"), _LIM_REC_LABEL),
                    "recommendation_focus": _compact(row.get("recommendation_focus"), _LIM_REC_FOCUS),
                    "reasons": [str(x or "").strip() for x in list(row.get("reasons") or [])[:3] if str(x or "").strip()],
                    "url": _compact(row.get("url"), _LIM_URL),
                }
            )
        allowed = {
            "ok",
            "generated_at",
            "estimate_center_eok",
            "estimate_low_eok",
            "estimate_high_eok",
            "confidence_score",
            "confidence_percent",
            "publication_mode",
            "publication_label",
            "publication_reason",
            "price_source_tier",
            "price_source_label",
            "price_sample_count",
            "price_is_estimate",
            "price_range_kind",
            "price_source_channel",
            "price_disclaimer",
            "recommendation_meta",
        }
        trimmed = {k: payload.get(k) for k in allowed if k in payload}
        if summary_recommended:
            trimmed["recommended_listings"] = summary_recommended
        trimmed["response_policy"] = policy
        return _json_ready(trimmed)
    if tier == "detail":
        payload.pop("neighbors", None)
        detail_recommended = []
        for row in list(payload.get("recommended_listings") or [])[:4]:
            if not isinstance(row, dict):
                continue
            detail_recommended.append(_detail_recommendation_row(row))
        if detail_recommended:
            payload["recommended_listings"] = detail_recommended
        payload["response_policy"] = policy
        return _json_ready(payload)
    payload["tenant_id"] = _tenant_id_value(resolution)
    payload["response_policy"] = policy
    return _json_ready(payload)


def _json_ready(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, set):
        return [_json_ready(v) for v in sorted(value, key=lambda item: str(item))]
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    if hasattr(value, "_asdict"):
        try:
            return _json_ready(value._asdict())
        except (TypeError, AttributeError):
            pass
    if hasattr(value, "__dict__"):
        try:
            return _json_ready(vars(value))
        except TypeError:
            pass
    return str(value)



def _pick_total_value(result: dict[str, Any]) -> float:
    for key in ("total_transfer_value_eok", "internal_estimate_eok", "estimate_center_eok", "public_center_eok"):
        value = _to_float(result.get(key))
        if value is not None:
            return float(value)
    low = _to_float(result.get("estimate_low_eok"))
    high = _to_float(result.get("estimate_high_eok"))
    if low is not None and high is not None:
        return float((low + high) / 2.0)
    return 0.0



def _clean_row_license_text(row: dict[str, Any], fallback_license: str) -> dict[str, Any]:
    out = dict(row or {})
    current = _compact(out.get("license_text"))
    if not current or current.replace("?", "") == "":
        out["license_text"] = fallback_license
    return out


_BaseYangdoBlackboxEstimator = globals()["YangdoBlackboxEstimator"]
_BaseYangdoUsageStore = globals()["YangdoUsageStore"]


class YangdoUsageStore(_BaseYangdoUsageStore):
    def usage_snapshot(self, *args, **kwargs) -> dict[str, Any]:
        """Return current API usage counts, falling back to zeros on any DB error."""
        try:
            return super().usage_snapshot(*args, **kwargs)
        except (sqlite3.Error, OSError, TypeError, KeyError, ValueError):
            tenant_id = _compact(kwargs.get("tenant_id") if kwargs else "")
            plan = _compact(kwargs.get("plan") if kwargs else "").lower()
            year_month = _compact(kwargs.get("year_month") if kwargs else "")
            return {
                "tenant_id": tenant_id or "unknown",
                "plan": plan or "unknown",
                "year_month": year_month,
                "usage_events": 0,
                "ok_events": 0,
                "error_events": 0,
                "remaining_usage_events": None,
                "protected": False,
                "blocked": False,
            }

    def insert_estimate_usage(self, *args, **kwargs) -> dict[str, Any] | None:
        """Record a single estimate event, returning ``None`` on any DB error."""
        try:
            return super().insert_estimate_usage(*args, **kwargs)
        except (sqlite3.Error, OSError, TypeError, KeyError, ValueError):
            return None


class YangdoBlackboxEstimator(_BaseYangdoBlackboxEstimator):
    @classmethod
    def _is_separate_balance_group_token(cls, raw: Any) -> bool:
        return _is_special_license_text(raw)

    @classmethod
    def _is_balance_separate_paid_group(cls, target: dict[str, Any] | None) -> bool:
        target = target or {}
        return _is_special_license_text(target.get("license_text") or target.get("raw_license_key") or target.get("license_tokens"))

    def _target_from_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = dict(payload or {})
        out = super()._target_from_payload(data)
        license_text = _normalize_license_text(data.get("license_text") or out.get("license_text"))
        if license_text:
            out["license_text"] = license_text
            out["raw_license_key"] = _compact(out.get("raw_license_key")) or license_text
            out["license_tokens"] = set(out.get("license_tokens") or {license_text})
        reorg_mode = _normalize_reorg_mode(data.get("reorg_mode") or data.get("reorganization_type") or out.get("reorg_mode"))
        out["reorg_mode"] = reorg_mode
        credit_level = _normalize_credit_level(data.get("credit_level") or out.get("credit_level"))
        if credit_level or out.get("credit_level"):
            out["credit_level"] = credit_level
        admin_history = _normalize_admin_history(data.get("admin_history") or out.get("admin_history"))
        if admin_history or out.get("admin_history"):
            out["admin_history"] = admin_history
        requested_mode = _normalize_balance_usage_mode(data.get("balance_usage_mode") or out.get("balance_usage_mode_requested"))
        raw_balance = float(_to_float(data.get("balance_eok")) or _to_float(out.get("balance_eok")) or 0.0)
        is_special = self._is_balance_separate_paid_group(out)
        out["requires_reorg_mode"] = is_special
        out["input_balance_eok"] = raw_balance
        out["balance_usage_mode_requested"] = requested_mode or ""
        out["split_optional_pricing"] = is_special and reorg_mode == "분할/합병"
        if out["split_optional_pricing"]:
            for field in ("specialty", "surplus_eok", "debt_ratio", "liq_ratio"):
                out[field] = None
            out["credit_level"] = ""
            missing = [str(x or "").strip() for x in list(out.get("missing_critical") or []) if str(x or "").strip()]
            out["missing_critical"] = [x for x in missing if x != "이익잉여금"]
        balance_mode = _resolve_balance_usage_mode(
            requested_mode=requested_mode,
            seller_withdraws_guarantee_loan=bool(data.get("seller_withdraws_guarantee_loan")),
            buyer_takes_balance_as_credit=bool(data.get("buyer_takes_balance_as_credit")),
            balance_excluded=is_special,
            license_text=license_text,
            reorg_mode=reorg_mode,
        )
        out["balance_excluded"] = bool(is_special)
        out["balance_usage_mode"] = balance_mode
        out["seller_withdraws_guarantee_loan"] = balance_mode == "loan_withdrawal"
        out["buyer_takes_balance_as_credit"] = balance_mode == "credit_transfer"
        return out

    def estimate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Run a full yangdo price estimation with post-processing (publication safety, recommendations)."""
        data = dict(payload or {})
        target = self._target_from_payload(data)
        result = dict(super().estimate(data) or {})
        if not bool(result.get("ok")):
            return result

        license_text = _compact(target.get("license_text") or data.get("license_text"))
        clean_license = _normalize_license_text(license_text)
        raw_balance = float(_to_float(data.get("balance_eok")) or _to_float(target.get("input_balance_eok")) or 0.0)
        total = _pick_total_value(result)
        low = float(_to_float(result.get("estimate_low_eok")) or _to_float(result.get("total_transfer_low_eok")) or total)
        high = float(_to_float(result.get("estimate_high_eok")) or _to_float(result.get("total_transfer_high_eok")) or total)
        public_total = _to_float(result.get("public_total_transfer_value_eok"))
        if public_total is None:
            public_total = _to_float(result.get("public_center_eok"))
        if public_total is None:
            public_total = total
        public_low = _to_float(result.get("public_total_transfer_low_eok"))
        if public_low is None:
            public_low = _to_float(result.get("public_low_eok"))
        if public_low is None:
            public_low = low
        public_high = _to_float(result.get("public_total_transfer_high_eok"))
        if public_high is None:
            public_high = _to_float(result.get("public_high_eok"))
        if public_high is None:
            public_high = high
        pricing_adjustment = _maybe_apply_fire_single_license_guarded_prior(
            records=list(getattr(self, "_records", []) or []),
            target=target,
            total=total,
            low=low,
            high=high,
            public_total=public_total,
            public_low=public_low,
            public_high=public_high,
        )
        if pricing_adjustment:
            total = float(_to_float(pricing_adjustment.get("adjusted_total_transfer_value_eok")) or total)
            low = float(_to_float(pricing_adjustment.get("adjusted_low_eok")) or low)
            high = float(_to_float(pricing_adjustment.get("adjusted_high_eok")) or high)
            public_total = _to_float(pricing_adjustment.get("adjusted_public_total_transfer_value_eok")) or public_total
            public_low = _to_float(pricing_adjustment.get("adjusted_public_low_eok")) or public_low
            public_high = _to_float(pricing_adjustment.get("adjusted_public_high_eok")) or public_high
            result["core_pricing_mode"] = pricing_adjustment.get("mode")
            result["core_pricing_adjustment"] = pricing_adjustment
        requested_mode = _normalize_balance_usage_mode(data.get("balance_usage_mode") or target.get("balance_usage_mode_requested"))
        is_special = self._is_balance_separate_paid_group(target)

        if is_special:
            settlement = _build_settlement_output(
                total_transfer_value_eok=total,
                total_low_eok=low,
                total_high_eok=high,
                public_total_transfer_value_eok=public_total,
                public_total_low_eok=public_low,
                public_total_high_eok=public_high,
                raw_balance_input_eok=raw_balance,
                balance_excluded=True,
                balance_usage_mode=target.get("balance_usage_mode") or "loan_withdrawal",
                effective_balance_rate=0.0,
                split_optional_pricing=bool(target.get("split_optional_pricing")),
                license_text=license_text,
                reorg_mode=target.get("reorg_mode"),
                requested_balance_usage_mode=requested_mode,
            )
            result.update(settlement)
            result["balance_excluded"] = True
            result["base_model_applied"] = True
            result["balance_model_mode"] = "special_settlement_split"
            result["balance_adjustment_eok"] = 0.0
            result["balance_pass_through"] = 0.0
            result["core_estimate_eok"] = _round4(total)
            result["estimate_center_eok"] = _round4(total)
            notes = [str(x or "").strip() for x in list(result.get("risk_notes") or []) if str(x or "").strip()]
            notes = [x for x in notes if "공제조합 잔액" not in x or "별도" not in x]
            policy_summary = _compact((result.get("settlement_policy") or {}).get("summary"))
            if policy_summary:
                notes.append(policy_summary)
            adjustment_reason = _compact((pricing_adjustment or {}).get("reason"))
            if adjustment_reason and adjustment_reason not in notes:
                notes.append(adjustment_reason)
            result["risk_notes"] = notes
        else:
            result["balance_excluded"] = False
            if raw_balance > 0:
                result["base_model_applied"] = True
                result["balance_usage_mode_requested"] = requested_mode or _compact(target.get("balance_usage_mode_requested"))
                result["balance_usage_mode"] = _compact(result.get("balance_usage_mode") or target.get("balance_usage_mode") or "embedded_balance")
                result["balance_model_mode"] = _compact(result.get("balance_model_mode") or "balance_base_core_beta")
                result["balance_adjustment_eok"] = _round4(raw_balance)
                result["balance_pass_through"] = 1.0
                result["core_estimate_eok"] = _round4(max(0.0, total - raw_balance))
            settlement = _build_settlement_output(
                total_transfer_value_eok=total,
                total_low_eok=low,
                total_high_eok=high,
                public_total_transfer_value_eok=public_total,
                public_total_low_eok=public_low,
                public_total_high_eok=public_high,
                raw_balance_input_eok=raw_balance,
                balance_excluded=False,
                balance_usage_mode=result.get("balance_usage_mode") or target.get("balance_usage_mode") or "embedded_balance",
                effective_balance_rate=result.get("balance_pass_through") or 1.0,
                split_optional_pricing=bool(target.get("split_optional_pricing")),
                license_text=license_text,
                reorg_mode=target.get("reorg_mode"),
                requested_balance_usage_mode=requested_mode,
            )
            result.update(settlement)
            notes = [str(x or "").strip() for x in list(result.get("risk_notes") or []) if str(x or "").strip()]
            result["risk_notes"] = [x for x in notes if "전기·정보통신·소방" not in x and "공제조합 잔액이 양도가와 별도" not in x]

        result["target"] = target
        result["neighbors"] = [_clean_row_license_text(row, clean_license) for row in list(result.get("neighbors") or []) if isinstance(row, dict)]
        result["recommended_listings"] = [_clean_row_license_text(row, clean_license) for row in list(result.get("recommended_listings") or []) if isinstance(row, dict)]
        return _apply_special_sector_publication_guard(result, target)


_ORIGINAL_HANDLER_DO_GET = getattr(Handler, "do_GET", None)


def _patched_handler_do_get(self) -> None:  # noqa: ANN001
    path = str(getattr(self, "path", "") or "").split("?", 1)[0]
    if path in {"/health", "/v1/health"}:
        if hasattr(self, "_allow_request") and not self._allow_request():
            return
        if hasattr(self, "_require_channel_ready") and not self._require_channel_ready():
            return
        _write_partner_health_json(self, 200)
        return
    if _ORIGINAL_HANDLER_DO_GET is None:
        return None
    return _ORIGINAL_HANDLER_DO_GET(self)


if _ORIGINAL_HANDLER_DO_GET is not None:
    Handler.do_GET = _patched_handler_do_get


vars(_BASE).update(
    {
        "YangdoBlackboxEstimator": YangdoBlackboxEstimator,
        "YangdoUsageStore": YangdoUsageStore,
        "_SPECIAL_BALANCE_LOAN_UTILIZATION": _SPECIAL_BALANCE_LOAN_UTILIZATION,
        "_SPECIAL_BALANCE_AUTO_POLICIES": _SPECIAL_BALANCE_AUTO_POLICIES,
        "_SPECIAL_SETTLEMENT_SCENARIO_INPUT_MODES": _SPECIAL_SETTLEMENT_SCENARIO_INPUT_MODES,
        "_normalize_license_text": _normalize_license_text,
        "_special_balance_sector_name": _special_balance_sector_name,
        "_normalize_reorg_mode": _normalize_reorg_mode,
        "_normalize_balance_usage_mode": _normalize_balance_usage_mode,
        "_normalize_credit_level": _normalize_credit_level,
        "_normalize_admin_history": _normalize_admin_history,
        "_get_special_balance_auto_policy": _get_special_balance_auto_policy,
        "_resolve_special_auto_mode": _resolve_special_auto_mode,
        "_resolve_balance_usage_mode": _resolve_balance_usage_mode,
        "_settlement_mode_label": _settlement_mode_label,
        "_settlement_input_mode_label": _settlement_input_mode_label,
        "_build_single_settlement_view": _build_single_settlement_view,
        "_build_settlement_output": _build_settlement_output,
        "_tenant_plan_key": _tenant_plan_key,
        "_tenant_id_value": _tenant_id_value,
        "_estimate_response_tier": _estimate_response_tier,
        "_range_pair_from_record": _range_pair_from_record,
        "_prioritize_display_neighbors": _prioritize_display_neighbors,
        "_recommendation_ops": _recommendation_ops,
        "_build_recommendation_result": _build_recommendation_result,
        "_build_recommended_listings": _build_recommended_listings,
        "_apply_special_sector_publication_guard": _apply_special_sector_publication_guard,
        "_project_estimate_result": _project_estimate_result,
        "collapse_duplicate_neighbors": collapse_duplicate_neighbors,
    }
)

for _name, _value in vars(_BASE).items():
    if _name in {"__name__", "__file__", "__package__", "__loader__", "__spec__", "__cached__"}:
        continue
    globals()[_name] = _value
__doc__ = getattr(_BASE, "__doc__", None)
__all__ = [name for name in globals() if not name.startswith("__")]


if __name__ == "__main__":
    import logging as _logging
    import signal as _signal

    _shutdown_logger = _logging.getLogger("yangdo_blackbox_api")

    def _graceful_shutdown(signum: int, _frame: object) -> None:
        sig_name = _signal.Signals(signum).name if hasattr(_signal, "Signals") else str(signum)
        _shutdown_logger.info("yangdo estimate api received %s, shutting down", sig_name)
        raise SystemExit(0)

    _signal.signal(_signal.SIGTERM, _graceful_shutdown)
    main()
