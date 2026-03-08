#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPERATOR_DEMO = ROOT / "logs" / "permit_operator_demo_packet_latest.json"
DEFAULT_PUBLIC_CONTRACT = ROOT / "logs" / "permit_public_contract_audit_latest.json"
DEFAULT_WIDGET_CATALOG = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_JSON = ROOT / "logs" / "permit_partner_binding_parity_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "permit_partner_binding_parity_packet_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _clean_string_list(value: Any) -> List[str]:
    out: List[str] = []
    for item in _safe_list(value):
        text = _safe_str(item)
        if text and text not in out:
            out.append(text)
    return out


def _partner_case_priority(case: Dict[str, Any]) -> tuple[int, int, str]:
    manual_review_expected = bool(case.get("manual_review_expected"))
    review_reason = _safe_str(case.get("review_reason"))
    expected_status = _safe_str(case.get("expected_status"))
    case_kind = _safe_str(case.get("case_kind"))
    if not manual_review_expected:
        if review_reason == "capital_and_technician_shortfall" or case_kind == "shortfall_fail":
            return (0, 0, review_reason)
        if "capital" in review_reason or case_kind == "capital_only_fail":
            return (1, 0, review_reason)
        if "technician" in review_reason or case_kind == "technician_only_fail":
            return (2, 0, review_reason)
        if expected_status in {"detail_checklist", "shortfall"}:
            return (3, 0, review_reason)
        return (4, 0, review_reason)
    if review_reason:
        return (5, 0, review_reason)
    return (6, 0, case_kind)


def _derive_binding_focus(case: Dict[str, Any]) -> str:
    review_reason = _safe_str(case.get("review_reason"))
    if bool(case.get("manual_review_expected")):
        return "manual_review_gate"
    if review_reason == "capital_and_technician_shortfall":
        return "capital_and_technician_gap_first"
    if "capital" in review_reason:
        return "capital_gap_first"
    if "technician" in review_reason:
        return "technician_gap_first"
    if review_reason:
        return "review_reason_first"
    return "baseline_reference"


def _match_demo_case_by_preset_id(demo_cases: List[Dict[str, Any]], preset_id: str) -> Dict[str, Any]:
    target = _safe_str(preset_id)
    if not target:
        return {}
    for case in demo_cases:
        if _safe_str(case.get("preset_id")) == target:
            return dict(case)
    return {}


def _merge_prompt_case_binding(
    *,
    prompt_case_binding: Dict[str, Any],
    matched_demo_case: Dict[str, Any],
) -> Dict[str, Any]:
    merged = dict(matched_demo_case) if matched_demo_case else {}
    merged.update(prompt_case_binding)
    if matched_demo_case and not _safe_str(merged.get("case_kind")):
        merged["case_kind"] = _safe_str(matched_demo_case.get("case_kind"))
    return merged


def _select_partner_binding_case(family: Dict[str, Any]) -> Dict[str, Any]:
    demo_cases = [_safe_dict(row) for row in _safe_list(family.get("demo_cases")) if _safe_dict(row)]
    prompt_case_binding = _safe_dict(family.get("prompt_case_binding"))
    if prompt_case_binding:
        matched_demo_case = _match_demo_case_by_preset_id(demo_cases, _safe_str(prompt_case_binding.get("preset_id")))
        return _merge_prompt_case_binding(
            prompt_case_binding=prompt_case_binding,
            matched_demo_case=matched_demo_case,
        )
    if demo_cases:
        return dict(sorted(demo_cases, key=_partner_case_priority)[0])
    return {}


def build_packet(
    *,
    operator_demo_path: Path,
    public_contract_path: Path,
    widget_catalog_path: Path,
) -> Dict[str, Any]:
    operator_demo = _load_json(operator_demo_path)
    public_contract = _load_json(public_contract_path)
    widget_catalog = _load_json(widget_catalog_path)

    operator_summary = _safe_dict(operator_demo.get("summary"))
    public_summary = _safe_dict(public_contract.get("summary"))
    public_contracts = _safe_dict(public_contract.get("contracts"))
    widget_summary = _safe_dict(widget_catalog.get("summary"))

    detail_offerings = _clean_string_list(public_contracts.get("detail_allowed_offerings"))
    assist_offerings = _clean_string_list(public_contracts.get("assist_allowed_offerings"))

    partner_surface: List[Dict[str, Any]] = []
    for family in _safe_list(operator_demo.get("families")):
        row = _safe_dict(family)
        binding = _select_partner_binding_case(row)
        if not binding:
            continue
        manual_review_expected = bool(binding.get("manual_review_expected"))
        exposure_lane = "manual_review_assist" if manual_review_expected else "detail_checklist"
        exposure_offerings = assist_offerings if manual_review_expected else detail_offerings
        partner_surface.append(
            {
                "claim_id": _safe_str(row.get("claim_id")),
                "claim_title": _safe_str(row.get("claim_title")),
                "family_key": _safe_str(row.get("family_key")),
                "binding_preset_id": _safe_str(binding.get("preset_id")),
                "service_code": _safe_str(binding.get("service_code")),
                "service_name": _safe_str(binding.get("service_name")),
                "expected_status": _safe_str(binding.get("expected_status")),
                "review_reason": _safe_str(binding.get("review_reason")),
                "manual_review_expected": manual_review_expected,
                "binding_focus": _safe_str(binding.get("binding_focus")) or _derive_binding_focus(binding),
                "source_case_kind": _safe_str(binding.get("case_kind")) or "prompt_case_binding",
                "exposure_lane": exposure_lane,
                "public_summary_visible": False,
                "partner_widget_visible": True,
                "partner_api_visible": True,
                "allowed_offerings": exposure_offerings,
                "cta_label": "Request manual review" if manual_review_expected else "View detailed checklist",
                "cta_target": "/consult?intent=permit" if manual_review_expected else "/permit",
            }
        )

    family_total = len(partner_surface)
    manual_review_family_total = sum(1 for row in partner_surface if row.get("manual_review_expected"))
    detail_checklist_family_total = family_total - manual_review_family_total
    public_contract_ok = bool(public_summary.get("contract_ok"))
    offering_exposure_ok = bool(public_summary.get("offering_exposure_ok"))
    detail_contract_ok = bool(public_summary.get("detail_checklist_contract_ok"))
    assist_contract_ok = bool(public_summary.get("assist_contract_ok"))
    partner_surface_ready = family_total > 0 and detail_contract_ok and assist_contract_ok
    packet_ready = (
        bool(operator_summary.get("operator_demo_ready"))
        and public_contract_ok
        and offering_exposure_ok
        and partner_surface_ready
        and bool(detail_offerings)
        and bool(assist_offerings)
    )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "permit_partner_binding_parity_packet_latest",
        "summary": {
            "packet_ready": packet_ready,
            "family_total": family_total,
            "detail_checklist_family_total": detail_checklist_family_total,
            "manual_review_family_total": manual_review_family_total,
            "public_contract_ok": public_contract_ok,
            "offering_exposure_ok": offering_exposure_ok,
            "partner_surface_ready": partner_surface_ready,
            "detail_checklist_contract_ok": detail_contract_ok,
            "manual_review_assist_contract_ok": assist_contract_ok,
            "detail_allowed_offering_total": len(detail_offerings),
            "manual_review_assist_offering_total": len(assist_offerings),
        },
        "public_contract": {
            "detail_allowed_offerings": detail_offerings,
            "manual_review_assist_allowed_offerings": assist_offerings,
            "public_summary_visible_fields": _clean_string_list(public_contracts.get("public_fields")),
            "detail_visible_fields": _clean_string_list(public_contracts.get("detail_fields")),
            "assist_visible_fields": _clean_string_list(public_contracts.get("assist_fields")),
        },
        "partner_surface": partner_surface,
        "verification_targets": [
            "permit_public_contract_ok == true",
            "detail_checklist_contract_ok == true",
            "manual_review_assist_contract_ok == true",
            "one representative partner-safe case per permit family",
            "public summary still hides checklist/manual-review case detail",
        ],
        "next_actions": [
            "Expose exactly one partner-safe representative case per permit family on widget/API contracts.",
            "Keep public summary minimal; do not leak operator demo steps or raw case payloads.",
            "Route manual-review families to manual-review assist and all other families to detail checklist by default.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = _safe_dict(payload.get("summary"))
    lines = [
        "# Permit Partner Binding Parity Packet",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- family_total: {summary.get('family_total')}",
        f"- detail_checklist_family_total: {summary.get('detail_checklist_family_total')}",
        f"- manual_review_family_total: {summary.get('manual_review_family_total')}",
        f"- public_contract_ok: {summary.get('public_contract_ok')}",
        f"- offering_exposure_ok: {summary.get('offering_exposure_ok')}",
        f"- partner_surface_ready: {summary.get('partner_surface_ready')}",
        "",
        "## Partner Surface",
    ]
    for row in _safe_list(payload.get("partner_surface")):
        item = _safe_dict(row)
        lines.append(
            f"- {item.get('claim_id')}: {item.get('service_code')} / {item.get('expected_status')} / {item.get('review_reason')} -> {item.get('exposure_lane')}"
        )
    lines.extend(["", "## Verification Targets"])
    for item in _clean_string_list(payload.get("verification_targets")):
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the permit partner binding parity packet.")
    parser.add_argument("--operator-demo", type=Path, default=DEFAULT_OPERATOR_DEMO)
    parser.add_argument("--public-contract", type=Path, default=DEFAULT_PUBLIC_CONTRACT)
    parser.add_argument("--widget-catalog", type=Path, default=DEFAULT_WIDGET_CATALOG)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_packet(
        operator_demo_path=args.operator_demo,
        public_contract_path=args.public_contract,
        widget_catalog_path=args.widget_catalog,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if bool(_safe_dict(payload.get("summary")).get("packet_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
