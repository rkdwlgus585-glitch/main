#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPERATOR_DEMO_PACKET_INPUT = ROOT / "logs" / "permit_operator_demo_packet_latest.json"
DEFAULT_PARTNER_BINDING_PARITY_INPUT = ROOT / "logs" / "permit_partner_binding_parity_packet_latest.json"
DEFAULT_WIDGET_INPUT = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_API_CONTRACT_INPUT = ROOT / "logs" / "api_contract_spec_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_partner_binding_observability_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_partner_binding_observability_latest.md"


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


def _api_master_contract(api_contract_spec: Dict[str, Any]) -> Dict[str, Any]:
    services = api_contract_spec.get("services") if isinstance(api_contract_spec.get("services"), dict) else {}
    permit_service = services.get("permit") if isinstance(services.get("permit"), dict) else {}
    response_contract = (
        permit_service.get("response_contract") if isinstance(permit_service.get("response_contract"), dict) else {}
    )
    catalog_contracts = (
        response_contract.get("catalog_contracts")
        if isinstance(response_contract.get("catalog_contracts"), dict)
        else {}
    )
    return catalog_contracts.get("master_catalog") if isinstance(catalog_contracts.get("master_catalog"), dict) else {}


def _widget_feed(widget_rental_catalog: Dict[str, Any]) -> Dict[str, Any]:
    packaging = widget_rental_catalog.get("packaging") if isinstance(widget_rental_catalog.get("packaging"), dict) else {}
    partner_rental = packaging.get("partner_rental") if isinstance(packaging.get("partner_rental"), dict) else {}
    return (
        partner_rental.get("permit_widget_feeds")
        if isinstance(partner_rental.get("permit_widget_feeds"), dict)
        else {}
    )


def _expected_families(
    partner_binding_parity_packet: Dict[str, Any],
    operator_demo_packet: Dict[str, Any],
) -> List[Dict[str, Any]]:
    parity_rows = [_safe_dict(row) for row in _safe_list(partner_binding_parity_packet.get("partner_surface")) if _safe_dict(row)]
    if parity_rows:
        return [
            {
                "claim_id": _safe_str(row.get("claim_id")),
                "family_key": _safe_str(row.get("family_key")),
                "binding_preset_id": _safe_str(row.get("binding_preset_id")),
                "service_code": _safe_str(row.get("service_code")),
                "expected_status": _safe_str(row.get("expected_status")),
                "review_reason": _safe_str(row.get("review_reason")),
                "manual_review_expected": bool(row.get("manual_review_expected")),
            }
            for row in parity_rows
            if _safe_str(row.get("claim_id"))
        ]
    out: List[Dict[str, Any]] = []
    for family in _safe_list(operator_demo_packet.get("families")):
        row = _safe_dict(family)
        binding = _safe_dict(row.get("prompt_case_binding"))
        claim_id = _safe_str(row.get("claim_id"))
        if not claim_id:
            continue
        out.append(
            {
                "claim_id": claim_id,
                "family_key": _safe_str(row.get("family_key")),
                "binding_preset_id": _safe_str(binding.get("preset_id")),
                "service_code": _safe_str(binding.get("service_code")),
                "expected_status": _safe_str(binding.get("expected_status")),
                "review_reason": _safe_str(binding.get("review_reason")),
                "manual_review_expected": bool(binding.get("manual_review_expected")),
            }
        )
    return out


def _sample_map(rows: List[Any]) -> Dict[str, Dict[str, Any]]:
    mapped: Dict[str, Dict[str, Any]] = {}
    for raw in rows:
        row = _safe_dict(raw)
        claim_id = _safe_str(row.get("claim_id"))
        if claim_id and claim_id not in mapped:
            mapped[claim_id] = row
    return mapped


def _missing_preview(
    expected_map: Dict[str, Dict[str, Any]],
    visible_map: Dict[str, Dict[str, Any]],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    preview: List[Dict[str, Any]] = []
    for claim_id, row in expected_map.items():
        if claim_id in visible_map:
            continue
        preview.append(
            {
                "claim_id": claim_id,
                "family_key": _safe_str(row.get("family_key")),
                "binding_preset_id": _safe_str(row.get("binding_preset_id")),
                "service_code": _safe_str(row.get("service_code")),
            }
        )
        if len(preview) >= limit:
            break
    return preview


def build_observability_report(
    *,
    operator_demo_packet: Dict[str, Any],
    permit_partner_binding_parity_packet: Dict[str, Any],
    widget_rental_catalog: Dict[str, Any],
    api_contract_spec: Dict[str, Any],
) -> Dict[str, Any]:
    operator_summary = (
        operator_demo_packet.get("summary") if isinstance(operator_demo_packet.get("summary"), dict) else {}
    )
    parity_summary = (
        permit_partner_binding_parity_packet.get("summary")
        if isinstance(permit_partner_binding_parity_packet.get("summary"), dict)
        else {}
    )
    widget_summary = (
        widget_rental_catalog.get("summary") if isinstance(widget_rental_catalog.get("summary"), dict) else {}
    )
    widget_feed = _widget_feed(widget_rental_catalog)
    api_master_contract = _api_master_contract(api_contract_spec)
    api_master_summary = (
        api_master_contract.get("current_summary")
        if isinstance(api_master_contract.get("current_summary"), dict)
        else {}
    )
    api_proof_surface = (
        api_master_contract.get("proof_surface_examples")
        if isinstance(api_master_contract.get("proof_surface_examples"), dict)
        else {}
    )

    expected_rows = _expected_families(permit_partner_binding_parity_packet, operator_demo_packet)
    expected_map = _sample_map(expected_rows)
    widget_map = _sample_map(_safe_list(widget_feed.get("partner_demo_samples")))
    api_map = _sample_map(_safe_list(api_proof_surface.get("partner_demo_samples")))

    widget_missing_preview = _missing_preview(expected_map, widget_map)
    api_missing_preview = _missing_preview(expected_map, api_map)
    widget_extra_claim_ids = sorted([claim_id for claim_id in widget_map if claim_id not in expected_map])
    api_extra_claim_ids = sorted([claim_id for claim_id in api_map if claim_id not in expected_map])

    rows: List[Dict[str, Any]] = []
    for claim_id, expected in expected_map.items():
        widget_row = widget_map.get(claim_id, {})
        api_row = api_map.get(claim_id, {})
        rows.append(
            {
                "claim_id": claim_id,
                "family_key": _safe_str(expected.get("family_key")),
                "binding_preset_id": _safe_str(expected.get("binding_preset_id")),
                "service_code": _safe_str(expected.get("service_code")),
                "expected_status": _safe_str(expected.get("expected_status")),
                "review_reason": _safe_str(expected.get("review_reason")),
                "manual_review_expected": bool(expected.get("manual_review_expected")),
                "widget_visible": bool(widget_row),
                "api_visible": bool(api_row),
                "widget_binding_preset_id": _safe_str(widget_row.get("binding_preset_id")),
                "api_binding_preset_id": _safe_str(api_row.get("binding_preset_id")),
            }
        )

    expected_family_total = len(expected_map)
    widget_binding_family_total = len(widget_map)
    api_binding_family_total = len(api_map)
    operator_binding_family_total = int(operator_summary.get("prompt_case_binding_total", 0) or 0)
    widget_binding_surface_ready = bool(widget_summary.get("permit_partner_binding_surface_ready", False))
    api_binding_surface_ready = bool(api_master_summary.get("partner_binding_surface_ready", False))
    parity_packet_ready = bool(parity_summary.get("packet_ready", False))
    observability_ready = all(
        [
            parity_packet_ready,
            widget_binding_surface_ready,
            api_binding_surface_ready,
            expected_family_total > 0,
            operator_binding_family_total == expected_family_total,
            widget_binding_family_total == expected_family_total,
            api_binding_family_total == expected_family_total,
            not widget_missing_preview,
            not api_missing_preview,
            not widget_extra_claim_ids,
            not api_extra_claim_ids,
        ]
    )

    summary = {
        "parity_packet_ready": parity_packet_ready,
        "expected_family_total": expected_family_total,
        "operator_binding_family_total": operator_binding_family_total,
        "widget_binding_family_total": widget_binding_family_total,
        "api_binding_family_total": api_binding_family_total,
        "widget_binding_surface_ready": widget_binding_surface_ready,
        "api_binding_surface_ready": api_binding_surface_ready,
        "partner_binding_surface_ready": widget_binding_surface_ready and api_binding_surface_ready,
        "widget_missing_family_total": len(widget_missing_preview),
        "api_missing_family_total": len(api_missing_preview),
        "widget_extra_family_total": len(widget_extra_claim_ids),
        "api_extra_family_total": len(api_extra_claim_ids),
        "observability_ready": observability_ready,
    }

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "families": rows,
        "widget_missing_preview": widget_missing_preview,
        "api_missing_preview": api_missing_preview,
        "widget_extra_claim_ids": widget_extra_claim_ids,
        "api_extra_claim_ids": api_extra_claim_ids,
        "source_paths": {
            "operator_demo_packet": str(DEFAULT_OPERATOR_DEMO_PACKET_INPUT.resolve()),
            "partner_binding_parity_packet": str(DEFAULT_PARTNER_BINDING_PARITY_INPUT.resolve()),
            "widget_rental_catalog": str(DEFAULT_WIDGET_INPUT.resolve()),
            "api_contract_spec": str(DEFAULT_API_CONTRACT_INPUT.resolve()),
        },
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    lines = [
        "# Permit Partner Binding Observability",
        "",
        "## Summary",
        f"- parity_packet_ready: `{summary.get('parity_packet_ready', False)}`",
        f"- expected_family_total: `{summary.get('expected_family_total', 0)}`",
        f"- operator_binding_family_total: `{summary.get('operator_binding_family_total', 0)}`",
        f"- widget_binding_family_total: `{summary.get('widget_binding_family_total', 0)}`",
        f"- api_binding_family_total: `{summary.get('api_binding_family_total', 0)}`",
        f"- widget_binding_surface_ready: `{summary.get('widget_binding_surface_ready', False)}`",
        f"- api_binding_surface_ready: `{summary.get('api_binding_surface_ready', False)}`",
        f"- partner_binding_surface_ready: `{summary.get('partner_binding_surface_ready', False)}`",
        f"- widget_missing_family_total: `{summary.get('widget_missing_family_total', 0)}`",
        f"- api_missing_family_total: `{summary.get('api_missing_family_total', 0)}`",
        f"- widget_extra_family_total: `{summary.get('widget_extra_family_total', 0)}`",
        f"- api_extra_family_total: `{summary.get('api_extra_family_total', 0)}`",
        f"- observability_ready: `{summary.get('observability_ready', False)}`",
        "",
        "## Family Matrix",
    ]
    for row in [item for item in list(report.get("families") or []) if isinstance(item, dict)]:
        lines.append(
            f"- `{row.get('claim_id', '')}` widget={row.get('widget_visible', False)} api={row.get('api_visible', False)} "
            f"/ preset={row.get('binding_preset_id', '')} / service={row.get('service_code', '')} / reason={row.get('review_reason', '')}"
        )
    widget_missing = [item for item in list(report.get("widget_missing_preview") or []) if isinstance(item, dict)]
    if widget_missing:
        lines.extend(["", "## Widget Missing Preview"])
        for row in widget_missing:
            lines.append(
                f"- `{row.get('claim_id', '')}` / {row.get('family_key', '')} / preset={row.get('binding_preset_id', '')}"
            )
    api_missing = [item for item in list(report.get("api_missing_preview") or []) if isinstance(item, dict)]
    if api_missing:
        lines.extend(["", "## API Missing Preview"])
        for row in api_missing:
            lines.append(
                f"- `{row.get('claim_id', '')}` / {row.get('family_key', '')} / preset={row.get('binding_preset_id', '')}"
            )
    if list(report.get("widget_extra_claim_ids") or []):
        lines.extend(["", "## Widget Extra Claim IDs"])
        for claim_id in list(report.get("widget_extra_claim_ids") or []):
            lines.append(f"- `{claim_id}`")
    if list(report.get("api_extra_claim_ids") or []):
        lines.extend(["", "## API Extra Claim IDs"])
        for claim_id in list(report.get("api_extra_claim_ids") or []):
            lines.append(f"- `{claim_id}`")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate partner binding observability for permit partner-safe samples.")
    parser.add_argument("--operator-demo-packet", type=Path, default=DEFAULT_OPERATOR_DEMO_PACKET_INPUT)
    parser.add_argument("--partner-binding-parity", type=Path, default=DEFAULT_PARTNER_BINDING_PARITY_INPUT)
    parser.add_argument("--widget-input", type=Path, default=DEFAULT_WIDGET_INPUT)
    parser.add_argument("--api-contract-input", type=Path, default=DEFAULT_API_CONTRACT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    report = build_observability_report(
        operator_demo_packet=_load_json(args.operator_demo_packet.resolve()),
        permit_partner_binding_parity_packet=_load_json(args.partner_binding_parity.resolve()),
        widget_rental_catalog=_load_json(args.widget_input.resolve()),
        api_contract_spec=_load_json(args.api_contract_input.resolve()),
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "json": str(args.json_output.resolve()), "md": str(args.md_output.resolve())},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if bool((report.get("summary") or {}).get("observability_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
