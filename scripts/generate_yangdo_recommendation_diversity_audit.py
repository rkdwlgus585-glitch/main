#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
from scripts import generate_yangdo_recommendation_qa_matrix as qa_mod

DEFAULT_JSON = ROOT / "logs" / "yangdo_recommendation_diversity_audit_latest.json"
DEFAULT_MD = ROOT / "logs" / "yangdo_recommendation_diversity_audit_latest.md"


class _DetailGateway:
    def check_feature(self, resolution: Any, feature: str) -> bool:
        return feature == "estimate_detail"

    def check_system(self, resolution: Any, system: str) -> bool:
        return True


def _detail_resolution() -> Any:
    return SimpleNamespace(tenant=SimpleNamespace(plan="pro", tenant_id="seoul_main"))


def _detail_server() -> Any:
    return SimpleNamespace(tenant_gateway_enabled=True, tenant_gateway=_DetailGateway())


def _focus_count(rows: List[Dict[str, Any]], limit: int) -> int:
    values = {
        str(row.get("recommendation_focus_signature") or row.get("recommendation_focus") or "").strip()
        for row in rows[:limit]
        if str(row.get("recommendation_focus_signature") or row.get("recommendation_focus") or "").strip()
    }
    return len(values)


def _price_band_count(rows: List[Dict[str, Any]], limit: int) -> int:
    values = {
        str(row.get("recommendation_price_band") or "").strip()
        for row in rows[:limit]
        if str(row.get("recommendation_price_band") or "").strip()
    }
    return len(values)


def _precision_tier_count(rows: List[Dict[str, Any]], limit: int) -> int:
    values = {
        str(row.get("precision_tier") or "").strip()
        for row in rows[:limit]
        if str(row.get("precision_tier") or "").strip()
    }
    return len(values)


def _listing_band_count(rows: List[Dict[str, Any]], limit: int) -> int:
    values = {
        str(yangdo_blackbox_api._listing_number_band(row.get("seoul_no")))
        for row in rows[:limit]
        if int(row.get("seoul_no") or 0) > 0
    }
    return len(values)


def _max_group_count(rows: List[Dict[str, Any]], limit: int, key: str) -> int:
    counts: Dict[str, int] = {}
    for row in rows[:limit]:
        value = str(row.get(key) or "").strip()
        if not value:
            continue
        counts[value] = int(counts.get(value, 0) or 0) + 1
    return max(counts.values()) if counts else 0


def _max_listing_band_count(rows: List[Dict[str, Any]], limit: int) -> int:
    counts: Dict[str, int] = {}
    for row in rows[:limit]:
        seoul_no = int(row.get("seoul_no") or 0)
        if seoul_no <= 0:
            continue
        band = str(yangdo_blackbox_api._listing_number_band(seoul_no))
        counts[band] = int(counts.get(band, 0) or 0) + 1
    return max(counts.values()) if counts else 0


def _scenario_top3_spread(est: Any) -> Dict[str, Any]:
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
        (99.2, qa_mod._record(est, uid=7208, specialty=20.1, sales3=15.1, balance=0.6, price=3.01, license_text="종합", row=1)),
        (99.0, qa_mod._record(est, uid=7211, specialty=20.0, sales3=15.0, balance=0.6, price=2.98, license_text="종합", row=2)),
        (98.7, qa_mod._record(est, uid=7212, specialty=19.9, sales3=14.9, balance=0.6, price=3.04, license_text="종합", row=3)),
        (98.5, qa_mod._record(est, uid=6201, specialty=24.0, sales3=15.8, balance=0.6, price=3.78, license_text="종합", row=4)),
        (98.2, qa_mod._record(est, uid=5201, specialty=17.8, sales3=13.9, balance=0.6, price=2.46, license_text="종합", row=5)),
    ]
    result = yangdo_blackbox_api._build_recommendation_result(target=target, rows=rows, center=3.0, low=2.85, high=3.15, limit=4)
    recommended = list(result.get("recommended_listings") or [])
    top_three = recommended[:3]
    top_ids = [int(row.get("seoul_no") or 0) for row in top_three]
    focus_count = _focus_count(top_three, 3)
    price_count = _price_band_count(top_three, 3)
    ok = len(top_three) == 3 and len(set(top_ids)) == 3 and focus_count >= 2 and price_count >= 2
    return {
        "scenario_id": "top3_spread_without_top1_regression",
        "ok": ok,
        "expected": {
            "top3_unique_listing_count": 3,
            "top3_unique_focus_signatures_min": 2,
            "top3_unique_price_bands_min": 2,
        },
        "observed": {
            "top_ids": top_ids,
            "top3_focus_count": focus_count,
            "top3_price_band_count": price_count,
            "focus_signatures": [str(row.get("recommendation_focus_signature") or "") for row in top_three],
            "price_bands": [str(row.get("recommendation_price_band") or "") for row in top_three],
            "meta": dict(result.get("recommendation_meta") or {}),
        },
        "why": "상위 추천이 첫 추천을 해치지 않으면서도 가격대와 추천축이 한 가지로만 몰리지 않는지 검사합니다.",
    }


def _scenario_detail_contract_hides_internal_fields(est: Any) -> Dict[str, Any]:
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
        (99.1, qa_mod._record(est, uid=7208, specialty=20.1, sales3=15.1, balance=0.6, price=3.01, license_text="종합", row=1)),
        (98.5, qa_mod._record(est, uid=6201, specialty=24.0, sales3=15.8, balance=0.6, price=3.78, license_text="종합", row=2)),
        (96.4, qa_mod._record(est, uid=4301, specialty=31.0, sales3=11.4, balance=0.4, price=2.02, license_text="건축", row=3)),
    ]
    rec_result = yangdo_blackbox_api._build_recommendation_result(target=target, rows=rows, center=3.0, low=2.85, high=3.15, limit=3)
    payload = {
        "ok": True,
        "generated_at": "2026-03-07T10:00:00",
        "estimate_center_eok": 3.0,
        "estimate_low_eok": 2.85,
        "estimate_high_eok": 3.15,
        "confidence_score": 76.0,
        "confidence_percent": 76,
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
    projected = yangdo_blackbox_api._project_estimate_result(_detail_server(), _detail_resolution(), payload)
    first = dict((projected.get("recommended_listings") or [{}])[0])
    hidden_keys = {"recommendation_score", "similarity", "recommendation_focus_signature", "recommendation_price_band"}
    ok = bool(first) and not any(key in first for key in hidden_keys)
    return {
        "scenario_id": "detail_projection_hides_internal_diversity_fields",
        "ok": ok,
        "expected": {"hidden_keys": sorted(hidden_keys)},
        "observed": {
            "projected_keys": sorted(first.keys()),
            "detail_count": len(list(projected.get("recommended_listings") or [])),
        },
        "why": "상세 tier도 설명 가능한 필드만 공개하고 raw score와 내부 다양성 신호는 숨겨야 합니다.",
    }


def _scenario_precision_mix(est: Any) -> Dict[str, Any]:
    target = est._target_from_payload(
        {
            "license_text": "건축",
            "specialty": 11.0,
            "sales3_eok": 5.1,
            "sales5_eok": 6.8,
            "balance_eok": 0.2,
            "capital_eok": 2.6,
            "company_type": "주식회사",
        }
    )
    rows = [
        (97.4, qa_mod._record(est, uid=5301, specialty=11.2, sales3=5.4, balance=0.2, price=1.08, license_text="건축", row=1)),
        (92.3, qa_mod._record(est, uid=5302, specialty=14.8, sales3=7.6, balance=0.2, price=1.26, license_text="건축", row=2)),
        (85.4, qa_mod._record(est, uid=5303, specialty=27.0, sales3=14.8, balance=0.2, price=1.55, license_text="건축", row=3)),
        (84.6, qa_mod._record(est, uid=5304, specialty=32.0, sales3=16.4, balance=0.2, price=1.64, license_text="건축", row=4)),
    ]
    result = yangdo_blackbox_api._build_recommendation_result(target=target, rows=rows, center=1.12, low=1.0, high=1.24, limit=4)
    recommended = list(result.get("recommended_listings") or [])
    precision_count = _precision_tier_count(recommended, 4)
    unique_ids = len({int(row.get("seoul_no") or 0) for row in recommended if int(row.get("seoul_no") or 0) > 0})
    listing_bridge_ok = all("seoulmna.co.kr" in str(row.get("url") or "") for row in recommended if isinstance(row, dict))
    ok = precision_count >= 2 and unique_ids == len(recommended) and listing_bridge_ok
    return {
        "scenario_id": "precision_mix_and_listing_bridge_consistency",
        "ok": ok,
        "expected": {
            "unique_precision_tiers_min": 2,
            "unique_listing_count_matches": True,
            "listing_bridge_host": "seoulmna.co.kr",
        },
        "observed": {
            "precision_tiers": [str(row.get("precision_tier") or "") for row in recommended],
            "unique_precision_tier_count": precision_count,
            "unique_listing_count": unique_ids,
            "recommended_count": len(recommended),
            "urls": [str(row.get("url") or "") for row in recommended],
        },
        "why": "추천이 한 등급에만 몰리지 않고, 매물 브리지는 계속 .co.kr로 유지되어야 합니다.",
    }


def _scenario_listing_band_spread(est: Any) -> Dict[str, Any]:
    target = est._target_from_payload(
        {
            "license_text": "종합",
            "specialty": 18.0,
            "sales3_eok": 12.0,
            "sales5_eok": 16.5,
            "balance_eok": 0.5,
            "capital_eok": 3.0,
            "company_type": "주식회사",
        }
    )
    rows = [
        (98.6, qa_mod._record(est, uid=1203, specialty=18.1, sales3=12.1, balance=0.5, price=2.18, license_text="종합", row=1)),
        (98.2, qa_mod._record(est, uid=3408, specialty=18.0, sales3=11.9, balance=0.5, price=2.21, license_text="종합", row=2)),
        (97.8, qa_mod._record(est, uid=5609, specialty=17.9, sales3=12.2, balance=0.5, price=2.24, license_text="종합", row=3)),
        (97.4, qa_mod._record(est, uid=7812, specialty=18.3, sales3=12.4, balance=0.5, price=2.27, license_text="종합", row=4)),
    ]
    result = yangdo_blackbox_api._build_recommendation_result(target=target, rows=rows, center=2.22, low=2.08, high=2.34, limit=4)
    recommended = list(result.get("recommended_listings") or [])
    listing_band_count = _listing_band_count(recommended, 4)
    focus_count = _focus_count(recommended, 4)
    ok = len(recommended) == 4 and listing_band_count >= 3
    return {
        "scenario_id": "listing_band_spread_under_close_scores",
        "ok": ok,
        "expected": {
            "unique_listing_band_count_min": 3,
        },
        "observed": {
            "top_ids": [int(row.get("seoul_no") or 0) for row in recommended],
            "listing_bands": [int(yangdo_blackbox_api._listing_number_band(row.get("seoul_no"))) for row in recommended],
            "unique_listing_band_count": listing_band_count,
            "unique_focus_signature_count": focus_count,
        },
        "why": "점수가 비슷한 후보가 이어질 때도 같은 번호대나 같은 추천축이 과대표되지 않는지 확인합니다.",
    }


def _scenario_cluster_concentration_guard(est: Any) -> Dict[str, Any]:
    target = est._target_from_payload(
        {
            "license_text": "종합",
            "specialty": 16.0,
            "sales3_eok": 10.0,
            "sales5_eok": 14.0,
            "balance_eok": 0.4,
            "capital_eok": 3.0,
            "company_type": "주식회사",
        }
    )
    rows = [
        (98.9, qa_mod._record(est, uid=3602, specialty=16.1, sales3=10.2, balance=0.4, price=2.12, license_text="종합", row=1)),
        (98.6, qa_mod._record(est, uid=5208, specialty=16.0, sales3=10.1, balance=0.4, price=2.16, license_text="종합", row=2)),
        (98.3, qa_mod._record(est, uid=6201, specialty=16.4, sales3=10.8, balance=0.4, price=2.38, license_text="종합", row=3)),
        (98.0, qa_mod._record(est, uid=7208, specialty=15.6, sales3=9.7, balance=0.4, price=1.94, license_text="종합", row=4)),
    ]
    result = yangdo_blackbox_api._build_recommendation_result(target=target, rows=rows, center=2.14, low=2.0, high=2.28, limit=4)
    recommended = list(result.get("recommended_listings") or [])
    max_listing_band = _max_listing_band_count(recommended, 4)
    max_focus_group = _max_group_count(recommended, 4, "recommendation_focus_signature")
    ok = len(recommended) == 4 and max_listing_band <= 2 and max_focus_group <= 2
    return {
        "scenario_id": "cluster_concentration_guard_under_close_scores",
        "ok": ok,
        "expected": {
            "max_listing_band_count": 2,
            "max_focus_signature_count": 2,
        },
        "observed": {
            "top_ids": [int(row.get("seoul_no") or 0) for row in recommended],
            "listing_bands": [int(yangdo_blackbox_api._listing_number_band(row.get("seoul_no"))) for row in recommended],
            "focus_signatures": [str(row.get("recommendation_focus_signature") or "") for row in recommended],
            "max_listing_band_count": max_listing_band,
            "max_focus_signature_count": max_focus_group,
        },
        "why": "상위 추천이 같은 번호대 cluster나 동일 추천축에 과도하게 몰리면 시장 탐색 후보군의 폭이 급격히 줄어듭니다.",
    }


def _scenario_top_rank_signature_concentration_guard(est: Any) -> Dict[str, Any]:
    target = est._target_from_payload(
        {
            "license_text": "종합",
            "specialty": 19.0,
            "sales3_eok": 13.0,
            "sales5_eok": 17.5,
            "balance_eok": 0.5,
            "capital_eok": 3.1,
            "company_type": "주식회사",
        }
    )
    rows = [
        (98.8, qa_mod._record(est, uid=8101, specialty=19.1, sales3=13.2, balance=0.5, price=2.62, license_text="종합", row=1)),
        (98.6, qa_mod._record(est, uid=8104, specialty=18.9, sales3=12.9, balance=0.5, price=2.66, license_text="종합", row=2)),
        (98.4, qa_mod._record(est, uid=5102, specialty=19.4, sales3=13.6, balance=0.5, price=2.28, license_text="종합", row=3)),
        (98.2, qa_mod._record(est, uid=6105, specialty=18.5, sales3=12.5, balance=0.5, price=3.08, license_text="종합", row=4)),
        (97.9, qa_mod._record(est, uid=7107, specialty=19.7, sales3=13.8, balance=0.5, price=2.94, license_text="종합", row=5)),
    ]
    result = yangdo_blackbox_api._build_recommendation_result(target=target, rows=rows, center=2.72, low=2.48, high=2.96, limit=5)
    recommended = list(result.get("recommended_listings") or [])
    top_three = recommended[:3]
    max_top_focus = _max_group_count(top_three, 3, "recommendation_focus_signature")
    unique_top_focus = _focus_count(top_three, 3)
    max_top_price_band = _max_group_count(top_three, 3, "recommendation_price_band")
    ok = len(top_three) == 3 and max_top_focus <= 2 and unique_top_focus >= 2 and max_top_price_band <= 2
    return {
        "scenario_id": "top_rank_signature_concentration_guard",
        "ok": ok,
        "expected": {
            "top3_unique_focus_signature_count_min": 2,
            "top3_max_focus_signature_count": 2,
            "top3_max_price_band_count": 2,
        },
        "observed": {
            "top_ids": [int(row.get("seoul_no") or 0) for row in top_three],
            "focus_signatures": [str(row.get("recommendation_focus_signature") or "") for row in top_three],
            "price_bands": [str(row.get("recommendation_price_band") or "") for row in top_three],
            "top3_unique_focus_signature_count": unique_top_focus,
            "top3_max_focus_signature_count": max_top_focus,
            "top3_max_price_band_count": max_top_price_band,
        },
        "why": "상위 2~3개 추천이 사실상 같은 설명 서명만 반복하면 추천 다양성이 살아 있어도 사용자 체감은 단조로워집니다.",
    }


def _scenario_price_band_concentration_guard(est: Any) -> Dict[str, Any]:
    target = est._target_from_payload(
        {
            "license_text": "건축",
            "specialty": 10.5,
            "sales3_eok": 5.0,
            "sales5_eok": 6.6,
            "balance_eok": 0.2,
            "capital_eok": 2.6,
            "company_type": "주식회사",
        }
    )
    rows = [
        (98.5, qa_mod._record(est, uid=2201, specialty=10.7, sales3=5.2, balance=0.2, price=1.18, license_text="건축", row=1)),
        (98.1, qa_mod._record(est, uid=3204, specialty=10.4, sales3=4.9, balance=0.2, price=1.92, license_text="건축", row=2)),
        (97.8, qa_mod._record(est, uid=4207, specialty=10.6, sales3=5.1, balance=0.2, price=2.48, license_text="건축", row=3)),
        (97.5, qa_mod._record(est, uid=5208, specialty=10.8, sales3=5.4, balance=0.2, price=3.16, license_text="건축", row=4)),
    ]
    result = yangdo_blackbox_api._build_recommendation_result(target=target, rows=rows, center=2.05, low=1.82, high=2.32, limit=4)
    recommended = list(result.get("recommended_listings") or [])
    unique_price_bands = _price_band_count(recommended, 4)
    max_price_band = _max_group_count(recommended, 4, "recommendation_price_band")
    ok = len(recommended) == 4 and unique_price_bands >= 3 and max_price_band <= 2
    return {
        "scenario_id": "price_band_concentration_guard_under_close_scores",
        "ok": ok,
        "expected": {
            "unique_price_band_count_min": 3,
            "max_price_band_count": 2,
        },
        "observed": {
            "top_ids": [int(row.get("seoul_no") or 0) for row in recommended],
            "price_bands": [str(row.get("recommendation_price_band") or "") for row in recommended],
            "unique_price_band_count": unique_price_bands,
            "max_price_band_count": max_price_band,
        },
        "why": "상위 추천이 특정 가격대에만 과집중되면 추천 폭은 넓어 보여도 실제 시장 선택지는 좁아집니다.",
    }


def build_yangdo_recommendation_diversity_audit() -> Dict[str, Any]:
    est = yangdo_blackbox_api.YangdoBlackboxEstimator()
    baseline_records = [
        qa_mod._record(est, uid=1001, specialty=18.0, sales3=12.0, balance=0.4, price=2.22, license_text="종합", row=1),
        qa_mod._record(est, uid=1002, specialty=19.5, sales3=13.1, balance=0.5, price=2.34, license_text="종합", row=2),
        qa_mod._record(est, uid=1003, specialty=21.0, sales3=14.6, balance=0.6, price=2.52, license_text="종합", row=3),
    ]
    qa_mod._prime_estimator(est, baseline_records)

    scenarios = [
        _scenario_top3_spread(est),
        _scenario_detail_contract_hides_internal_fields(est),
        _scenario_precision_mix(est),
        _scenario_listing_band_spread(est),
        _scenario_cluster_concentration_guard(est),
        _scenario_top_rank_signature_concentration_guard(est),
        _scenario_price_band_concentration_guard(est),
    ]
    passed = sum(1 for row in scenarios if bool(row.get("ok")))
    failed = len(scenarios) - passed
    summary = {
        "scenario_count": len(scenarios),
        "passed_count": passed,
        "failed_count": failed,
        "diversity_ok": failed == 0,
        "top1_stability_ok": bool(scenarios[0].get("ok")),
        "price_band_spread_ok": bool(scenarios[0].get("ok")),
        "focus_signature_spread_ok": bool(scenarios[0].get("ok")),
        "detail_projection_contract_ok": bool(scenarios[1].get("ok")),
        "precision_tier_spread_ok": bool(scenarios[2].get("ok")),
        "unique_listing_ok": bool(scenarios[2].get("ok")),
        "listing_bridge_ok": bool(scenarios[2].get("ok")),
        "listing_band_spread_ok": bool(scenarios[3].get("ok")),
        "cluster_concentration_ok": bool(scenarios[4].get("ok")),
        "top_rank_signature_concentration_ok": bool(scenarios[5].get("ok")),
        "price_band_concentration_ok": bool(scenarios[6].get("ok")),
    }
    next_actions: List[str] = []
    if failed:
        next_actions.append("추천 상위 결과가 특정 패턴으로 다시 몰리는지 확인하고 diversity rerank penalty를 조정합니다.")
    else:
        next_actions.append("추천 다양성 보정은 녹색입니다. 다음은 /yangdo 서비스 카피와 임대 상품 노출 차등을 더 정교화합니다.")
    next_actions.append("detail tier에는 설명 가능한 필드만 공개하고 raw score와 내부 다양성 신호는 계속 internal로 유지합니다.")
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "yangdo_recommendation_diversity_audit_latest",
        "summary": summary,
        "scenarios": scenarios,
        "next_actions": next_actions,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Yangdo Recommendation Diversity Audit",
        "",
        f"- diversity_ok: {summary.get('diversity_ok')}",
        f"- scenario_count: {summary.get('scenario_count')}",
        f"- passed_count: {summary.get('passed_count')}",
        f"- failed_count: {summary.get('failed_count')}",
        f"- top1_stability_ok: {summary.get('top1_stability_ok')}",
        f"- price_band_spread_ok: {summary.get('price_band_spread_ok')}",
        f"- focus_signature_spread_ok: {summary.get('focus_signature_spread_ok')}",
        f"- detail_projection_contract_ok: {summary.get('detail_projection_contract_ok')}",
        f"- precision_tier_spread_ok: {summary.get('precision_tier_spread_ok')}",
        f"- unique_listing_ok: {summary.get('unique_listing_ok')}",
        f"- listing_bridge_ok: {summary.get('listing_bridge_ok')}",
        f"- listing_band_spread_ok: {summary.get('listing_band_spread_ok')}",
        f"- cluster_concentration_ok: {summary.get('cluster_concentration_ok')}",
        f"- top_rank_signature_concentration_ok: {summary.get('top_rank_signature_concentration_ok')}",
        f"- price_band_concentration_ok: {summary.get('price_band_concentration_ok')}",
        "",
        "## Scenarios",
    ]
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
    parser = argparse.ArgumentParser(description="Audit diversity and explainability drift in yangdo recommendations.")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_yangdo_recommendation_diversity_audit()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if payload.get("summary", {}).get("diversity_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
