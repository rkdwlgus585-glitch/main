#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPERATIONS = ROOT / "logs" / "operations_packet_latest.json"
DEFAULT_ATTORNEY = ROOT / "logs" / "attorney_handoff_latest.json"
DEFAULT_STAGING_APPLY = ROOT / "logs" / "wordpress_staging_apply_plan_latest.json"
DEFAULT_WP_APPLY = ROOT / "logs" / "wp_surface_lab_apply_latest.json"
DEFAULT_WP_VERIFY = ROOT / "logs" / "wp_surface_lab_page_verify_latest.json"
DEFAULT_WIDGET_CATALOG = ROOT / "logs" / "widget_rental_catalog_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _build_priorities(
    *,
    operations: Dict[str, Any],
    attorney: Dict[str, Any],
    staging_apply: Dict[str, Any],
    wp_apply: Dict[str, Any],
    wp_verify: Dict[str, Any],
    widget_catalog: Dict[str, Any],
    operations_path: Path,
    attorney_path: Path,
    staging_apply_path: Path,
    wp_apply_path: Path,
    wp_verify_path: Path,
    widget_catalog_path: Path,
) -> Dict[str, Any]:
    decisions = operations.get("decisions") if isinstance(operations.get("decisions"), dict) else {}
    topology = operations.get("topology") if isinstance(operations.get("topology"), dict) else {}
    required_inputs = operations.get("required_inputs") if isinstance(operations.get("required_inputs"), dict) else {}
    partner_common = _as_list(required_inputs.get("partner_common"))
    tracks = attorney.get("tracks") if isinstance(attorney.get("tracks"), list) else []
    staging_summary = staging_apply.get("summary") if isinstance(staging_apply.get("summary"), dict) else {}
    wp_apply_summary = wp_apply.get("summary") if isinstance(wp_apply.get("summary"), dict) else {}
    wp_verify_summary = wp_verify.get("summary") if isinstance(wp_verify.get("summary"), dict) else {}
    catalog_summary = widget_catalog.get("summary") if isinstance(widget_catalog.get("summary"), dict) else {}
    packaging = widget_catalog.get("packaging") if isinstance(widget_catalog.get("packaging"), dict) else {}

    immediate_blockers: List[Dict[str, Any]] = []
    if str(decisions.get("seoul_live_decision") or "") != "ready":
        immediate_blockers.append(
            {
                "priority": 1,
                "category": "platform_launch",
                "title": "SeoulMNA live release final confirmation",
                "why": "The platform and calculators are prepared, but the live mount is still held by the final release guard.",
                "action": "Run deploy_seoul_widget_embed_release.py with --confirm-live YES after the final operator check.",
                "evidence": "operations_packet_latest.json: decisions.seoul_live_decision",
            }
        )
    wp_runtime_decision = str(decisions.get("wp_runtime_decision") or "")
    wp_surface_apply_decision = str(decisions.get("wp_surface_apply_decision") or "")
    wp_verification_ok = bool(wp_verify_summary.get("verification_ok"))
    if wp_runtime_decision == "scaffold_ready_runtime_missing":
        immediate_blockers.append(
            {
                "priority": 1,
                "category": "wordpress_runtime",
                "title": "Close the WordPress lab runtime gap",
                "why": "The Astra/WordPress platform path is apply-ready, but runtime verification cannot execute until Docker or an equivalent local runtime exists.",
                "action": "Install Docker Desktop or provide an equivalent isolated runtime, then run the WordPress runtime/bootstrap/apply/verify chain.",
                "evidence": "wp_surface_lab_runtime_validation_latest.json: summary.runtime_ready=false",
            }
        )
    elif wp_surface_apply_decision not in {"verified"} and not wp_verification_ok:
        immediate_blockers.append(
            {
                "priority": 1,
                "category": "wordpress_verification",
                "title": "Close the WordPress page verification gap",
                "why": "The WordPress lab runtime is available, but the platform pages are not yet verified against the CTA-only home and lazy-gate service-page policy.",
                "action": "Run verify_wp_surface_lab_pages.py and clear any homepage/service-page policy drift before live adoption.",
                "evidence": "wp_surface_lab_page_verify_latest.json: summary.verification_ok=false",
            }
        )
    if str(decisions.get("partner_activation_decision") or "") != "ready":
        immediate_blockers.append(
            {
                "priority": 1,
                "category": "partner_activation",
                "title": "Collect the shared partner onboarding inputs once",
                "why": "All current partner offerings share the same missing input set, so one standardized intake packet removes the largest commercialization blocker.",
                "action": f"Collect these once for each partner: {', '.join(partner_common) or 'partner_proof_url, partner_api_key, partner_data_source_approval' }.",
                "evidence": "operations_packet_latest.json: required_inputs.partner_common",
            }
        )
    if decisions.get("yangdo_recommendation_qa_ok") is False:
        immediate_blockers.append(
            {
                "priority": 1,
                "category": "yangdo_recommendation_qa",
                "title": "Restore recommendation precision before live expansion",
                "why": "The yangdo engine now sells both range estimation and similar-listing recommendation, so recommendation regressions are a direct product risk.",
                "action": "Fix the failing recommendation QA scenarios and regenerate the canonical operations packet before live rollout.",
                "evidence": "operations_packet_latest.json: decisions.yangdo_recommendation_qa_ok",
            }
        )

    structural_improvements: List[Dict[str, Any]] = [
        {
            "priority": 2,
            "category": "wordpress_platform",
            "title": "Keep calculators off the initial .kr render path",
            "why": "CTA-only home/knowledge pages and lazy gates on service pages remain the lowest-risk mix for SEO, speed, and traffic control.",
            "action": "Do not inline iframes on the homepage; keep the service-page lazy gate policy as the only public calculator entry path.",
            "evidence": "wordpress_platform_strategy_latest.json: calculator_mount_decision",
        },
        {
            "priority": 2,
            "category": "site_role_split",
            "title": "Preserve the .kr / .co.kr role split",
            "why": f"The platform host ({topology.get('main_platform_host') or 'seoulmna.kr'}) and listing host ({topology.get('listing_market_host') or 'seoulmna.co.kr'}) should not collapse into one runtime surface.",
            "action": "Keep .co.kr listing-focused and route calculator demand back to .kr service pages and .kr/_calc/*.",
            "evidence": "operations_packet_latest.json: topology",
        },
        {
            "priority": 2,
            "category": "apply_chain",
            "title": "Promote the WordPress apply bundle to the default staging path",
            "why": "The WP-CLI apply bundle is now the shortest reproducible route from blueprint assets to an actual rendered WordPress platform.",
            "action": "Use the generated apply-platform-blueprints.php bundle instead of manual page editing whenever staging is refreshed.",
            "evidence": "wp_surface_lab_apply_latest.json + wordpress_staging_apply_plan_latest.json",
        },
        {
            "priority": 2,
            "category": "yangdo_recommendation_experience",
            "title": "Keep the yangdo service page framed as estimate plus recommendation",
            "why": "The product is no longer just a price calculator. The .kr service page and operator packet should keep exposing recommendation precision and recommendation reasons as part of the value proposition.",
            "action": "Maintain recommendation explainer copy, recommendation QA, and safe summary projection together as one release gate.",
            "evidence": "operations_packet_latest.json: summaries.yangdo_recommendation_qa",
        },
    ]

    patent_hardening: List[Dict[str, Any]] = []
    for track in tracks:
        if not isinstance(track, dict):
            continue
        track_id = str(track.get("track_id") or "").strip()
        system_id = str(track.get("system_id") or "").strip()
        position = track.get("attorney_position") if isinstance(track.get("attorney_position"), dict) else {}
        claim_focus = _as_list(position.get("claim_focus"))
        avoid_in_claims = _as_list(position.get("avoid_in_claims"))
        if track_id == "P":
            patent_hardening.append(
                {
                    "priority": 3,
                    "category": "patent_platform_boundary",
                    "title": "Keep platform details outside the core independent claims",
                    "why": "The shared platform supports commercialization, but over-claiming WordPress, routing, or billing internals would weaken A/B focus.",
                    "action": "Use the platform track as business/implementation context only and keep A/B centered on engine logic.",
                    "evidence": f"attorney_handoff_latest.json: track {track_id}",
                }
            )
            continue
        if track_id == "A":
            focus_summary = "duplicate clustering, contamination filtering, and confidence-controlled disclosure"
            exclusion_summary = "site-specific crawling details and UI text"
        elif track_id == "B":
            focus_summary = "typed criteria, verified rule mapping, and manual-review gating"
            exclusion_summary = "generic checklist UI and document storage details"
        else:
            focus_summary = ", ".join(claim_focus[:2]) or "the core engine flow"
            exclusion_summary = ", ".join(avoid_in_claims[:2]) or "site/UI/deployment specifics"
        patent_hardening.append(
            {
                "priority": 3,
                "category": f"patent_{system_id}",
                "title": f"Freeze {track_id} around the current core logic, not the deployment shell",
                "why": f"Track {track_id} is strongest when the claims stay anchored on {focus_summary}.",
                "action": f"Retain the current exclusions in drafting: {exclusion_summary}.",
                "evidence": f"attorney_handoff_latest.json: track {track_id}",
            }
        )

    commercialization_gaps: List[Dict[str, Any]] = [
        {
            "priority": 2,
            "category": "rental_packaging",
            "title": "Turn the offer templates into a standard commercial menu",
            "why": f"There are already {catalog_summary.get('standard_offering_count', 0)} standard and {catalog_summary.get('pro_offering_count', 0)} pro offerings in config, but they need a single canonical commercial view.",
            "action": "Use the widget rental catalog as the commercial source of truth for widget, API, and internal-unlimited packaging.",
            "evidence": "widget_rental_catalog_latest.json",
        },
        {
            "priority": 2,
            "category": "partner_intake",
            "title": "Standardize one onboarding packet for all current partner offerings",
            "why": "The partner matrix shows all current partner offerings become ready after the same three inputs are supplied.",
            "action": f"Issue one reusable onboarding packet covering: {', '.join(partner_common) or 'partner_proof_url, partner_api_key, partner_data_source_approval'}.",
            "evidence": "operations_packet_latest.json + widget_rental_catalog_latest.json",
        },
        {
            "priority": 2,
            "category": "internal_role_protection",
            "title": "Keep Seoul internal unlimited separate from partner plans",
            "why": "Seoul internal tenants should remain unlimited so .co.kr can consume the tools without being throttled like a partner tenant.",
            "action": "Do not collapse pro_internal into partner pricing. Preserve it as an internal-only lane.",
            "evidence": "widget_rental_catalog_latest.json: packaging.internal_unlimited",
        },
    ]

    top_next_actions = []
    for group in (immediate_blockers, structural_improvements, commercialization_gaps, patent_hardening):
        for item in group:
            top_next_actions.append(item)
    top_next_actions = sorted(top_next_actions, key=lambda row: (int(row.get("priority", 99) or 99), str(row.get("category") or "")))[:5]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_paths": {
            "operations_packet": str(operations_path.resolve()),
            "attorney_handoff": str(attorney_path.resolve()),
            "wordpress_staging_apply_plan": str(staging_apply_path.resolve()),
            "wp_surface_lab_apply": str(wp_apply_path.resolve()),
            "wp_surface_lab_page_verify": str(wp_verify_path.resolve()),
            "widget_rental_catalog": str(widget_catalog_path.resolve()),
        },
        "summary": {
            "immediate_blocker_count": len(immediate_blockers),
            "structural_improvement_count": len(structural_improvements),
            "patent_hardening_count": len(patent_hardening),
            "commercialization_gap_count": len(commercialization_gaps),
            "top_action_count": len(top_next_actions),
            "wp_runtime_ready": wp_runtime_decision in {"runtime_running", "runtime_launch_ready"},
            "wp_page_verification_ok": wp_verification_ok,
            "wp_apply_bundle_ready": bool(wp_apply_summary.get("bundle_ready")),
            "staging_cutover_ready": bool(staging_summary.get("cutover_ready")),
            "rental_catalog_ready": bool(catalog_summary),
        },
        "immediate_blockers": immediate_blockers,
        "structural_improvements": structural_improvements,
        "patent_hardening": patent_hardening,
        "commercialization_gaps": commercialization_gaps,
        "top_next_actions": top_next_actions,
        "notes": [
            "This loop intentionally favors platform completion and commercialization blockers before late-stage patent polishing.",
            "If a future batch closes the WordPress runtime and live release blockers, the next priority should shift to automated partner onboarding intake and final attorney adjustment.",
            f"Current standard/pro offering counts: {catalog_summary.get('standard_offering_count', 0)}/{catalog_summary.get('pro_offering_count', 0)}.",
            f"Current partner widget/API packaging: {', '.join((packaging.get('partner_rental') or {}).get('widget_standard') or []) or '(none)'} / {', '.join((packaging.get('partner_rental') or {}).get('api_or_detail_pro') or []) or '(none)'}.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Program Improvement Loop",
        "",
        "## Summary",
        f"- immediate_blocker_count: {summary.get('immediate_blocker_count')}",
        f"- structural_improvement_count: {summary.get('structural_improvement_count')}",
        f"- patent_hardening_count: {summary.get('patent_hardening_count')}",
        f"- commercialization_gap_count: {summary.get('commercialization_gap_count')}",
        f"- wp_runtime_ready: {summary.get('wp_runtime_ready')}",
        f"- wp_page_verification_ok: {summary.get('wp_page_verification_ok')}",
        f"- staging_cutover_ready: {summary.get('staging_cutover_ready')}",
        "",
        "## Top Next Actions",
    ]
    for row in payload.get("top_next_actions") or []:
        if not isinstance(row, dict):
            continue
        lines.append(f"- [P{row.get('priority')}] {row.get('title')}: {row.get('action')}")
    for section_key, title in (
        ("immediate_blockers", "Immediate Blockers"),
        ("structural_improvements", "Structural Improvements"),
        ("commercialization_gaps", "Commercialization Gaps"),
        ("patent_hardening", "Patent Hardening"),
    ):
        lines.append("")
        lines.append(f"## {title}")
        rows = payload.get(section_key) or []
        for row in rows:
            if not isinstance(row, dict):
                continue
            lines.append(f"- {row.get('title')}: {row.get('why')} / {row.get('action')}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the autonomous improvement loop for the SeoulMNA platform program")
    parser.add_argument("--operations", type=Path, default=DEFAULT_OPERATIONS)
    parser.add_argument("--attorney", type=Path, default=DEFAULT_ATTORNEY)
    parser.add_argument("--wordpress-staging-apply-plan", type=Path, default=DEFAULT_STAGING_APPLY)
    parser.add_argument("--wp-surface-lab-apply", type=Path, default=DEFAULT_WP_APPLY)
    parser.add_argument("--wp-surface-lab-page-verify", type=Path, default=DEFAULT_WP_VERIFY)
    parser.add_argument("--widget-rental-catalog", type=Path, default=DEFAULT_WIDGET_CATALOG)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "program_improvement_loop_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "program_improvement_loop_latest.md")
    args = parser.parse_args()

    payload = _build_priorities(
        operations=_load_json(args.operations),
        attorney=_load_json(args.attorney),
        staging_apply=_load_json(args.wordpress_staging_apply_plan),
        wp_apply=_load_json(args.wp_surface_lab_apply),
        wp_verify=_load_json(args.wp_surface_lab_page_verify),
        widget_catalog=_load_json(args.widget_rental_catalog),
        operations_path=args.operations,
        attorney_path=args.attorney,
        staging_apply_path=args.wordpress_staging_apply_plan,
        wp_apply_path=args.wp_surface_lab_apply,
        wp_verify_path=args.wp_surface_lab_page_verify,
        widget_catalog_path=args.widget_rental_catalog,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
