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

DEFAULT_JSON = ROOT / "logs" / "yangdo_recommendation_contract_audit_latest.json"
DEFAULT_MD = ROOT / "logs" / "yangdo_recommendation_contract_audit_latest.md"


class _FakeGateway:
    def __init__(self, features: List[str] | None = None):
        self._features = set(features or [])

    def check_feature(self, resolution: Any, feature: str) -> bool:
        return feature in self._features

    def check_system(self, resolution: Any, system: str) -> bool:
        return True


def _sample_result() -> Dict[str, Any]:
    return {
        "ok": True,
        "generated_at": "2026-03-07T10:00:00",
        "estimate_center_eok": 3.0,
        "estimate_low_eok": 2.8,
        "estimate_high_eok": 3.2,
        "confidence_score": 74.0,
        "confidence_percent": 74,
        "publication_mode": "full",
        "publication_label": "range",
        "publication_reason": "",
        "price_source_tier": "B",
        "price_source_label": "shared market data",
        "price_sample_count": 6,
        "price_is_estimate": True,
        "price_range_kind": "AI_ESTIMATED_RANGE",
        "price_source_channel": "SHARED_MARKET_LISTING_DATASET",
        "price_disclaimer": "Reference only.",
        "recommendation_meta": {
            "recommendation_version": "listing_recommender_v2",
            "recommended_count": 2,
            "precision_mode": "balanced",
        },
        "recommended_listings": [
            {
                "seoul_no": 7208,
                "license_text": "general",
                "display_low_eok": 2.9,
                "display_high_eok": 3.1,
                "recommendation_label": "priority review",
                "recommendation_focus": "license match, sales scale, price band",
                "recommendation_score": 88.1,
                "precision_tier": "high",
                "fit_summary": "License, sales scale, and price band align well.",
                "matched_axes": ["license match", "sales scale", "price band"],
                "mismatch_flags": ["recent 3-year sales gap"],
                "reasons": ["license composition matches", "sales scale is similar"],
                "recommendation_focus_signature": "license|sales|price:center",
                "recommendation_price_band": "center",
                "similarity": 0.86,
                "url": "https://seoulmna.co.kr/mna/7208",
            }
        ],
        "neighbors": [{"seoul_no": 1}],
    }


def _project(features: List[str], plan: str) -> Dict[str, Any]:
    server = SimpleNamespace(
        tenant_gateway_enabled=True,
        tenant_gateway=_FakeGateway(features=features),
    )
    resolution = SimpleNamespace(
        tenant=SimpleNamespace(plan=plan, tenant_id=f"{plan}_tenant"),
    )
    return yangdo_blackbox_api._project_estimate_result(server, resolution, _sample_result())


def build_contract_audit() -> Dict[str, Any]:
    summary_payload = _project([], "standard")
    detail_payload = _project(["estimate_detail"], "pro")
    internal_payload = _project(["estimate_internal"], "pro_internal")

    summary_listing = dict((summary_payload.get("recommended_listings") or [{}])[0])
    detail_listing = dict((detail_payload.get("recommended_listings") or [{}])[0])
    internal_listing = dict((internal_payload.get("recommended_listings") or [{}])[0])

    summary_safe = (
        "recommendation_meta" in summary_payload
        and "recommended_listings" in summary_payload
        and "recommendation_score" not in summary_listing
        and "precision_tier" not in summary_listing
        and "fit_summary" not in summary_listing
        and "matched_axes" not in summary_listing
        and "mismatch_flags" not in summary_listing
        and "recommendation_focus_signature" not in summary_listing
        and "recommendation_price_band" not in summary_listing
        and "similarity" not in summary_listing
    )
    detail_explainable = (
        "recommendation_meta" in detail_payload
        and "recommended_listings" in detail_payload
        and "neighbors" not in detail_payload
        and "precision_tier" in detail_listing
        and "fit_summary" in detail_listing
        and "matched_axes" in detail_listing
        and "mismatch_flags" in detail_listing
        and "reasons" in detail_listing
        and "recommendation_focus" in detail_listing
        and "recommendation_score" not in detail_listing
        and "recommendation_focus_signature" not in detail_listing
        and "recommendation_price_band" not in detail_listing
        and "similarity" not in detail_listing
    )
    internal_debug_visible = (
        "recommendation_meta" in internal_payload
        and "recommended_listings" in internal_payload
        and "neighbors" in internal_payload
        and "tenant_id" in internal_payload
        and "recommendation_score" in internal_listing
        and "recommendation_focus_signature" in internal_listing
        and "recommendation_price_band" in internal_listing
        and "similarity" in internal_listing
    )

    contract_ok = summary_safe and detail_explainable and internal_debug_visible
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "contract_ok": contract_ok,
            "summary_safe": summary_safe,
            "detail_explainable": detail_explainable,
            "internal_debug_visible": internal_debug_visible,
            "summary_keys": sorted(summary_payload.keys()),
            "detail_keys": sorted(detail_payload.keys()),
            "internal_keys": sorted(internal_payload.keys()),
        },
        "tiers": {
            "summary": {
                "response_policy": summary_payload.get("response_policy"),
                "recommended_listing_keys": sorted(summary_listing.keys()),
            },
            "detail": {
                "response_policy": detail_payload.get("response_policy"),
                "recommended_listing_keys": sorted(detail_listing.keys()),
            },
            "internal": {
                "response_policy": internal_payload.get("response_policy"),
                "recommended_listing_keys": sorted(internal_listing.keys()),
            },
        },
        "next_actions": (
            ["summary/detail/internal recommendation contract is aligned."]
            if contract_ok
            else ["Fix response-tier recommendation field separation before expanding partner rental exposure."]
        ),
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Yangdo Recommendation Contract Audit",
        "",
        f"- contract_ok: {summary.get('contract_ok')}",
        f"- summary_safe: {summary.get('summary_safe')}",
        f"- detail_explainable: {summary.get('detail_explainable')}",
        f"- internal_debug_visible: {summary.get('internal_debug_visible')}",
        "",
        "## Tiers",
    ]
    tiers = payload.get("tiers") if isinstance(payload.get("tiers"), dict) else {}
    for key in ("summary", "detail", "internal"):
        row = tiers.get(key) if isinstance(tiers.get(key), dict) else {}
        lines.append(f"- {key}: keys={', '.join(row.get('recommended_listing_keys') or []) or '(none)'}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit summary/detail/internal recommendation field separation.")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_contract_audit()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool((payload.get("summary") or {}).get("contract_ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
