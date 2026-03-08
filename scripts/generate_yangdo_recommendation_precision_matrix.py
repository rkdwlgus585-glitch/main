#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yangdo_blackbox_api
from scripts import generate_yangdo_recommendation_qa_matrix as qa_base

DEFAULT_JSON = ROOT / "logs" / "yangdo_recommendation_precision_matrix_latest.json"
DEFAULT_MD = ROOT / "logs" / "yangdo_recommendation_precision_matrix_latest.md"


class _FeatureGateway:
    def __init__(self, features: List[str]) -> None:
        self._features = set(features or [])

    def check_feature(self, resolution: Any, feature: str) -> bool:
        return feature in self._features

    def check_system(self, resolution: Any, system: str) -> bool:
        return True


def _detail_projection_explainable(est: Any) -> Dict[str, Any]:
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
        (99.0, qa_base._record(est, uid=5201, specialty=20.0, sales3=15.0, balance=0.6, price=2.88, license_text="종합", row=1)),
        (97.0, qa_base._record(est, uid=6201, specialty=20.5, sales3=15.2, balance=0.6, price=2.94, license_text="종합", row=2)),
        (96.0, qa_base._record(est, uid=7208, specialty=21.0, sales3=16.0, balance=0.6, price=3.08, license_text="종합", row=3)),
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
    server = type(
        "_DetailServer",
        (),
        {
            "tenant_gateway_enabled": True,
            "tenant_gateway": _FeatureGateway(["estimate_detail"]),
        },
    )()
    projected = yangdo_blackbox_api._project_estimate_result(server, qa_base._standard_resolution(), payload)
    first = dict((projected.get("recommended_listings") or [{}])[0])
    ok = (
        "precision_tier" in first
        and "matched_axes" in first
        and "mismatch_flags" in first
        and "fit_summary" in first
        and "reasons" in first
        and "recommendation_focus" in first
        and "recommendation_score" not in first
        and "recommendation_focus_signature" not in first
        and "recommendation_price_band" not in first
        and "similarity" not in first
        and "neighbors" not in projected
    )
    return {
        "scenario_id": "detail_tier_keeps_explainable_recommendation_fields",
        "ok": ok,
        "expected": {
            "precision_tier_visible": True,
            "fit_axes_visible": True,
            "detail_safe_fields_visible": True,
            "internal_recommendation_fields_hidden": True,
            "neighbors_hidden": True,
        },
        "observed": {
            "detail_keys": sorted(list(projected.keys())),
            "recommended_listing_keys": sorted(list(first.keys())),
        },
        "why": "detail tier? ?? ??? ?????? ?? ?? ???? ??? raw score? ?? ??? ?, neighbor ???? ??? ???.",
    }


def _special_sector_target(
    est: Any,
    *,
    license_text: str,
    reorg_mode: str,
    specialty: float,
    sales3_eok: float,
    sales5_eok: float,
    balance_eok: float,
    capital_eok: float,
) -> Dict[str, Any]:
    return est._target_from_payload(
        {
            "license_text": license_text,
            "reorg_mode": reorg_mode,
            "specialty": specialty,
            "sales3_eok": sales3_eok,
            "sales5_eok": sales5_eok,
            "balance_eok": balance_eok,
            "capital_eok": capital_eok,
            "company_type": "주식회사",
        }
    )


def _special_sector_rows(est: Any, *, license_text: str) -> List[Dict[str, Any]]:
    return [
        qa_base._record(est, uid=9101, specialty=18.0, sales3=12.0, balance=0.4, price=2.22, license_text=license_text, row=1),
        qa_base._record(est, uid=9102, specialty=18.5, sales3=12.4, balance=0.7, price=2.30, license_text=license_text, row=2),
        qa_base._record(est, uid=9103, specialty=19.2, sales3=12.8, balance=1.1, price=2.36, license_text=license_text, row=3),
    ]


def _special_sector_scenario(
    est: Any,
    *,
    scenario_id: str,
    license_text: str,
    reorg_mode: str,
    expected_focus: str,
    expected_mismatch_missing: str,
    why: str,
) -> Dict[str, Any]:
    rows_data = _special_sector_rows(est, license_text=license_text)
    qa_base._prime_estimator(est, rows_data)
    target = _special_sector_target(
        est,
        license_text=license_text,
        reorg_mode=reorg_mode,
        specialty=18.2,
        sales3_eok=12.45,
        sales5_eok=15.5,
        balance_eok=99.0,
        capital_eok=3.0,
    )
    rows = [(98.5, rows_data[0]), (97.2, rows_data[1]), (96.7, rows_data[2])]
    result = yangdo_blackbox_api._build_recommendation_result(
        target=target,
        rows=rows,
        center=2.3,
        low=2.2,
        high=2.4,
        limit=3,
    )
    top = dict((result.get("recommended_listings") or [{}])[0])
    mismatch_flags = list(top.get("mismatch_flags") or [])
    focus = str(top.get("recommendation_focus") or "")
    ok = (
        bool(target.get("balance_excluded"))
        and bool(top)
        and expected_focus in focus
        and expected_mismatch_missing not in " ".join(mismatch_flags)
    )
    return {
        "scenario_id": scenario_id,
        "ok": ok,
        "expected": {
            "balance_excluded": True,
            "focus_contains": expected_focus,
            "mismatch_excludes": expected_mismatch_missing,
            "reorg_mode": str(target.get("reorg_mode") or ""),
        },
        "observed": {
            "license_text": license_text,
            "reorg_mode": str(target.get("reorg_mode") or ""),
            "split_optional_pricing": bool(target.get("split_optional_pricing")),
            "balance_excluded": bool(target.get("balance_excluded")),
            "top_seoul_no": int(top.get("seoul_no") or 0),
            "recommendation_focus": focus,
            "matched_axes": list(top.get("matched_axes") or []),
            "mismatch_flags": mismatch_flags,
        },
        "why": why,
    }


def _special_sector_comprehensive_electric(est: Any) -> Dict[str, Any]:
    return _special_sector_scenario(
        est,
        scenario_id="special_sector_comprehensive_uses_sales_and_scale_without_balance",
        license_text="\uC804\uAE30",
        reorg_mode="comprehensive",
        expected_focus="시평 규모",
        expected_mismatch_missing="공제잔액 차이",
        why="전기 포괄은 공제잔액을 가격과 추천에서 빼되, 비교축은 실적과 시평 중심으로 유지되어야 합니다.",
    )


def _special_sector_split_electric(est: Any) -> Dict[str, Any]:
    return _special_sector_scenario(
        est,
        scenario_id="special_sector_split_uses_sales_and_capital_without_balance",
        license_text="\uC804\uAE30",
        reorg_mode="split_merge",
        expected_focus="자본금",
        expected_mismatch_missing="공제잔액 차이",
        why="전기 분할·합병은 공제잔액 대신 최근 3년 실적과 자본금이 추천 중심축으로 올라와야 합니다.",
    )


def _special_sector_comprehensive_telecom(est: Any) -> Dict[str, Any]:
    return _special_sector_scenario(
        est,
        scenario_id="telecom_comprehensive_keeps_scale_focus_without_balance",
        license_text="\uC815\uBCF4\uD1B5\uC2E0",
        reorg_mode="comprehensive",
        expected_focus="시평 규모",
        expected_mismatch_missing="공제잔액 차이",
        why="정보통신 포괄도 공제잔액은 배제하되 추천 설명은 시평·실적 중심으로 유지되어야 합니다.",
    )


def _special_sector_split_telecom(est: Any) -> Dict[str, Any]:
    return _special_sector_scenario(
        est,
        scenario_id="telecom_split_moves_focus_to_sales_and_capital",
        license_text="\uC815\uBCF4\uD1B5\uC2E0",
        reorg_mode="split_merge",
        expected_focus="자본금",
        expected_mismatch_missing="공제잔액 차이",
        why="정보통신 분할·합병은 추천 설명에서도 공제 대신 최근 3년 실적과 자본금이 먼저 보여야 합니다.",
    )


def _special_sector_split_fire(est: Any) -> Dict[str, Any]:
    return _special_sector_scenario(
        est,
        scenario_id="fire_split_moves_focus_to_sales_and_capital",
        license_text="\uC18C\uBC29",
        reorg_mode="split_merge",
        expected_focus="자본금",
        expected_mismatch_missing="공제잔액 차이",
        why="소방 분할·합병도 추천 비교축이 최근 3년 실적과 자본금으로 옮겨져야 운영 설명과 일치합니다.",
    )


def _scenario_specs(est: Any) -> List[Dict[str, Any]]:
    return [
        {
            "sector_group": "general",
            "price_band": "mid_2_to_4_eok",
            "response_tier": "raw",
            "precision_target": "high",
            "builder": qa_base._scenario_strict_match,
        },
        {
            "sector_group": "general",
            "price_band": "hot_band_fallback",
            "response_tier": "raw",
            "precision_target": "medium_or_high",
            "builder": qa_base._scenario_fallback_when_hot_band_weak,
        },
        {
            "sector_group": "balance_excluded_sector",
            "price_band": "mid_2_to_3_eok",
            "response_tier": "raw",
            "precision_target": "stable",
            "builder": qa_base._scenario_balance_excluded_stable,
        },
        {
            "sector_group": "balance_excluded_sector",
            "price_band": "mid_2_to_3_eok",
            "response_tier": "raw",
            "precision_target": "comprehensive_focus",
            "builder": _special_sector_comprehensive_electric,
        },
        {
            "sector_group": "balance_excluded_sector",
            "price_band": "mid_2_to_3_eok",
            "response_tier": "raw",
            "precision_target": "split_focus",
            "builder": _special_sector_split_electric,
        },
        {
            "sector_group": "balance_excluded_sector",
            "price_band": "mid_2_to_3_eok",
            "response_tier": "raw",
            "precision_target": "comprehensive_focus",
            "builder": _special_sector_comprehensive_telecom,
        },
        {
            "sector_group": "balance_excluded_sector",
            "price_band": "mid_2_to_3_eok",
            "response_tier": "raw",
            "precision_target": "split_focus",
            "builder": _special_sector_split_telecom,
        },
        {
            "sector_group": "balance_excluded_sector",
            "price_band": "mid_2_to_3_eok",
            "response_tier": "raw",
            "precision_target": "split_focus",
            "builder": _special_sector_split_fire,
        },
        {
            "sector_group": "general",
            "price_band": "sub_1_eok",
            "response_tier": "raw",
            "precision_target": "assist",
            "builder": qa_base._scenario_sparse_assistive,
        },
        {
            "sector_group": "general",
            "price_band": "mid_2_to_4_eok",
            "response_tier": "summary",
            "precision_target": "safe_summary",
            "builder": qa_base._scenario_summary_projection_safe,
        },
        {
            "sector_group": "general",
            "price_band": "mid_2_to_4_eok",
            "response_tier": "detail",
            "precision_target": "detail_explainable",
            "builder": _detail_projection_explainable,
        },
    ]


def _counts_by_axis(rows: List[Dict[str, Any]], axis: str) -> Dict[str, Dict[str, int]]:
    out: Dict[str, Dict[str, int]] = {}
    for row in rows:
        key = str(row.get(axis) or "").strip()
        if not key:
            continue
        bucket = out.setdefault(key, {"scenario_count": 0, "passed_count": 0, "failed_count": 0})
        bucket["scenario_count"] += 1
        if bool(row.get("ok")):
            bucket["passed_count"] += 1
        else:
            bucket["failed_count"] += 1
    return out


def _precision_counts(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for row in rows:
        observed = row.get("observed") if isinstance(row.get("observed"), dict) else {}
        tier = str(observed.get("precision_tier") or observed.get("precision_mode") or "").strip()
        if tier:
            out[tier] = int(out.get(tier, 0) or 0) + 1
    return out


def build_yangdo_recommendation_precision_matrix() -> Dict[str, Any]:
    est = yangdo_blackbox_api.YangdoBlackboxEstimator()
    baseline_records = [
        qa_base._record(est, uid=1001, specialty=18.0, sales3=12.0, balance=0.4, price=2.22, license_text="종합", row=1),
        qa_base._record(est, uid=1002, specialty=19.5, sales3=13.1, balance=0.5, price=2.34, license_text="종합", row=2),
        qa_base._record(est, uid=1003, specialty=21.0, sales3=14.6, balance=0.6, price=2.52, license_text="종합", row=3),
    ]
    qa_base._prime_estimator(est, baseline_records)

    scenarios: List[Dict[str, Any]] = []
    for spec in _scenario_specs(est):
        builder = spec["builder"]
        row = dict(builder(est))
        row["sector_group"] = spec["sector_group"]
        row["price_band"] = spec["price_band"]
        row["response_tier"] = spec["response_tier"]
        row["precision_target"] = spec["precision_target"]
        scenarios.append(row)

    passed = sum(1 for row in scenarios if bool(row.get("ok")))
    failed = len(scenarios) - passed
    scenario_map = {str(row.get("scenario_id") or ""): bool(row.get("ok")) for row in scenarios}
    summary = {
        "scenario_count": len(scenarios),
        "passed_count": passed,
        "failed_count": failed,
        "precision_ok": failed == 0,
        "high_precision_ok": scenario_map.get("strict_profile_match_7000_band", False),
        "fallback_precision_ok": scenario_map.get("fallback_when_hot_band_is_weak", False),
        "balance_excluded_precision_ok": scenario_map.get("balance_excluded_sector_keeps_recommendation_stable", False),
        "special_sector_comprehensive_ok": scenario_map.get("special_sector_comprehensive_uses_sales_and_scale_without_balance", False)
        and scenario_map.get("telecom_comprehensive_keeps_scale_focus_without_balance", False),
        "special_sector_split_ok": scenario_map.get("special_sector_split_uses_sales_and_capital_without_balance", False)
        and scenario_map.get("telecom_split_moves_focus_to_sales_and_capital", False)
        and scenario_map.get("fire_split_moves_focus_to_sales_and_capital", False),
        "assist_precision_ok": scenario_map.get("sparse_profile_returns_assistive_recommendation", False),
        "summary_publication_ok": scenario_map.get("summary_tier_keeps_safe_recommendation_fields_only", False),
        "detail_explainability_ok": scenario_map.get("detail_tier_keeps_explainable_recommendation_fields", False),
        "sector_groups": _counts_by_axis(scenarios, "sector_group"),
        "price_bands": _counts_by_axis(scenarios, "price_band"),
        "response_tiers": _counts_by_axis(scenarios, "response_tier"),
        "precision_counts": _precision_counts(scenarios),
    }
    next_actions = []
    if failed:
        next_actions.append("추천 정밀도 매트릭스 실패 시나리오를 먼저 수정하고 운영 패킷을 다시 생성합니다.")
    else:
        next_actions.append("추천 정밀도 매트릭스가 녹색이므로 추천 설명 UX와 임대형 상품 차등 공개 정책의 기준으로 사용합니다.")
    next_actions.append("high/assist/summary/detail 축이 동시에 유지되는지 회귀 기준으로 계속 추적합니다.")
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "yangdo_recommendation_precision_matrix_latest",
        "summary": summary,
        "scenarios": scenarios,
        "next_actions": next_actions,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Yangdo Recommendation Precision Matrix",
        "",
        f"- precision_ok: {summary.get('precision_ok')}",
        f"- scenario_count: {summary.get('scenario_count')}",
        f"- passed_count: {summary.get('passed_count')}",
        f"- failed_count: {summary.get('failed_count')}",
        f"- high_precision_ok: {summary.get('high_precision_ok')}",
        f"- fallback_precision_ok: {summary.get('fallback_precision_ok')}",
        f"- balance_excluded_precision_ok: {summary.get('balance_excluded_precision_ok')}",
        f"- assist_precision_ok: {summary.get('assist_precision_ok')}",
        f"- summary_publication_ok: {summary.get('summary_publication_ok')}",
        f"- detail_explainability_ok: {summary.get('detail_explainability_ok')}",
        "",
        "## Sector Groups",
    ]
    for key, value in sorted((summary.get("sector_groups") or {}).items()):
        lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")
    lines.extend(["", "## Price Bands"])
    for key, value in sorted((summary.get("price_bands") or {}).items()):
        lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")
    lines.extend(["", "## Response Tiers"])
    for key, value in sorted((summary.get("response_tiers") or {}).items()):
        lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")
    lines.extend(["", "## Precision Counts"])
    for key, value in sorted((summary.get("precision_counts") or {}).items()):
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Scenarios"])
    for row in payload.get("scenarios", []):
        lines.append(
            f"- {row.get('scenario_id')}: ok={row.get('ok')} sector={row.get('sector_group')} band={row.get('price_band')} tier={row.get('response_tier')}"
        )
        lines.append(f"  - why: {row.get('why')}")
        lines.append(f"  - expected: {json.dumps(row.get('expected') or {}, ensure_ascii=False)}")
        lines.append(f"  - observed: {json.dumps(row.get('observed') or {}, ensure_ascii=False)}")
    lines.extend(["", "## Next Actions"])
    for item in payload.get("next_actions", []):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a deterministic precision matrix for yangdo recommendation quality.")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_yangdo_recommendation_precision_matrix()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool((payload.get("summary") or {}).get("precision_ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
