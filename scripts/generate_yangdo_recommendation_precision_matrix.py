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
    summary = {
        "scenario_count": len(scenarios),
        "passed_count": passed,
        "failed_count": failed,
        "precision_ok": failed == 0,
        "high_precision_ok": bool(scenarios[0].get("ok")),
        "fallback_precision_ok": bool(scenarios[1].get("ok")),
        "balance_excluded_precision_ok": bool(scenarios[2].get("ok")),
        "assist_precision_ok": bool(scenarios[3].get("ok")),
        "summary_publication_ok": bool(scenarios[4].get("ok")),
        "detail_explainability_ok": bool(scenarios[5].get("ok")),
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
