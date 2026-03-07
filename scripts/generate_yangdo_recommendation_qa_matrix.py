#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import json
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yangdo_blackbox_api

DEFAULT_JSON = ROOT / "logs" / "yangdo_recommendation_qa_matrix_latest.json"
DEFAULT_MD = ROOT / "logs" / "yangdo_recommendation_qa_matrix_latest.md"

allmod = importlib.import_module("all")


class _FakeGateway:
    def check_feature(self, resolution: Any, feature: str) -> bool:
        return False

    def check_system(self, resolution: Any, system: str) -> bool:
        return True


def _meta_from_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    def _avg(field: str) -> Any:
        vals = [float(r.get(field)) for r in records if isinstance(r.get(field), (int, float))]
        if not vals:
            return None
        return sum(vals) / len(vals)

    def _median(field: str) -> Any:
        vals = sorted(float(r.get(field)) for r in records if isinstance(r.get(field), (int, float)))
        if not vals:
            return None
        mid = len(vals) // 2
        if len(vals) % 2:
            return vals[mid]
        return (vals[mid - 1] + vals[mid]) / 2.0

    return {
        "avg_balance_eok": _avg("balance_eok"),
        "avg_capital_eok": _avg("capital_eok"),
        "avg_surplus_eok": _avg("surplus_eok"),
        "median_specialty": _median("specialty"),
        "median_sales3_eok": _median("sales3_eok"),
    }


def _prime_estimator(est: Any, records: List[Dict[str, Any]]) -> None:
    est._records = list(records)
    est._train_records = list(records)
    est._token_index = allmod._build_neighbor_index(records)
    est._meta = _meta_from_records(records)


def _record(
    est: Any,
    *,
    uid: int,
    specialty: float,
    sales3: float,
    balance: float,
    price: float,
    license_text: str,
    row: int,
) -> Dict[str, Any]:
    base = est._target_from_payload(
        {
            "license_text": license_text,
            "specialty": specialty,
            "sales3_eok": sales3,
            "sales5_eok": round(sales3 * 1.35, 4),
            "balance_eok": balance,
            "capital_eok": 3.0,
            "surplus_eok": 0.4,
            "license_year": 2016,
            "debt_ratio": 70.0,
            "liq_ratio": 220.0,
            "company_type": "주식회사",
            "credit_level": "보통",
            "admin_history": "없음",
            "provided_signals": 9,
        }
    )
    base.update(
        {
            "uid": str(uid),
            "row": int(row),
            "number": int(uid),
            "current_price_eok": float(price),
            "claim_price_eok": None,
            "current_price_text": f"{price}억",
            "claim_price_text": "",
            "years": {
                "y23": round(sales3 * 0.30, 4),
                "y24": round(sales3 * 0.33, 4),
                "y25": round(sales3 * 0.37, 4),
            },
        }
    )
    return base


def _standard_resolution() -> Any:
    return SimpleNamespace(tenant=SimpleNamespace(plan="standard", tenant_id="seoul_main"))


def _standard_server() -> Any:
    return SimpleNamespace(tenant_gateway_enabled=True, tenant_gateway=_FakeGateway())


def _scenario_strict_match(est: Any) -> Dict[str, Any]:
    target = est._target_from_payload(
        {
            "license_text": "종합",
            "specialty": 20.0,
            "sales3_eok": 15.0,
            "sales5_eok": 20.0,
            "balance_eok": 0.6,
            "capital_eok": 3.0,
            "company_type": "주식회사",
        }
    )
    rows = [
        (99.0, _record(est, uid=5201, specialty=20.0, sales3=15.0, balance=0.6, price=2.88, license_text="종합", row=1)),
        (98.0, _record(est, uid=6201, specialty=20.5, sales3=15.2, balance=0.6, price=2.94, license_text="종합", row=2)),
        (96.0, _record(est, uid=7201, specialty=22.5, sales3=18.1, balance=0.9, price=3.18, license_text="종합", row=3)),
        (99.2, _record(est, uid=7208, specialty=20.1, sales3=15.1, balance=0.6, price=3.01, license_text="종합", row=4)),
    ]
    result = yangdo_blackbox_api._build_recommendation_result(
        target=target,
        rows=rows,
        center=3.0,
        low=2.8,
        high=3.2,
        limit=3,
    )
    top = dict((result.get("recommended_listings") or [{}])[0])
    meta = dict(result.get("recommendation_meta") or {})
    ok = (
        int(top.get("seoul_no") or 0) == 7208
        and str(top.get("precision_tier") or "") == "high"
        and len(list(top.get("matched_axes") or [])) >= 2
        and int(meta.get("recommended_count") or 0) >= 3
    )
    return {
        "scenario_id": "strict_profile_match_7000_band",
        "ok": ok,
        "expected": {
            "top_seoul_no": 7208,
            "precision_tier": "high",
            "matched_axes_min": 2,
        },
        "observed": {
            "top_seoul_no": int(top.get("seoul_no") or 0),
            "precision_tier": str(top.get("precision_tier") or ""),
            "recommendation_focus": str(top.get("recommendation_focus") or ""),
            "matched_axes": list(top.get("matched_axes") or []),
            "fit_summary": str(top.get("fit_summary") or ""),
            "precision_mode": str(meta.get("precision_mode") or ""),
            "recommended_count": int(meta.get("recommended_count") or 0),
        },
        "why": "입력 프로필과 거의 같은 7000번대 매물이 있으면 추천 최상위가 그 밴드로 올라와야 합니다.",
    }


def _scenario_fallback_when_hot_band_weak(est: Any) -> Dict[str, Any]:
    target = est._target_from_payload(
        {
            "license_text": "??",
            "specialty": 20.0,
            "sales3_eok": 15.0,
            "sales5_eok": 20.0,
            "balance_eok": 0.6,
            "capital_eok": 3.0,
            "company_type": "????",
        }
    )
    rows = [
        (99.0, _record(est, uid=5201, specialty=20.0, sales3=15.0, balance=0.6, price=2.88, license_text="??", row=1)),
        (97.0, _record(est, uid=6201, specialty=20.5, sales3=15.2, balance=0.6, price=2.94, license_text="??", row=2)),
        (98.5, _record(est, uid=7201, specialty=22.0, sales3=26.0, balance=0.7, price=3.35, license_text="??", row=3)),
        (98.0, _record(est, uid=7208, specialty=21.5, sales3=27.0, balance=0.7, price=3.42, license_text="??", row=4)),
    ]
    result = yangdo_blackbox_api._build_recommendation_result(
        target=target,
        rows=rows,
        center=2.95,
        low=2.8,
        high=3.1,
        limit=3,
    )
    recommended = list(result.get("recommended_listings") or [])
    top = dict(recommended[0]) if recommended else {}
    meta = dict(result.get("recommendation_meta") or {})
    recommended_ids = [int(item.get("seoul_no") or 0) for item in recommended]
    hot_band_ids = {7201, 7208}
    fallback_band_ids = {5201, 6201}
    top_id = int(top.get("seoul_no") or 0)
    top_band = str(top.get("recommendation_price_band") or "")
    unique_price_band_count = int(meta.get("unique_price_band_count") or 0)
    ok = (
        top_id in fallback_band_ids
        and top_id not in hot_band_ids
        and str(top.get("precision_tier") or "") in {"high", "medium"}
        and bool(hot_band_ids.intersection(recommended_ids))
        and unique_price_band_count >= 2
        and top_band == "2_to_3"
    )
    return {
        "scenario_id": "fallback_when_hot_band_is_weak",
        "ok": ok,
        "expected": {
            "top_seoul_no_any_of": sorted(fallback_band_ids),
            "top_excludes_hot_band_ids": sorted(hot_band_ids),
            "precision_tier_any_of": ["high", "medium"],
            "top_price_band": "2_to_3",
            "recommended_contains_hot_band": True,
            "unique_price_band_count_min": 2,
        },
        "observed": {
            "top_seoul_no": top_id,
            "precision_tier": str(top.get("precision_tier") or ""),
            "top_price_band": top_band,
            "mismatch_flags": list(top.get("mismatch_flags") or []),
            "fit_summary": str(top.get("fit_summary") or ""),
            "precision_mode": str(meta.get("precision_mode") or ""),
            "recommended_ids": recommended_ids,
            "unique_price_band_count": unique_price_band_count,
        },
        "why": "?? hot band? ???? ??? ????? ??? top1? ? ??? ???? ??, ???? ? ??? 2~3? fallback ??? ?? ???? ???.",
    }


def _scenario_balance_excluded_stable(est: Any) -> Dict[str, Any]:
    rows = [
        (98.5, _record(est, uid=9101, specialty=18.0, sales3=12.0, balance=0.4, price=2.22, license_text="전기", row=1)),
        (97.2, _record(est, uid=9102, specialty=18.5, sales3=12.4, balance=0.7, price=2.30, license_text="전기", row=2)),
        (96.7, _record(est, uid=9103, specialty=19.2, sales3=12.8, balance=1.1, price=2.36, license_text="전기", row=3)),
    ]
    target_low = est._target_from_payload(
        {
            "license_text": "전기",
            "specialty": 18.2,
            "sales3_eok": 12.4,
            "sales5_eok": 15.5,
            "balance_eok": 0.5,
            "capital_eok": 3.0,
            "company_type": "주식회사",
        }
    )
    target_high = dict(target_low)
    target_high["balance_eok"] = 50.0
    result_low = yangdo_blackbox_api._build_recommendation_result(
        target=target_low,
        rows=rows,
        center=2.3,
        low=2.2,
        high=2.4,
        limit=2,
    )
    result_high = yangdo_blackbox_api._build_recommendation_result(
        target=target_high,
        rows=rows,
        center=2.3,
        low=2.2,
        high=2.4,
        limit=2,
    )
    low_top = dict((result_low.get("recommended_listings") or [{}])[0])
    high_top = dict((result_high.get("recommended_listings") or [{}])[0])
    score_gap = abs(float(low_top.get("recommendation_score") or 0.0) - float(high_top.get("recommendation_score") or 0.0))
    ok = int(low_top.get("seoul_no") or 0) == int(high_top.get("seoul_no") or 0) and score_gap <= 0.2
    return {
        "scenario_id": "balance_excluded_sector_keeps_recommendation_stable",
        "ok": ok,
        "expected": {
            "same_top_seoul_no": True,
            "max_score_gap": 0.2,
        },
        "observed": {
            "low_balance_top": int(low_top.get("seoul_no") or 0),
            "high_balance_top": int(high_top.get("seoul_no") or 0),
            "score_gap": round(score_gap, 4),
            "low_balance_focus": str(low_top.get("recommendation_focus") or ""),
            "high_balance_focus": str(high_top.get("recommendation_focus") or ""),
        },
        "why": "전기·정보통신·소방 계열은 공제잔액을 추천 축에 과하게 반영하지 않아야 합니다.",
    }


def _scenario_sparse_assistive(est: Any) -> Dict[str, Any]:
    target = est._target_from_payload(
        {
            "license_text": "건축",
            "specialty": 11.0,
            "sales3_eok": 4.2,
            "sales5_eok": 6.0,
            "balance_eok": 0.2,
            "capital_eok": 2.6,
            "company_type": "주식회사",
        }
    )
    rows = [
        (86.0, _record(est, uid=4301, specialty=28.0, sales3=14.0, balance=0.2, price=0.88, license_text="건축", row=1)),
        (84.5, _record(est, uid=4302, specialty=32.0, sales3=16.5, balance=0.3, price=0.96, license_text="건축", row=2)),
    ]
    result = yangdo_blackbox_api._build_recommendation_result(
        target=target,
        rows=rows,
        center=0.92,
        low=0.85,
        high=1.02,
        limit=2,
    )
    top = dict((result.get("recommended_listings") or [{}])[0])
    meta = dict(result.get("recommendation_meta") or {})
    ok = bool(top) and (str(top.get("precision_tier") or "") == "assist" or str(meta.get("precision_mode") or "") == "assist")
    return {
        "scenario_id": "sparse_profile_returns_assistive_recommendation",
        "ok": ok,
        "expected": {
            "assistive_precision": True,
        },
        "observed": {
            "top_seoul_no": int(top.get("seoul_no") or 0),
            "precision_tier": str(top.get("precision_tier") or ""),
            "precision_mode": str(meta.get("precision_mode") or ""),
            "fit_summary": str(top.get("fit_summary") or ""),
        },
        "why": "표본이 적고 규모 차이가 큰 구간은 우선 추천보다 보조 추천으로 내려와야 안전합니다.",
    }


def _scenario_summary_projection_safe(est: Any) -> Dict[str, Any]:
    target = est._target_from_payload(
        {
            "license_text": "종합",
            "specialty": 20.0,
            "sales3_eok": 15.0,
            "sales5_eok": 20.0,
            "balance_eok": 0.6,
            "capital_eok": 3.0,
            "company_type": "주식회사",
        }
    )
    rows = [
        (99.0, _record(est, uid=5201, specialty=20.0, sales3=15.0, balance=0.6, price=2.88, license_text="종합", row=1)),
        (97.0, _record(est, uid=6201, specialty=20.5, sales3=15.2, balance=0.6, price=2.94, license_text="종합", row=2)),
        (96.0, _record(est, uid=7208, specialty=21.0, sales3=16.0, balance=0.6, price=3.08, license_text="종합", row=3)),
    ]
    rec_result = yangdo_blackbox_api._build_recommendation_result(
        target=target,
        rows=rows,
        center=3.0,
        low=2.8,
        high=3.2,
        limit=3,
    )
    payload = {
        "ok": True,
        "generated_at": "2026-03-07T10:00:00",
        "estimate_center_eok": 3.0,
        "estimate_low_eok": 2.8,
        "estimate_high_eok": 3.2,
        "confidence_score": 74.0,
        "confidence_percent": 74,
        "publication_mode": "full",
        "publication_label": "기준가+범위",
        "publication_reason": "",
        "price_source_tier": "B",
        "price_source_label": "비교 자료 보통",
        "price_sample_count": 6,
        "price_is_estimate": True,
        "price_range_kind": "AI_ESTIMATED_RANGE",
        "price_source_channel": "SHARED_MARKET_LISTING_DATASET",
        "price_disclaimer": "참고용 가격입니다.",
        "recommended_listings": list(rec_result.get("recommended_listings") or []),
        "recommendation_meta": dict(rec_result.get("recommendation_meta") or {}),
        "neighbors": [{"seoul_no": 1}],
    }
    projected = yangdo_blackbox_api._project_estimate_result(_standard_server(), _standard_resolution(), payload)
    first = dict((projected.get("recommended_listings") or [{}])[0])
    ok = (
        "recommendation_score" not in first
        and "recommendation_meta" in projected
        and bool(first.get("recommendation_focus"))
    )
    return {
        "scenario_id": "summary_tier_keeps_safe_recommendation_fields_only",
        "ok": ok,
        "expected": {
            "recommendation_score_hidden": True,
            "recommendation_meta_visible": True,
        },
        "observed": {
            "summary_keys": sorted(list(projected.keys())),
            "recommended_listing_keys": sorted(list(first.keys())),
        },
        "why": "요약 tier는 추천 이유와 가격대만 보여주고 raw 추천 점수 같은 내부 신호는 숨겨야 합니다.",
    }


def build_yangdo_recommendation_qa_matrix() -> Dict[str, Any]:
    est = yangdo_blackbox_api.YangdoBlackboxEstimator()
    baseline_records = [
        _record(est, uid=1001, specialty=18.0, sales3=12.0, balance=0.4, price=2.22, license_text="종합", row=1),
        _record(est, uid=1002, specialty=19.5, sales3=13.1, balance=0.5, price=2.34, license_text="종합", row=2),
        _record(est, uid=1003, specialty=21.0, sales3=14.6, balance=0.6, price=2.52, license_text="종합", row=3),
    ]
    _prime_estimator(est, baseline_records)

    scenarios = [
        _scenario_strict_match(est),
        _scenario_fallback_when_hot_band_weak(est),
        _scenario_balance_excluded_stable(est),
        _scenario_sparse_assistive(est),
        _scenario_summary_projection_safe(est),
    ]
    passed = sum(1 for row in scenarios if bool(row.get("ok")))
    failed = len(scenarios) - passed
    precision_counts: Dict[str, int] = {}
    for row in scenarios:
        observed = row.get("observed") if isinstance(row.get("observed"), dict) else {}
        tier = str(observed.get("precision_tier") or observed.get("precision_mode") or "").strip()
        if tier:
            precision_counts[tier] = int(precision_counts.get(tier, 0) or 0) + 1
    next_actions = []
    if failed:
        next_actions.append("추천 QA 실패 시나리오를 우선 수정하고 운영 산출물을 다시 생성합니다.")
    else:
        next_actions.append("추천 QA 매트릭스가 녹색이므로 운영 산출물과 특허 handoff에 이 결과를 그대로 사용합니다.")
    next_actions.append("양도가 서비스 페이지에서는 추천 정밀도와 추천 이유를 계산기 게이트 앞 설명 영역에 유지합니다.")
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "yangdo_recommendation_qa_matrix_latest",
        "summary": {
            "scenario_count": len(scenarios),
            "passed_count": passed,
            "failed_count": failed,
            "qa_ok": failed == 0,
            "strict_profile_regression_ok": bool(scenarios[0].get("ok")),
            "fallback_regression_ok": bool(scenarios[1].get("ok")),
            "balance_exclusion_regression_ok": bool(scenarios[2].get("ok")),
            "assistive_precision_regression_ok": bool(scenarios[3].get("ok")),
            "summary_projection_regression_ok": bool(scenarios[4].get("ok")),
            "precision_counts": precision_counts,
        },
        "scenarios": scenarios,
        "next_actions": next_actions,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Yangdo Recommendation QA Matrix",
        "",
        f"- qa_ok: {summary.get('qa_ok')}",
        f"- scenario_count: {summary.get('scenario_count')}",
        f"- passed_count: {summary.get('passed_count')}",
        f"- failed_count: {summary.get('failed_count')}",
        f"- strict_profile_regression_ok: {summary.get('strict_profile_regression_ok')}",
        f"- fallback_regression_ok: {summary.get('fallback_regression_ok')}",
        f"- balance_exclusion_regression_ok: {summary.get('balance_exclusion_regression_ok')}",
        f"- assistive_precision_regression_ok: {summary.get('assistive_precision_regression_ok')}",
        f"- summary_projection_regression_ok: {summary.get('summary_projection_regression_ok')}",
        "",
        "## Precision Counts",
    ]
    precision_counts = summary.get("precision_counts") if isinstance(summary.get("precision_counts"), dict) else {}
    for key, value in sorted(precision_counts.items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Scenarios"])
    for row in payload.get("scenarios", []):
        lines.append(f"- {row.get('scenario_id')}: ok={row.get('ok')}")
        lines.append(f"  - why: {row.get('why')}")
        lines.append(f"  - expected: {json.dumps(row.get('expected') or {}, ensure_ascii=False)}")
        lines.append(f"  - observed: {json.dumps(row.get('observed') or {}, ensure_ascii=False)}")
    lines.extend(["", "## Next Actions"])
    for item in payload.get("next_actions", []):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a deterministic QA matrix for yangdo recommendation quality.")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_yangdo_recommendation_qa_matrix()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool((payload.get("summary") or {}).get("qa_ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
