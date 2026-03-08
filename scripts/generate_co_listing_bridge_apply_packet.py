#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "logs" / "listing_platform_bridge_policy_latest.json"
DEFAULT_SNIPPETS = ROOT / "logs" / "co_listing_bridge_snippets_latest.json"
DEFAULT_OPERATOR = ROOT / "logs" / "co_listing_bridge_operator_checklist_latest.json"
DEFAULT_PLAN = ROOT / "logs" / "co_listing_live_injection_plan_latest.json"
DEFAULT_BUNDLE = ROOT / "logs" / "co_listing_injection_bundle_latest.json"
DEFAULT_JSON = ROOT / "logs" / "co_listing_bridge_apply_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "co_listing_bridge_apply_packet_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_list(value: Any) -> List[Dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def build_co_listing_bridge_apply_packet(
    *,
    policy_path: Path,
    snippets_path: Path,
    operator_path: Path,
    plan_path: Path,
    bundle_path: Path,
) -> Dict[str, Any]:
    policy = _load_json(policy_path)
    snippets = _load_json(snippets_path)
    operator = _load_json(operator_path)
    plan = _load_json(plan_path)
    bundle = _load_json(bundle_path)

    summary_policy = policy.get("summary") if isinstance(policy.get("summary"), dict) else {}
    summary_operator = operator.get("summary") if isinstance(operator.get("summary"), dict) else {}
    summary_plan = plan.get("summary") if isinstance(plan.get("summary"), dict) else {}
    summary_bundle = bundle.get("summary") if isinstance(bundle.get("summary"), dict) else {}

    ctas = _as_list(policy.get("ctas"))
    placements = _as_list(plan.get("placements"))
    snippet_files = {
        str(row.get("placement") or ""): str(row.get("path") or "")
        for row in _as_list(snippets.get("files"))
    }

    placement_rows: List[Dict[str, Any]] = []
    for cta in ctas:
        placement = str(cta.get("placement") or "").strip()
        plan_row = next((row for row in placements if str(row.get("placement") or "") == placement), {})
        operator_row = next((row for row in _as_list(operator.get("placements")) if str(row.get("placement") or "") == placement), {})
        placement_rows.append(
            {
                "placement": placement,
                "service": str(cta.get("target_service") or ""),
                "selector": str(plan_row.get("selector") or ""),
                "selector_verified": bool(plan_row.get("selector_verified")),
                "snippet_file": snippet_files.get(placement, str(plan_row.get("snippet_file") or "")),
                "target_url": str(cta.get("target_url") or ""),
                "copy": str(cta.get("copy") or ""),
                "location_hint": str(operator_row.get("location_hint") or ""),
                "validation_hint": str(operator_row.get("validation_hint") or ""),
            }
        )

    placement_asset_ready_count = len(
        [
            row
            for row in placement_rows
            if bool(row.get("snippet_file")) and bool(row.get("target_url"))
        ]
    )
    placement_ready = all(bool(row.get("selector_verified")) and bool(row.get("snippet_file")) for row in placement_rows)
    strict_live_ready = bool(summary_plan.get("strict_live_ready"))
    artifact_ready = bool(summary_operator.get("checklist_ready")) and bool(summary_plan.get("plan_ready")) and bool(summary_bundle.get("bundle_ready")) and placement_asset_ready_count == len(placement_rows)
    apply_ready = bool(summary_operator.get("checklist_ready")) and strict_live_ready and bool(summary_bundle.get("bundle_ready")) and placement_ready

    bundle_script = str(next((row.get("path") for row in _as_list(bundle.get("files")) if str(row.get("kind") or "") == "script"), ""))
    bundle_manifest = str(next((row.get("path") for row in _as_list(bundle.get("files")) if str(row.get("kind") or "") == "manifest"), ""))

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "listing_host": str(summary_policy.get("listing_host") or "seoulmna.co.kr"),
            "platform_host": str(summary_policy.get("platform_host") or "seoulmna.kr"),
            "placement_count": len(placement_rows),
            "placement_asset_ready_count": placement_asset_ready_count,
            "placement_ready_count": len([row for row in placement_rows if row.get("selector_verified") and row.get("snippet_file")]),
            "artifact_ready": artifact_ready,
            "plan_ready": bool(summary_plan.get("plan_ready")),
            "strict_live_ready": strict_live_ready,
            "apply_ready": apply_ready,
            "bundle_script": bundle_script,
            "bundle_manifest": bundle_manifest,
            "css_file": str(summary_operator.get("css_file") or ""),
        },
        "placements": placement_rows,
        "apply_order": [
            {
                "step": 1,
                "action": "Load bridge-snippets.css into the .co.kr theme or common banner injection path.",
                "asset": str(summary_operator.get("css_file") or ""),
            },
            {
                "step": 2,
                "action": "Load the co-listing bridge JS bundle after the common CSS asset.",
                "asset": bundle_script,
            },
            {
                "step": 3,
                "action": "Verify placement selectors on live HTML and insert only the CTA bridge nodes.",
                "asset": str(summary_bundle.get("output_dir") or ""),
            },
            {
                "step": 4,
                "action": "Open representative list/detail pages and confirm that all CTA clicks route to .kr pages with UTM tags.",
                "asset": "",
            },
            {
                "step": 5,
                "action": "Confirm that .co.kr creates no /_calc iframe or direct calculator runtime.",
                "asset": "",
            },
        ],
        "next_actions": [
            "Use the selector-verified placement rows below as the only approved insertion points.",
            "Do not inline calculator runtime on .co.kr; all service demand must move to .kr.",
            "After insertion, run a browser check on a list page and at least one detail page.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# CO Listing Bridge Apply Packet",
        "",
        f"- listing_host: {summary.get('listing_host') or '(none)'}",
        f"- platform_host: {summary.get('platform_host') or '(none)'}",
        f"- placement_count: {summary.get('placement_count')}",
        f"- placement_asset_ready_count: {summary.get('placement_asset_ready_count')}",
        f"- placement_ready_count: {summary.get('placement_ready_count')}",
        f"- artifact_ready: {summary.get('artifact_ready')}",
        f"- plan_ready: {summary.get('plan_ready')}",
        f"- strict_live_ready: {summary.get('strict_live_ready')}",
        f"- apply_ready: {summary.get('apply_ready')}",
        f"- css_file: {summary.get('css_file') or '(none)'}",
        f"- bundle_script: {summary.get('bundle_script') or '(none)'}",
        "",
        "## Apply Order",
    ]
    for row in payload.get("apply_order", []):
        lines.append(f"- {row.get('step')}. {row.get('action')}")
        if row.get("asset"):
            lines.append(f"  - asset: {row.get('asset')}")
    lines.append("")
    lines.append("## Placements")
    for row in payload.get("placements", []):
        lines.append(f"- {row.get('placement')}: selector={row.get('selector')} verified={row.get('selector_verified')}")
        lines.append(f"  - service: {row.get('service')}")
        lines.append(f"  - target_url: {row.get('target_url')}")
        lines.append(f"  - snippet_file: {row.get('snippet_file')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a single apply packet for the .co.kr -> .kr live bridge insertions.")
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--snippets", type=Path, default=DEFAULT_SNIPPETS)
    parser.add_argument("--operator", type=Path, default=DEFAULT_OPERATOR)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--strict", action="store_true", help="Fail unless all live selectors are verified and the apply packet is fully ready.")
    args = parser.parse_args()

    payload = build_co_listing_bridge_apply_packet(
        policy_path=args.policy,
        snippets_path=args.snippets,
        operator_path=args.operator,
        plan_path=args.plan,
        bundle_path=args.bundle,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    ready_flag = bool(summary.get("apply_ready")) if args.strict else bool(summary.get("artifact_ready"))
    return 0 if ready_flag else 1


if __name__ == "__main__":
    raise SystemExit(main())
