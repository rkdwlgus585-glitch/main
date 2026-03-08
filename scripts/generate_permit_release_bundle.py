from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_release_bundle_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_release_bundle_latest.md"
DEFAULT_PROMPT_DOC = ROOT / "docs" / "permit_critical_thinking_prompt.md"


def _load_json_if_exists(path: str) -> Dict[str, Any]:
    target = Path(path)
    if not target.exists():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _doc_excerpt(text: str, limit: int = 6) -> str:
    lines = [line.rstrip() for line in str(text or "").splitlines() if line.strip()]
    return "\n".join(lines[:limit])


def build_step_specs(python_executable: str) -> List[Dict[str, Any]]:
    return [
        {
            "name": "permit_focus_seed_catalog",
            "command": [python_executable, "scripts\\generate_permit_focus_seed_catalog.py"],
            "outputs": [
                str(ROOT / "config" / "permit_focus_seed_catalog.json"),
                str(ROOT / "logs" / "permit_focus_seed_catalog_latest.md"),
            ],
        },
        {
            "name": "permit_focus_source_upgrade_packet",
            "command": [python_executable, "scripts\\generate_permit_focus_source_upgrade_packet.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_focus_source_upgrade_packet_latest.json"),
                str(ROOT / "logs" / "permit_focus_source_upgrade_packet_latest.md"),
            ],
        },
        {
            "name": "permit_focus_family_registry",
            "command": [
                python_executable,
                "scripts\\generate_permit_focus_family_registry.py",
                "--materialize-all-pending",
            ],
            "outputs": [
                str(ROOT / "config" / "permit_focus_family_registry.json"),
                str(ROOT / "logs" / "permit_focus_family_registry_latest.json"),
                str(ROOT / "logs" / "permit_focus_family_registry_latest.md"),
            ],
        },
        {
            "name": "permit_precheck_html",
            "command": [
                python_executable,
                "permit_diagnosis_calculator.py",
                "--output",
                "output\\ai_permit_precheck.html",
            ],
            "outputs": [str(ROOT / "output" / "ai_permit_precheck.html")],
        },
        {
            "name": "permit_focus_report",
            "command": [python_executable, "scripts\\generate_permit_focus_priority_report.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_focus_priority_latest.json"),
                str(ROOT / "logs" / "permit_focus_priority_latest.md"),
            ],
        },
        {
            "name": "permit_selector_catalog",
            "command": [python_executable, "scripts\\generate_permit_selector_catalog.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_selector_catalog_latest.json"),
                str(ROOT / "logs" / "permit_selector_catalog_latest.md"),
            ],
        },
        {
            "name": "permit_platform_catalog",
            "command": [python_executable, "scripts\\generate_permit_platform_catalog.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_platform_catalog_latest.json"),
                str(ROOT / "logs" / "permit_platform_catalog_latest.md"),
            ],
        },
        {
            "name": "permit_master_catalog",
            "command": [python_executable, "scripts\\generate_permit_master_catalog.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_master_catalog_latest.json"),
                str(ROOT / "logs" / "permit_master_catalog_latest.md"),
            ],
        },
        {
            "name": "permit_capital_registration_logic_packet",
            "command": [python_executable, "scripts\\generate_permit_capital_registration_logic_packet.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_capital_registration_logic_packet_latest.json"),
                str(ROOT / "logs" / "permit_capital_registration_logic_packet_latest.md"),
            ],
        },
        {
            "name": "permit_provenance_audit",
            "command": [python_executable, "scripts\\generate_permit_provenance_audit.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_provenance_audit_latest.json"),
                str(ROOT / "logs" / "permit_provenance_audit_latest.md"),
            ],
        },
        {
            "name": "permit_source_upgrade_backlog",
            "command": [python_executable, "scripts\\generate_permit_source_upgrade_backlog.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_source_upgrade_backlog_latest.json"),
                str(ROOT / "logs" / "permit_source_upgrade_backlog_latest.md"),
            ],
        },
        {
            "name": "permit_patent_evidence_bundle",
            "command": [python_executable, "scripts\\generate_permit_patent_evidence_bundle.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_patent_evidence_bundle_latest.json"),
                str(ROOT / "logs" / "permit_patent_evidence_bundle_latest.md"),
            ],
        },
        {
            "name": "permit_family_case_goldset",
            "command": [python_executable, "scripts\\generate_permit_family_case_goldset.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_family_case_goldset_latest.json"),
                str(ROOT / "logs" / "permit_family_case_goldset_latest.md"),
            ],
        },
        {
            "name": "permit_runtime_case_assertions",
            "command": [python_executable, "scripts\\generate_permit_runtime_case_assertions.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_runtime_case_assertions_latest.json"),
                str(ROOT / "logs" / "permit_runtime_case_assertions_latest.md"),
            ],
        },
        {
            "name": "permit_capital_registration_logic_packet_refresh",
            "command": [python_executable, "scripts\\generate_permit_capital_registration_logic_packet.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_capital_registration_logic_packet_latest.json"),
                str(ROOT / "logs" / "permit_capital_registration_logic_packet_latest.md"),
            ],
        },
        {
            "name": "permit_review_case_presets",
            "command": [python_executable, "scripts\\generate_permit_review_case_presets.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_review_case_presets_latest.json"),
                str(ROOT / "logs" / "permit_review_case_presets_latest.md"),
            ],
        },
        {
            "name": "permit_case_story_surface",
            "command": [python_executable, "scripts\\generate_permit_case_story_surface.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_case_story_surface_latest.json"),
                str(ROOT / "logs" / "permit_case_story_surface_latest.md"),
            ],
        },
        {
            "name": "permit_operator_demo_packet",
            "command": [python_executable, "scripts\\generate_permit_operator_demo_packet.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_operator_demo_packet_latest.json"),
                str(ROOT / "logs" / "permit_operator_demo_packet_latest.md"),
            ],
        },
        {
            "name": "permit_review_reason_decision_ladder",
            "command": [python_executable, "scripts\\generate_permit_review_reason_decision_ladder.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_review_reason_decision_ladder_latest.json"),
                str(ROOT / "logs" / "permit_review_reason_decision_ladder_latest.md"),
            ],
        },
        {
            "name": "permit_prompt_case_binding_packet",
            "command": [python_executable, "scripts\\generate_permit_prompt_case_binding_packet.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_prompt_case_binding_packet_latest.json"),
                str(ROOT / "logs" / "permit_prompt_case_binding_packet_latest.md"),
            ],
        },
        {
            "name": "permit_critical_prompt_surface_packet",
            "command": [python_executable, "scripts\\generate_permit_critical_prompt_surface_packet.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_critical_prompt_surface_packet_latest.json"),
                str(ROOT / "logs" / "permit_critical_prompt_surface_packet_latest.md"),
            ],
        },
        {
            "name": "widget_rental_catalog",
            "command": [python_executable, "scripts\\generate_widget_rental_catalog.py"],
            "outputs": [
                str(ROOT / "logs" / "widget_rental_catalog_latest.json"),
                str(ROOT / "logs" / "widget_rental_catalog_latest.md"),
            ],
        },
        {
            "name": "api_contract_spec",
            "command": [python_executable, "scripts\\generate_api_contract_spec.py"],
            "outputs": [str(ROOT / "logs" / "api_contract_spec_latest.json")],
        },
        {
            "name": "permit_partner_binding_parity_packet",
            "command": [python_executable, "scripts\\generate_permit_partner_binding_parity_packet.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_partner_binding_parity_packet_latest.json"),
                str(ROOT / "logs" / "permit_partner_binding_parity_packet_latest.md"),
            ],
        },
        {
            "name": "permit_thinking_prompt_bundle_packet",
            "command": [python_executable, "scripts\\generate_permit_thinking_prompt_bundle_packet.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_thinking_prompt_bundle_packet_latest.json"),
                str(ROOT / "logs" / "permit_thinking_prompt_bundle_packet_latest.md"),
            ],
        },
        {
            "name": "permit_partner_binding_observability",
            "command": [python_executable, "scripts\\generate_permit_partner_binding_observability.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_partner_binding_observability_latest.json"),
                str(ROOT / "logs" / "permit_partner_binding_observability_latest.md"),
            ],
        },
        {
            "name": "permit_partner_gap_preview_digest",
            "command": [python_executable, "scripts\\generate_permit_partner_gap_preview_digest.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_partner_gap_preview_digest_latest.json"),
                str(ROOT / "logs" / "permit_partner_gap_preview_digest_latest.md"),
            ],
        },
        {
            "name": "permit_case_release_guard",
            "command": [python_executable, "scripts\\generate_permit_case_release_guard.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_case_release_guard_latest.json"),
                str(ROOT / "logs" / "permit_case_release_guard_latest.md"),
            ],
        },
        {
            "name": "permit_preset_story_release_guard",
            "command": [python_executable, "scripts\\generate_permit_preset_story_release_guard.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_preset_story_release_guard_latest.json"),
                str(ROOT / "logs" / "permit_preset_story_release_guard_latest.md"),
            ],
        },
        {
            "name": "permit_demo_surface_observability",
            "command": [python_executable, "scripts\\generate_permit_demo_surface_observability.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_demo_surface_observability_latest.json"),
                str(ROOT / "logs" / "permit_demo_surface_observability_latest.md"),
            ],
        },
        {
            "name": "permit_surface_drift_digest",
            "command": [python_executable, "scripts\\generate_permit_surface_drift_digest.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_surface_drift_digest_latest.json"),
                str(ROOT / "logs" / "permit_surface_drift_digest_latest.md"),
            ],
        },
        {
            "name": "permit_runtime_reasoning_guard",
            "command": [python_executable, "scripts\\generate_permit_runtime_reasoning_guard.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_runtime_reasoning_guard_latest.json"),
                str(ROOT / "logs" / "permit_runtime_reasoning_guard_latest.md"),
            ],
        },
        {
            "name": "permit_next_action_brainstorm",
            "command": [python_executable, "scripts\\generate_permit_next_action_brainstorm.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_next_action_brainstorm_latest.json"),
                str(ROOT / "logs" / "permit_next_action_brainstorm_latest.md"),
            ],
        },
        {
            "name": "founder_mode_prompt_bundle_refresh",
            "command": [python_executable, "scripts\\generate_founder_mode_prompt_bundle.py"],
            "outputs": [
                str(ROOT / "logs" / "founder_mode_prompt_bundle_latest.json"),
                str(ROOT / "logs" / "founder_mode_prompt_bundle_latest.md"),
            ],
        },
        {
            "name": "system_split_first_principles_packet_refresh",
            "command": [python_executable, "scripts\\generate_system_split_first_principles_packet.py"],
            "outputs": [
                str(ROOT / "logs" / "system_split_first_principles_packet_latest.json"),
                str(ROOT / "logs" / "system_split_first_principles_packet_latest.md"),
            ],
        },
        {
            "name": "permit_thinking_prompt_bundle_packet_refresh",
            "command": [python_executable, "scripts\\generate_permit_thinking_prompt_bundle_packet.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_thinking_prompt_bundle_packet_latest.json"),
                str(ROOT / "logs" / "permit_thinking_prompt_bundle_packet_latest.md"),
            ],
        },
        {
            "name": "permit_closed_lane_stale_audit",
            "command": [python_executable, "scripts\\generate_permit_closed_lane_stale_audit.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_closed_lane_stale_audit_latest.json"),
                str(ROOT / "logs" / "permit_closed_lane_stale_audit_latest.md"),
            ],
        },
        {
            "name": "permit_next_action_brainstorm_refresh",
            "command": [python_executable, "scripts\\generate_permit_next_action_brainstorm.py"],
            "outputs": [
                str(ROOT / "logs" / "permit_next_action_brainstorm_latest.json"),
                str(ROOT / "logs" / "permit_next_action_brainstorm_latest.md"),
            ],
        },
    ]


def _truncate_output(text: str, limit: int = 4000) -> str:
    clean = str(text or "").strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3] + "..."


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _find_step_output_path(step_results: List[Dict[str, Any]], step_name: str, suffix: str) -> str:
    for row in step_results:
        if str(row.get("name") or "") != step_name:
            continue
        for output in list(row.get("outputs") or []):
            text = str(output or "").strip()
            if text.endswith(suffix):
                return text
    return ""


def run_bundle(*, python_executable: str) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = []
    for spec in build_step_specs(python_executable):
        started = time.perf_counter()
        completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        process = subprocess.run(
            spec["command"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        duration_sec = round(time.perf_counter() - started, 3)
        ok = process.returncode == 0
        results.append(
            {
                "name": spec["name"],
                "command": spec["command"],
                "outputs": list(spec.get("outputs") or []),
                "ok": ok,
                "returncode": int(process.returncode),
                "completed_at": completed_at,
                "duration_sec": duration_sec,
                "stdout": _truncate_output(process.stdout),
                "stderr": _truncate_output(process.stderr),
            }
        )
        if not ok:
            break
    case_release_guard_report = {}
    review_case_presets_report = {}
    case_story_surface_report = {}
    preset_story_release_guard_report = {}
    operator_demo_packet_report = {}
    review_reason_decision_ladder_report = {}
    prompt_case_binding_packet_report = {}
    critical_prompt_surface_packet_report = {}
    partner_binding_parity_packet_report = {}
    thinking_prompt_bundle_packet_report = {}
    partner_binding_observability_report = {}
    partner_gap_preview_digest_report = {}
    demo_surface_observability_report = {}
    surface_drift_digest_report = {}
    runtime_reasoning_guard_report = {}
    closed_lane_stale_audit_report = {}
    capital_registration_logic_packet_report = {}
    widget_rental_catalog_report = {}
    api_contract_spec_report = {}
    for row in results:
        outputs = [str(item or "").strip() for item in list(row.get("outputs") or []) if str(item or "").strip()]
        json_output = next((item for item in outputs if item.endswith(".json")), "")
        if not json_output:
            continue
        name = str(row.get("name") or "")
        if name == "permit_case_release_guard":
            case_release_guard_report = _load_json_if_exists(json_output)
        elif name == "permit_review_case_presets":
            review_case_presets_report = _load_json_if_exists(json_output)
        elif name == "permit_case_story_surface":
            case_story_surface_report = _load_json_if_exists(json_output)
        elif name == "permit_preset_story_release_guard":
            preset_story_release_guard_report = _load_json_if_exists(json_output)
        elif name == "permit_operator_demo_packet":
            operator_demo_packet_report = _load_json_if_exists(json_output)
        elif name == "permit_review_reason_decision_ladder":
            review_reason_decision_ladder_report = _load_json_if_exists(json_output)
        elif name == "permit_prompt_case_binding_packet":
            prompt_case_binding_packet_report = _load_json_if_exists(json_output)
        elif name == "permit_critical_prompt_surface_packet":
            critical_prompt_surface_packet_report = _load_json_if_exists(json_output)
        elif name == "permit_partner_binding_parity_packet":
            partner_binding_parity_packet_report = _load_json_if_exists(json_output)
        elif name == "permit_thinking_prompt_bundle_packet":
            thinking_prompt_bundle_packet_report = _load_json_if_exists(json_output)
        elif name == "permit_partner_binding_observability":
            partner_binding_observability_report = _load_json_if_exists(json_output)
        elif name == "permit_partner_gap_preview_digest":
            partner_gap_preview_digest_report = _load_json_if_exists(json_output)
        elif name == "permit_demo_surface_observability":
            demo_surface_observability_report = _load_json_if_exists(json_output)
        elif name == "permit_surface_drift_digest":
            surface_drift_digest_report = _load_json_if_exists(json_output)
        elif name == "permit_runtime_reasoning_guard":
            runtime_reasoning_guard_report = _load_json_if_exists(json_output)
        elif name == "permit_closed_lane_stale_audit":
            closed_lane_stale_audit_report = _load_json_if_exists(json_output)
        elif name in {"permit_capital_registration_logic_packet", "permit_capital_registration_logic_packet_refresh"}:
            capital_registration_logic_packet_report = _load_json_if_exists(json_output)
        elif name == "widget_rental_catalog":
            widget_rental_catalog_report = _load_json_if_exists(json_output)
        elif name == "api_contract_spec":
            api_contract_spec_report = _load_json_if_exists(json_output)
    return build_manifest(
        python_executable=python_executable,
        step_results=results,
        case_release_guard_report=case_release_guard_report,
        review_case_presets_report=review_case_presets_report,
        case_story_surface_report=case_story_surface_report,
        preset_story_release_guard_report=preset_story_release_guard_report,
        operator_demo_packet_report=operator_demo_packet_report,
        review_reason_decision_ladder_report=review_reason_decision_ladder_report,
        prompt_case_binding_packet_report=prompt_case_binding_packet_report,
        critical_prompt_surface_packet_report=critical_prompt_surface_packet_report,
        partner_binding_parity_packet_report=partner_binding_parity_packet_report,
        thinking_prompt_bundle_packet_report=thinking_prompt_bundle_packet_report,
        partner_binding_observability_report=partner_binding_observability_report,
        partner_gap_preview_digest_report=partner_gap_preview_digest_report,
        demo_surface_observability_report=demo_surface_observability_report,
        surface_drift_digest_report=surface_drift_digest_report,
        runtime_reasoning_guard_report=runtime_reasoning_guard_report,
        closed_lane_stale_audit_report=closed_lane_stale_audit_report,
        capital_registration_logic_packet_report=capital_registration_logic_packet_report,
        widget_rental_catalog_report=widget_rental_catalog_report,
        api_contract_spec_report=api_contract_spec_report,
    )


def build_manifest(
    *,
    python_executable: str,
    step_results: List[Dict[str, Any]],
    case_release_guard_report: Dict[str, Any] | None = None,
    review_case_presets_report: Dict[str, Any] | None = None,
    case_story_surface_report: Dict[str, Any] | None = None,
    preset_story_release_guard_report: Dict[str, Any] | None = None,
    operator_demo_packet_report: Dict[str, Any] | None = None,
    review_reason_decision_ladder_report: Dict[str, Any] | None = None,
    prompt_case_binding_packet_report: Dict[str, Any] | None = None,
    critical_prompt_surface_packet_report: Dict[str, Any] | None = None,
    partner_binding_parity_packet_report: Dict[str, Any] | None = None,
    thinking_prompt_bundle_packet_report: Dict[str, Any] | None = None,
    partner_binding_observability_report: Dict[str, Any] | None = None,
    partner_gap_preview_digest_report: Dict[str, Any] | None = None,
    demo_surface_observability_report: Dict[str, Any] | None = None,
    surface_drift_digest_report: Dict[str, Any] | None = None,
    runtime_reasoning_guard_report: Dict[str, Any] | None = None,
    closed_lane_stale_audit_report: Dict[str, Any] | None = None,
    capital_registration_logic_packet_report: Dict[str, Any] | None = None,
    widget_rental_catalog_report: Dict[str, Any] | None = None,
    api_contract_spec_report: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    failed = [row for row in step_results if not bool(row.get("ok"))]
    case_guard_summary = (
        dict((case_release_guard_report or {}).get("summary") or {})
        if isinstance(case_release_guard_report, dict)
        else {}
    )
    case_guard_missing = (
        dict((case_release_guard_report or {}).get("missing") or {})
        if isinstance(case_release_guard_report, dict)
        else {}
    )
    case_guard_failed_total = (
        int(case_guard_summary.get("runtime_failed_case_total", 0) or 0)
        + int(case_guard_summary.get("runtime_missing_case_total", 0) or 0)
        + int(case_guard_summary.get("widget_missing_case_total", 0) or 0)
        + int(case_guard_summary.get("api_missing_case_total", 0) or 0)
        + int(case_guard_summary.get("runtime_extra_case_total", 0) or 0)
        + int(case_guard_summary.get("widget_extra_case_total", 0) or 0)
        + int(case_guard_summary.get("api_extra_case_total", 0) or 0)
    )
    review_case_presets_summary = (
        dict((review_case_presets_report or {}).get("summary") or {})
        if isinstance(review_case_presets_report, dict)
        else {}
    )
    case_story_surface_summary = (
        dict((case_story_surface_report or {}).get("summary") or {})
        if isinstance(case_story_surface_report, dict)
        else {}
    )
    preset_story_guard_summary = (
        dict((preset_story_release_guard_report or {}).get("summary") or {})
        if isinstance(preset_story_release_guard_report, dict)
        else {}
    )
    operator_demo_summary = (
        dict((operator_demo_packet_report or {}).get("summary") or {})
        if isinstance(operator_demo_packet_report, dict)
        else {}
    )
    review_reason_decision_ladder_summary = (
        dict((review_reason_decision_ladder_report or {}).get("summary") or {})
        if isinstance(review_reason_decision_ladder_report, dict)
        else {}
    )
    prompt_case_binding_packet_summary = (
        dict((prompt_case_binding_packet_report or {}).get("summary") or {})
        if isinstance(prompt_case_binding_packet_report, dict)
        else {}
    )
    critical_prompt_surface_packet_summary = (
        dict((critical_prompt_surface_packet_report or {}).get("summary") or {})
        if isinstance(critical_prompt_surface_packet_report, dict)
        else {}
    )
    partner_binding_parity_packet_summary = (
        dict((partner_binding_parity_packet_report or {}).get("summary") or {})
        if isinstance(partner_binding_parity_packet_report, dict)
        else {}
    )
    thinking_prompt_bundle_packet_summary = (
        dict((thinking_prompt_bundle_packet_report or {}).get("summary") or {})
        if isinstance(thinking_prompt_bundle_packet_report, dict)
        else {}
    )
    partner_binding_observability_summary = (
        dict((partner_binding_observability_report or {}).get("summary") or {})
        if isinstance(partner_binding_observability_report, dict)
        else {}
    )
    partner_gap_preview_digest_summary = (
        dict((partner_gap_preview_digest_report or {}).get("summary") or {})
        if isinstance(partner_gap_preview_digest_report, dict)
        else {}
    )
    demo_surface_observability_summary = (
        dict((demo_surface_observability_report or {}).get("summary") or {})
        if isinstance(demo_surface_observability_report, dict)
        else {}
    )
    surface_drift_digest_summary = (
        dict((surface_drift_digest_report or {}).get("summary") or {})
        if isinstance(surface_drift_digest_report, dict)
        else {}
    )
    runtime_reasoning_guard_summary = (
        dict((runtime_reasoning_guard_report or {}).get("summary") or {})
        if isinstance(runtime_reasoning_guard_report, dict)
        else {}
    )
    closed_lane_stale_audit_summary = (
        dict((closed_lane_stale_audit_report or {}).get("summary") or {})
        if isinstance(closed_lane_stale_audit_report, dict)
        else {}
    )
    capital_registration_logic_packet_summary = (
        dict((capital_registration_logic_packet_report or {}).get("summary") or {})
        if isinstance(capital_registration_logic_packet_report, dict)
        else {}
    )
    widget_summary = (
        dict((widget_rental_catalog_report or {}).get("summary") or {})
        if isinstance(widget_rental_catalog_report, dict)
        else {}
    )
    api_contract_master_summary = {}
    if isinstance(api_contract_spec_report, dict):
        services = api_contract_spec_report.get("services") if isinstance(api_contract_spec_report.get("services"), dict) else {}
        permit_service = services.get("permit") if isinstance(services.get("permit"), dict) else {}
        response_contract = (
            permit_service.get("response_contract") if isinstance(permit_service.get("response_contract"), dict) else {}
        )
        catalog_contracts = (
            response_contract.get("catalog_contracts")
            if isinstance(response_contract.get("catalog_contracts"), dict)
            else {}
        )
        master_contract = (
            catalog_contracts.get("master_catalog") if isinstance(catalog_contracts.get("master_catalog"), dict) else {}
        )
        api_contract_master_summary = (
            master_contract.get("current_summary") if isinstance(master_contract.get("current_summary"), dict) else {}
        )
    operator_demo_packet_json_path = _find_step_output_path(
        step_results,
        "permit_operator_demo_packet",
        "permit_operator_demo_packet_latest.json",
    )
    operator_demo_packet_md_path = _find_step_output_path(
        step_results,
        "permit_operator_demo_packet",
        "permit_operator_demo_packet_latest.md",
    )
    thinking_prompt_bundle_json_path = _find_step_output_path(
        step_results,
        "permit_thinking_prompt_bundle_packet",
        "permit_thinking_prompt_bundle_packet_latest.json",
    )
    thinking_prompt_bundle_md_path = _find_step_output_path(
        step_results,
        "permit_thinking_prompt_bundle_packet",
        "permit_thinking_prompt_bundle_packet_latest.md",
    )
    partner_binding_observability_json_path = _find_step_output_path(
        step_results,
        "permit_partner_binding_observability",
        "permit_partner_binding_observability_latest.json",
    )
    partner_binding_observability_md_path = _find_step_output_path(
        step_results,
        "permit_partner_binding_observability",
        "permit_partner_binding_observability_latest.md",
    )
    partner_gap_preview_digest_json_path = _find_step_output_path(
        step_results,
        "permit_partner_gap_preview_digest",
        "permit_partner_gap_preview_digest_latest.json",
    )
    partner_gap_preview_digest_md_path = _find_step_output_path(
        step_results,
        "permit_partner_gap_preview_digest",
        "permit_partner_gap_preview_digest_latest.md",
    )
    demo_surface_observability_json_path = _find_step_output_path(
        step_results,
        "permit_demo_surface_observability",
        "permit_demo_surface_observability_latest.json",
    )
    demo_surface_observability_md_path = _find_step_output_path(
        step_results,
        "permit_demo_surface_observability",
        "permit_demo_surface_observability_latest.md",
    )
    surface_drift_digest_json_path = _find_step_output_path(
        step_results,
        "permit_surface_drift_digest",
        "permit_surface_drift_digest_latest.json",
    )
    surface_drift_digest_md_path = _find_step_output_path(
        step_results,
        "permit_surface_drift_digest",
        "permit_surface_drift_digest_latest.md",
    )
    runtime_reasoning_guard_json_path = _find_step_output_path(
        step_results,
        "permit_runtime_reasoning_guard",
        "permit_runtime_reasoning_guard_latest.json",
    )
    runtime_reasoning_guard_md_path = _find_step_output_path(
        step_results,
        "permit_runtime_reasoning_guard",
        "permit_runtime_reasoning_guard_latest.md",
    )
    closed_lane_stale_audit_json_path = _find_step_output_path(
        step_results,
        "permit_closed_lane_stale_audit",
        "permit_closed_lane_stale_audit_latest.json",
    )
    closed_lane_stale_audit_md_path = _find_step_output_path(
        step_results,
        "permit_closed_lane_stale_audit",
        "permit_closed_lane_stale_audit_latest.md",
    )
    operator_demo_release_surface_ready = bool(
        operator_demo_summary.get("operator_demo_ready", False) and operator_demo_packet_md_path
    )
    widget_partner_demo_surface_ready = bool(widget_summary.get("permit_partner_demo_surface_ready", False))
    widget_partner_binding_surface_ready = bool(widget_summary.get("permit_partner_binding_surface_ready", False))
    api_partner_demo_surface_ready = bool(api_contract_master_summary.get("partner_demo_surface_ready", False))
    api_partner_binding_surface_ready = bool(api_contract_master_summary.get("partner_binding_surface_ready", False))
    partner_demo_surface_ready = widget_partner_demo_surface_ready and api_partner_demo_surface_ready
    thinking_prompt_bundle_ready = bool(thinking_prompt_bundle_packet_summary.get("packet_ready", False))
    partner_binding_observability_ready = bool(partner_binding_observability_summary.get("observability_ready", False))
    demo_surface_observability_ready = bool(
        demo_surface_observability_summary.get("observability_ready", False)
    )
    surface_drift_digest_ready = bool(surface_drift_digest_summary.get("digest_ready", False))
    critical_prompt_doc = _load_text_if_exists(DEFAULT_PROMPT_DOC)
    critical_prompt_doc_ready = bool(critical_prompt_doc.strip())
    critical_prompt_doc_excerpt = _doc_excerpt(critical_prompt_doc)
    partner_qa_snapshot = {
        "release_guard_ready": bool(case_guard_summary.get("release_guard_ready", False)),
        "family_total": int(case_guard_summary.get("family_total", 0) or 0),
        "case_total": int(case_guard_summary.get("case_total", 0) or 0),
        "failed_total": case_guard_failed_total,
        "review_case_preset_total": int(review_case_presets_summary.get("preset_total", 0) or 0),
        "case_story_family_total": int(case_story_surface_summary.get("story_family_total", 0) or 0),
        "case_story_review_reason_total": int(case_story_surface_summary.get("review_reason_total", 0) or 0),
        "case_story_manual_review_family_total": int(
            case_story_surface_summary.get("manual_review_family_total", 0) or 0
        ),
        "preset_story_release_guard_ready": bool(
            preset_story_guard_summary.get("preset_story_guard_ready", False)
        ),
        "runtime_review_preset_surface_ready": bool(
            preset_story_guard_summary.get("runtime_review_preset_surface_ready", False)
        ),
        "runtime_case_story_surface_ready": bool(
            preset_story_guard_summary.get("runtime_case_story_surface_ready", False)
        ),
        "story_contract_parity_ready": bool(
            preset_story_guard_summary.get("story_contract_parity_ready", False)
        ),
        "operator_demo_ready": bool(operator_demo_summary.get("operator_demo_ready", False)),
        "operator_demo_release_surface_ready": operator_demo_release_surface_ready,
        "operator_demo_family_total": int(operator_demo_summary.get("family_total", 0) or 0),
        "operator_demo_case_total": int(operator_demo_summary.get("demo_case_total", 0) or 0),
        "operator_demo_packet_json_path": operator_demo_packet_json_path,
        "operator_demo_packet_md_path": operator_demo_packet_md_path,
        "widget_partner_demo_surface_ready": widget_partner_demo_surface_ready,
        "api_partner_demo_surface_ready": api_partner_demo_surface_ready,
        "partner_demo_surface_ready": partner_demo_surface_ready,
        "widget_partner_binding_surface_ready": widget_partner_binding_surface_ready,
        "api_partner_binding_surface_ready": api_partner_binding_surface_ready,
        "partner_binding_surface_ready": widget_partner_binding_surface_ready and api_partner_binding_surface_ready,
        "prompt_case_binding_packet_ready": bool(prompt_case_binding_packet_summary.get("packet_ready", False)),
        "critical_prompt_surface_packet_ready": bool(critical_prompt_surface_packet_summary.get("packet_ready", False)),
        "partner_binding_parity_packet_ready": bool(partner_binding_parity_packet_summary.get("packet_ready", False)),
        "thinking_prompt_bundle_ready": thinking_prompt_bundle_ready,
        "thinking_prompt_bundle_prompt_section_total": int(
            thinking_prompt_bundle_packet_summary.get("prompt_section_total", 0) or 0
        ),
        "thinking_prompt_bundle_operator_jump_case_total": int(
            thinking_prompt_bundle_packet_summary.get("operator_jump_case_total", 0) or 0
        ),
        "thinking_prompt_bundle_decision_ladder_row_total": int(
            thinking_prompt_bundle_packet_summary.get("decision_ladder_row_total", 0) or 0
        ),
        "thinking_prompt_bundle_runtime_target_ready": bool(
            thinking_prompt_bundle_packet_summary.get("runtime_target_ready", False)
        ),
        "thinking_prompt_bundle_release_target_ready": bool(
            thinking_prompt_bundle_packet_summary.get("release_target_ready", False)
        ),
        "thinking_prompt_bundle_operator_target_ready": bool(
            thinking_prompt_bundle_packet_summary.get("operator_target_ready", False)
        ),
        "thinking_prompt_bundle_json_path": thinking_prompt_bundle_json_path,
        "thinking_prompt_bundle_md_path": thinking_prompt_bundle_md_path,
        "partner_binding_observability_ready": partner_binding_observability_ready,
        "partner_binding_expected_family_total": int(
            partner_binding_observability_summary.get("expected_family_total", 0) or 0
        ),
        "partner_binding_widget_family_total": int(
            partner_binding_observability_summary.get("widget_binding_family_total", 0) or 0
        ),
        "partner_binding_api_family_total": int(
            partner_binding_observability_summary.get("api_binding_family_total", 0) or 0
        ),
        "partner_binding_widget_missing_total": int(
            partner_binding_observability_summary.get("widget_missing_family_total", 0) or 0
        ),
        "partner_binding_api_missing_total": int(
            partner_binding_observability_summary.get("api_missing_family_total", 0) or 0
        ),
        "partner_binding_observability_json_path": partner_binding_observability_json_path,
        "partner_binding_observability_md_path": partner_binding_observability_md_path,
        "partner_binding_widget_missing_preview": [
            str(item.get("claim_id") or "")
            for item in list((partner_binding_observability_report or {}).get("widget_missing_preview") or [])[:5]
            if isinstance(item, dict) and str(item.get("claim_id") or "").strip()
        ],
        "partner_binding_api_missing_preview": [
            str(item.get("claim_id") or "")
            for item in list((partner_binding_observability_report or {}).get("api_missing_preview") or [])[:5]
            if isinstance(item, dict) and str(item.get("claim_id") or "").strip()
        ],
        "partner_gap_preview_digest_ready": bool(
            partner_gap_preview_digest_summary.get("digest_ready", False)
        ),
        "partner_gap_preview_blank_binding_preset_total": int(
            partner_gap_preview_digest_summary.get("blank_binding_preset_total", 0) or 0
        ),
        "partner_gap_preview_widget_preset_mismatch_total": int(
            partner_gap_preview_digest_summary.get("widget_preset_mismatch_total", 0) or 0
        ),
        "partner_gap_preview_api_preset_mismatch_total": int(
            partner_gap_preview_digest_summary.get("api_preset_mismatch_total", 0) or 0
        ),
        "partner_gap_preview_json_path": partner_gap_preview_digest_json_path,
        "partner_gap_preview_md_path": partner_gap_preview_digest_md_path,
        "partner_gap_preview_blank_binding_preview": [
            str(item.get("claim_id") or "")
            for item in list((partner_gap_preview_digest_report or {}).get("blank_binding_preset_preview") or [])[:5]
            if isinstance(item, dict) and str(item.get("claim_id") or "").strip()
        ],
        "capital_registration_logic_packet_ready": bool(
            capital_registration_logic_packet_summary.get("packet_ready", False)
        ),
        "capital_registration_focus_total": int(
            capital_registration_logic_packet_summary.get("focus_target_total", 0) or 0
        ),
            "capital_registration_family_total": int(
                capital_registration_logic_packet_summary.get("family_total", 0) or 0
            ),
            "capital_registration_core_only_guarded_total": int(
                capital_registration_logic_packet_summary.get("core_only_guarded_total", 0) or 0
            ),
            "capital_evidence_missing_total": int(
                capital_registration_logic_packet_summary.get("capital_evidence_missing_total", 0) or 0
            ),
        "technical_evidence_missing_total": int(
            capital_registration_logic_packet_summary.get("technical_evidence_missing_total", 0) or 0
        ),
        "other_evidence_missing_total": int(
            capital_registration_logic_packet_summary.get("other_evidence_missing_total", 0) or 0
        ),
        "capital_registration_primary_gap_id": _safe_str(
            capital_registration_logic_packet_summary.get("primary_gap_id")
        ),
        "review_reason_total": int(review_reason_decision_ladder_summary.get("review_reason_total", 0) or 0),
        "review_reason_manual_review_gate_total": int(
            review_reason_decision_ladder_summary.get("manual_review_gate_total", 0) or 0
        ),
        "review_reason_prompt_bound_total": int(
            review_reason_decision_ladder_summary.get("prompt_bound_reason_total", 0) or 0
        ),
        "review_reason_decision_ladder_ready": bool(
            review_reason_decision_ladder_summary.get("decision_ladder_ready", False)
        ),
        "demo_surface_observability_ready": demo_surface_observability_ready,
        "demo_surface_observability_json_path": demo_surface_observability_json_path,
        "demo_surface_observability_md_path": demo_surface_observability_md_path,
        "runtime_reasoning_card_surface_ready": bool(
            demo_surface_observability_summary.get("runtime_reasoning_card_surface_ready", False)
        ),
        "runtime_reasoning_review_reason_total": int(
            runtime_reasoning_guard_summary.get(
                "review_reason_total",
                demo_surface_observability_summary.get(
                    "runtime_reasoning_review_reason_total",
                    review_reason_decision_ladder_summary.get("review_reason_total", 0),
                ),
            )
            or 0
        ),
        "runtime_reasoning_prompt_bound_total": int(
            runtime_reasoning_guard_summary.get(
                "prompt_bound_reason_total",
                demo_surface_observability_summary.get(
                    "runtime_reasoning_prompt_bound_total",
                    review_reason_decision_ladder_summary.get("prompt_bound_reason_total", 0),
                ),
            )
            or 0
        ),
        "runtime_reasoning_binding_gap_total": int(
            runtime_reasoning_guard_summary.get(
                "binding_gap_total",
                demo_surface_observability_summary.get("runtime_reasoning_binding_gap_total", 0),
            )
            or 0
        ),
        "runtime_reasoning_guard_ready": bool(runtime_reasoning_guard_summary.get("guard_ready", False)),
        "runtime_reasoning_guard_json_path": runtime_reasoning_guard_json_path,
        "runtime_reasoning_guard_md_path": runtime_reasoning_guard_md_path,
        "closed_lane_stale_audit_ready": bool(closed_lane_stale_audit_summary.get("audit_ready", False)),
        "closed_lane_id": _safe_str(closed_lane_stale_audit_summary.get("closed_lane_id")),
        "closed_lane_stale_reference_total": int(
            closed_lane_stale_audit_summary.get("stale_reference_total", 0) or 0
        ),
        "closed_lane_stale_artifact_total": int(
            closed_lane_stale_audit_summary.get("stale_artifact_total", 0) or 0
        ),
        "closed_lane_stale_primary_lane_total": int(
            closed_lane_stale_audit_summary.get("stale_primary_lane_total", 0) or 0
        ),
        "closed_lane_stale_system_bottleneck_total": int(
            closed_lane_stale_audit_summary.get("stale_system_bottleneck_total", 0) or 0
        ),
        "closed_lane_stale_prompt_bundle_lane_total": int(
            closed_lane_stale_audit_summary.get("stale_prompt_bundle_lane_total", 0) or 0
        ),
        "closed_lane_stale_audit_json_path": closed_lane_stale_audit_json_path,
        "closed_lane_stale_audit_md_path": closed_lane_stale_audit_md_path,
        "surface_drift_digest_ready": surface_drift_digest_ready,
        "surface_drift_digest_delta_ready": bool(surface_drift_digest_summary.get("delta_ready", False)),
        "surface_drift_changed_surface_total": int(surface_drift_digest_summary.get("changed_surface_total", 0) or 0),
        "surface_drift_readiness_flip_total": int(surface_drift_digest_summary.get("readiness_flip_total", 0) or 0),
        "surface_drift_reasoning_changed_surface_total": int(
            surface_drift_digest_summary.get("reasoning_changed_surface_total", 0) or 0
        ),
        "surface_drift_reasoning_regression_total": int(
            surface_drift_digest_summary.get("reasoning_regression_total", 0) or 0
        ),
        "surface_drift_digest_json_path": surface_drift_digest_json_path,
        "surface_drift_digest_md_path": surface_drift_digest_md_path,
        "critical_prompt_doc_ready": critical_prompt_doc_ready,
        "critical_prompt_doc_path": str(DEFAULT_PROMPT_DOC.resolve()),
        "runtime_missing_cases": list(case_guard_missing.get("runtime_cases") or [])[:5],
        "widget_missing_cases": list(case_guard_missing.get("widget_cases") or [])[:5],
        "api_missing_cases": list(case_guard_missing.get("api_cases") or [])[:5],
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cwd": str(ROOT),
        "python_executable": python_executable,
        "summary": {
            "step_total": len(step_results),
            "ok_total": sum(1 for row in step_results if bool(row.get("ok"))),
            "failed_total": len(failed),
            "blocking_failure_name": str(failed[0].get("name", "") or "") if failed else "",
            "release_ready": not failed,
            "case_release_guard_ready": bool(case_guard_summary.get("release_guard_ready", False)),
            "case_release_guard_family_total": int(case_guard_summary.get("family_total", 0) or 0),
            "case_release_guard_case_total": int(case_guard_summary.get("case_total", 0) or 0),
            "case_release_guard_failed_total": case_guard_failed_total,
            "case_release_guard_preview_ready": bool(case_guard_summary),
            "review_case_preset_ready": bool(review_case_presets_summary.get("preset_ready", False)),
            "review_case_preset_total": int(review_case_presets_summary.get("preset_total", 0) or 0),
            "review_case_manual_review_total": int(
                review_case_presets_summary.get("manual_review_expected_total", 0) or 0
            ),
            "case_story_surface_ready": bool(case_story_surface_summary.get("story_ready", False)),
            "case_story_family_total": int(case_story_surface_summary.get("story_family_total", 0) or 0),
            "case_story_review_reason_total": int(case_story_surface_summary.get("review_reason_total", 0) or 0),
            "case_story_manual_review_family_total": int(
                case_story_surface_summary.get("manual_review_family_total", 0) or 0
            ),
            "preset_story_release_guard_ready": bool(
                preset_story_guard_summary.get("preset_story_guard_ready", False)
            ),
            "runtime_review_preset_surface_ready": bool(
                preset_story_guard_summary.get("runtime_review_preset_surface_ready", False)
            ),
            "runtime_case_story_surface_ready": bool(
                preset_story_guard_summary.get("runtime_case_story_surface_ready", False)
            ),
            "story_contract_parity_ready": bool(
                preset_story_guard_summary.get("story_contract_parity_ready", False)
            ),
            "operator_demo_ready": bool(operator_demo_summary.get("operator_demo_ready", False)),
            "operator_demo_release_surface_ready": operator_demo_release_surface_ready,
            "operator_demo_family_total": int(operator_demo_summary.get("family_total", 0) or 0),
            "operator_demo_case_total": int(operator_demo_summary.get("demo_case_total", 0) or 0),
            "operator_demo_packet_json_path": operator_demo_packet_json_path,
            "operator_demo_packet_md_path": operator_demo_packet_md_path,
            "widget_partner_demo_surface_ready": widget_partner_demo_surface_ready,
            "api_partner_demo_surface_ready": api_partner_demo_surface_ready,
            "partner_demo_surface_ready": partner_demo_surface_ready,
            "widget_partner_binding_surface_ready": widget_partner_binding_surface_ready,
            "api_partner_binding_surface_ready": api_partner_binding_surface_ready,
            "partner_binding_surface_ready": widget_partner_binding_surface_ready and api_partner_binding_surface_ready,
            "prompt_case_binding_packet_ready": bool(prompt_case_binding_packet_summary.get("packet_ready", False)),
            "critical_prompt_surface_packet_ready": bool(critical_prompt_surface_packet_summary.get("packet_ready", False)),
            "partner_binding_parity_packet_ready": bool(partner_binding_parity_packet_summary.get("packet_ready", False)),
            "thinking_prompt_bundle_ready": thinking_prompt_bundle_ready,
            "thinking_prompt_bundle_prompt_section_total": int(
                thinking_prompt_bundle_packet_summary.get("prompt_section_total", 0) or 0
            ),
            "thinking_prompt_bundle_operator_jump_case_total": int(
                thinking_prompt_bundle_packet_summary.get("operator_jump_case_total", 0) or 0
            ),
            "thinking_prompt_bundle_decision_ladder_row_total": int(
                thinking_prompt_bundle_packet_summary.get("decision_ladder_row_total", 0) or 0
            ),
            "thinking_prompt_bundle_runtime_target_ready": bool(
                thinking_prompt_bundle_packet_summary.get("runtime_target_ready", False)
            ),
            "thinking_prompt_bundle_release_target_ready": bool(
                thinking_prompt_bundle_packet_summary.get("release_target_ready", False)
            ),
            "thinking_prompt_bundle_operator_target_ready": bool(
                thinking_prompt_bundle_packet_summary.get("operator_target_ready", False)
            ),
            "thinking_prompt_bundle_json_path": thinking_prompt_bundle_json_path,
            "thinking_prompt_bundle_md_path": thinking_prompt_bundle_md_path,
            "partner_binding_observability_ready": partner_binding_observability_ready,
            "partner_binding_expected_family_total": int(
                partner_binding_observability_summary.get("expected_family_total", 0) or 0
            ),
            "partner_binding_widget_family_total": int(
                partner_binding_observability_summary.get("widget_binding_family_total", 0) or 0
            ),
            "partner_binding_api_family_total": int(
                partner_binding_observability_summary.get("api_binding_family_total", 0) or 0
            ),
            "partner_binding_widget_missing_total": int(
                partner_binding_observability_summary.get("widget_missing_family_total", 0) or 0
            ),
            "partner_binding_api_missing_total": int(
                partner_binding_observability_summary.get("api_missing_family_total", 0) or 0
            ),
            "partner_binding_observability_json_path": partner_binding_observability_json_path,
            "partner_binding_observability_md_path": partner_binding_observability_md_path,
            "partner_gap_preview_digest_ready": bool(
                partner_gap_preview_digest_summary.get("digest_ready", False)
            ),
            "partner_gap_preview_blank_binding_preset_total": int(
                partner_gap_preview_digest_summary.get("blank_binding_preset_total", 0) or 0
            ),
            "partner_gap_preview_widget_preset_mismatch_total": int(
                partner_gap_preview_digest_summary.get("widget_preset_mismatch_total", 0) or 0
            ),
            "partner_gap_preview_api_preset_mismatch_total": int(
                partner_gap_preview_digest_summary.get("api_preset_mismatch_total", 0) or 0
            ),
            "partner_gap_preview_json_path": partner_gap_preview_digest_json_path,
            "partner_gap_preview_md_path": partner_gap_preview_digest_md_path,
            "capital_registration_logic_packet_ready": bool(
                capital_registration_logic_packet_summary.get("packet_ready", False)
            ),
            "capital_registration_focus_total": int(
                capital_registration_logic_packet_summary.get("focus_target_total", 0) or 0
            ),
            "capital_registration_family_total": int(
                capital_registration_logic_packet_summary.get("family_total", 0) or 0
            ),
            "capital_registration_core_only_guarded_total": int(
                capital_registration_logic_packet_summary.get("core_only_guarded_total", 0) or 0
            ),
            "capital_evidence_missing_total": int(
                capital_registration_logic_packet_summary.get("capital_evidence_missing_total", 0) or 0
            ),
            "technical_evidence_missing_total": int(
                capital_registration_logic_packet_summary.get("technical_evidence_missing_total", 0) or 0
            ),
            "other_evidence_missing_total": int(
                capital_registration_logic_packet_summary.get("other_evidence_missing_total", 0) or 0
            ),
            "capital_registration_primary_gap_id": _safe_str(
                capital_registration_logic_packet_summary.get("primary_gap_id")
            ),
            "review_reason_total": int(review_reason_decision_ladder_summary.get("review_reason_total", 0) or 0),
            "review_reason_manual_review_gate_total": int(
                review_reason_decision_ladder_summary.get("manual_review_gate_total", 0) or 0
            ),
            "review_reason_prompt_bound_total": int(
                review_reason_decision_ladder_summary.get("prompt_bound_reason_total", 0) or 0
            ),
            "review_reason_decision_ladder_ready": bool(
                review_reason_decision_ladder_summary.get("decision_ladder_ready", False)
            ),
            "demo_surface_observability_ready": demo_surface_observability_ready,
            "demo_surface_observability_json_path": demo_surface_observability_json_path,
            "demo_surface_observability_md_path": demo_surface_observability_md_path,
            "runtime_reasoning_card_surface_ready": bool(
                demo_surface_observability_summary.get("runtime_reasoning_card_surface_ready", False)
            ),
            "runtime_reasoning_review_reason_total": int(
                runtime_reasoning_guard_summary.get(
                    "review_reason_total",
                    demo_surface_observability_summary.get(
                        "runtime_reasoning_review_reason_total",
                        review_reason_decision_ladder_summary.get("review_reason_total", 0),
                    ),
                )
                or 0
            ),
            "runtime_reasoning_prompt_bound_total": int(
                runtime_reasoning_guard_summary.get(
                    "prompt_bound_reason_total",
                    demo_surface_observability_summary.get(
                        "runtime_reasoning_prompt_bound_total",
                        review_reason_decision_ladder_summary.get("prompt_bound_reason_total", 0),
                    ),
                )
                or 0
            ),
            "runtime_reasoning_binding_gap_total": int(
                runtime_reasoning_guard_summary.get(
                    "binding_gap_total",
                    demo_surface_observability_summary.get("runtime_reasoning_binding_gap_total", 0),
                )
                or 0
            ),
            "runtime_reasoning_guard_ready": bool(runtime_reasoning_guard_summary.get("guard_ready", False)),
            "runtime_reasoning_guard_json_path": runtime_reasoning_guard_json_path,
            "runtime_reasoning_guard_md_path": runtime_reasoning_guard_md_path,
            "closed_lane_stale_audit_ready": bool(closed_lane_stale_audit_summary.get("audit_ready", False)),
            "closed_lane_id": _safe_str(closed_lane_stale_audit_summary.get("closed_lane_id")),
            "closed_lane_stale_reference_total": int(
                closed_lane_stale_audit_summary.get("stale_reference_total", 0) or 0
            ),
            "closed_lane_stale_artifact_total": int(
                closed_lane_stale_audit_summary.get("stale_artifact_total", 0) or 0
            ),
            "closed_lane_stale_primary_lane_total": int(
                closed_lane_stale_audit_summary.get("stale_primary_lane_total", 0) or 0
            ),
            "closed_lane_stale_system_bottleneck_total": int(
                closed_lane_stale_audit_summary.get("stale_system_bottleneck_total", 0) or 0
            ),
            "closed_lane_stale_prompt_bundle_lane_total": int(
                closed_lane_stale_audit_summary.get("stale_prompt_bundle_lane_total", 0) or 0
            ),
            "closed_lane_stale_audit_json_path": closed_lane_stale_audit_json_path,
            "closed_lane_stale_audit_md_path": closed_lane_stale_audit_md_path,
            "surface_drift_digest_ready": surface_drift_digest_ready,
            "surface_drift_digest_delta_ready": bool(surface_drift_digest_summary.get("delta_ready", False)),
            "surface_drift_changed_surface_total": int(surface_drift_digest_summary.get("changed_surface_total", 0) or 0),
            "surface_drift_readiness_flip_total": int(surface_drift_digest_summary.get("readiness_flip_total", 0) or 0),
            "surface_drift_reasoning_changed_surface_total": int(
                surface_drift_digest_summary.get("reasoning_changed_surface_total", 0) or 0
            ),
            "surface_drift_reasoning_regression_total": int(
                surface_drift_digest_summary.get("reasoning_regression_total", 0) or 0
            ),
            "surface_drift_digest_json_path": surface_drift_digest_json_path,
            "surface_drift_digest_md_path": surface_drift_digest_md_path,
            "critical_prompt_doc_ready": critical_prompt_doc_ready,
            "critical_prompt_doc_path": str(DEFAULT_PROMPT_DOC.resolve()),
            "critical_prompt_doc_excerpt": critical_prompt_doc_excerpt,
        },
        "partner_qa_snapshot": partner_qa_snapshot,
        "steps": step_results,
    }


def render_markdown(manifest: Dict[str, Any]) -> str:
    summary = dict(manifest.get("summary") or {})
    lines = [
        "# Permit Release Bundle",
        "",
        "## Summary",
        f"- generated_at: `{manifest.get('generated_at', '')}`",
        f"- python_executable: `{manifest.get('python_executable', '')}`",
        f"- step_total: `{summary.get('step_total', 0)}`",
        f"- ok_total: `{summary.get('ok_total', 0)}`",
        f"- failed_total: `{summary.get('failed_total', 0)}`",
        f"- blocking_failure_name: `{summary.get('blocking_failure_name', '')}`",
        f"- release_ready: `{summary.get('release_ready', False)}`",
        f"- case_release_guard_ready: `{summary.get('case_release_guard_ready', False)}`",
        f"- case_release_guard_family_total: `{summary.get('case_release_guard_family_total', 0)}`",
        f"- case_release_guard_case_total: `{summary.get('case_release_guard_case_total', 0)}`",
        f"- case_release_guard_failed_total: `{summary.get('case_release_guard_failed_total', 0)}`",
        f"- case_release_guard_preview_ready: `{summary.get('case_release_guard_preview_ready', False)}`",
        f"- review_case_preset_ready: `{summary.get('review_case_preset_ready', False)}`",
        f"- review_case_preset_total: `{summary.get('review_case_preset_total', 0)}`",
        f"- review_case_manual_review_total: `{summary.get('review_case_manual_review_total', 0)}`",
        f"- case_story_surface_ready: `{summary.get('case_story_surface_ready', False)}`",
        f"- case_story_family_total: `{summary.get('case_story_family_total', 0)}`",
        f"- case_story_review_reason_total: `{summary.get('case_story_review_reason_total', 0)}`",
        f"- case_story_manual_review_family_total: `{summary.get('case_story_manual_review_family_total', 0)}`",
        f"- preset_story_release_guard_ready: `{summary.get('preset_story_release_guard_ready', False)}`",
        f"- runtime_review_preset_surface_ready: `{summary.get('runtime_review_preset_surface_ready', False)}`",
        f"- runtime_case_story_surface_ready: `{summary.get('runtime_case_story_surface_ready', False)}`",
        f"- story_contract_parity_ready: `{summary.get('story_contract_parity_ready', False)}`",
        f"- operator_demo_ready: `{summary.get('operator_demo_ready', False)}`",
        f"- operator_demo_release_surface_ready: `{summary.get('operator_demo_release_surface_ready', False)}`",
        f"- operator_demo_family_total: `{summary.get('operator_demo_family_total', 0)}`",
        f"- operator_demo_case_total: `{summary.get('operator_demo_case_total', 0)}`",
        f"- operator_demo_packet_json_path: `{summary.get('operator_demo_packet_json_path', '')}`",
        f"- operator_demo_packet_md_path: `{summary.get('operator_demo_packet_md_path', '')}`",
        f"- widget_partner_demo_surface_ready: `{summary.get('widget_partner_demo_surface_ready', False)}`",
        f"- api_partner_demo_surface_ready: `{summary.get('api_partner_demo_surface_ready', False)}`",
        f"- partner_demo_surface_ready: `{summary.get('partner_demo_surface_ready', False)}`",
        f"- widget_partner_binding_surface_ready: `{summary.get('widget_partner_binding_surface_ready', False)}`",
        f"- api_partner_binding_surface_ready: `{summary.get('api_partner_binding_surface_ready', False)}`",
        f"- partner_binding_surface_ready: `{summary.get('partner_binding_surface_ready', False)}`",
        f"- prompt_case_binding_packet_ready: `{summary.get('prompt_case_binding_packet_ready', False)}`",
        f"- critical_prompt_surface_packet_ready: `{summary.get('critical_prompt_surface_packet_ready', False)}`",
        f"- partner_binding_parity_packet_ready: `{summary.get('partner_binding_parity_packet_ready', False)}`",
        f"- thinking_prompt_bundle_ready: `{summary.get('thinking_prompt_bundle_ready', False)}`",
        f"- thinking_prompt_bundle_prompt_section_total: `{summary.get('thinking_prompt_bundle_prompt_section_total', 0)}`",
        f"- thinking_prompt_bundle_operator_jump_case_total: `{summary.get('thinking_prompt_bundle_operator_jump_case_total', 0)}`",
        f"- thinking_prompt_bundle_decision_ladder_row_total: `{summary.get('thinking_prompt_bundle_decision_ladder_row_total', 0)}`",
        f"- thinking_prompt_bundle_runtime_target_ready: `{summary.get('thinking_prompt_bundle_runtime_target_ready', False)}`",
        f"- thinking_prompt_bundle_release_target_ready: `{summary.get('thinking_prompt_bundle_release_target_ready', False)}`",
        f"- thinking_prompt_bundle_operator_target_ready: `{summary.get('thinking_prompt_bundle_operator_target_ready', False)}`",
        f"- thinking_prompt_bundle_json_path: `{summary.get('thinking_prompt_bundle_json_path', '')}`",
        f"- thinking_prompt_bundle_md_path: `{summary.get('thinking_prompt_bundle_md_path', '')}`",
        f"- partner_binding_observability_ready: `{summary.get('partner_binding_observability_ready', False)}`",
        f"- partner_binding_expected_family_total: `{summary.get('partner_binding_expected_family_total', 0)}`",
        f"- partner_binding_widget_family_total: `{summary.get('partner_binding_widget_family_total', 0)}`",
        f"- partner_binding_api_family_total: `{summary.get('partner_binding_api_family_total', 0)}`",
        f"- partner_binding_widget_missing_total: `{summary.get('partner_binding_widget_missing_total', 0)}`",
        f"- partner_binding_api_missing_total: `{summary.get('partner_binding_api_missing_total', 0)}`",
        f"- partner_binding_observability_json_path: `{summary.get('partner_binding_observability_json_path', '')}`",
        f"- partner_binding_observability_md_path: `{summary.get('partner_binding_observability_md_path', '')}`",
        f"- partner_gap_preview_digest_ready: `{summary.get('partner_gap_preview_digest_ready', False)}`",
        f"- partner_gap_preview_blank_binding_preset_total: `{summary.get('partner_gap_preview_blank_binding_preset_total', 0)}`",
        f"- partner_gap_preview_widget_preset_mismatch_total: `{summary.get('partner_gap_preview_widget_preset_mismatch_total', 0)}`",
        f"- partner_gap_preview_api_preset_mismatch_total: `{summary.get('partner_gap_preview_api_preset_mismatch_total', 0)}`",
        f"- partner_gap_preview_json_path: `{summary.get('partner_gap_preview_json_path', '')}`",
        f"- partner_gap_preview_md_path: `{summary.get('partner_gap_preview_md_path', '')}`",
        f"- capital_registration_logic_packet_ready: `{summary.get('capital_registration_logic_packet_ready', False)}`",
        f"- capital_registration_focus_total: `{summary.get('capital_registration_focus_total', 0)}`",
        f"- capital_registration_family_total: `{summary.get('capital_registration_family_total', 0)}`",
        f"- capital_registration_core_only_guarded_total: `{summary.get('capital_registration_core_only_guarded_total', 0)}`",
        f"- capital_evidence_missing_total: `{summary.get('capital_evidence_missing_total', 0)}`",
        f"- technical_evidence_missing_total: `{summary.get('technical_evidence_missing_total', 0)}`",
        f"- other_evidence_missing_total: `{summary.get('other_evidence_missing_total', 0)}`",
        f"- capital_registration_primary_gap_id: `{summary.get('capital_registration_primary_gap_id', '')}`",
        f"- review_reason_total: `{summary.get('review_reason_total', 0)}`",
        f"- review_reason_manual_review_gate_total: `{summary.get('review_reason_manual_review_gate_total', 0)}`",
        f"- review_reason_prompt_bound_total: `{summary.get('review_reason_prompt_bound_total', 0)}`",
        f"- review_reason_decision_ladder_ready: `{summary.get('review_reason_decision_ladder_ready', False)}`",
        f"- demo_surface_observability_ready: `{summary.get('demo_surface_observability_ready', False)}`",
        f"- demo_surface_observability_json_path: `{summary.get('demo_surface_observability_json_path', '')}`",
        f"- demo_surface_observability_md_path: `{summary.get('demo_surface_observability_md_path', '')}`",
        f"- runtime_reasoning_card_surface_ready: `{summary.get('runtime_reasoning_card_surface_ready', False)}`",
        f"- runtime_reasoning_review_reason_total: `{summary.get('runtime_reasoning_review_reason_total', 0)}`",
        f"- runtime_reasoning_prompt_bound_total: `{summary.get('runtime_reasoning_prompt_bound_total', 0)}`",
        f"- runtime_reasoning_binding_gap_total: `{summary.get('runtime_reasoning_binding_gap_total', 0)}`",
        f"- runtime_reasoning_guard_ready: `{summary.get('runtime_reasoning_guard_ready', False)}`",
        f"- runtime_reasoning_guard_json_path: `{summary.get('runtime_reasoning_guard_json_path', '')}`",
        f"- runtime_reasoning_guard_md_path: `{summary.get('runtime_reasoning_guard_md_path', '')}`",
        f"- closed_lane_stale_audit_ready: `{summary.get('closed_lane_stale_audit_ready', False)}`",
        f"- closed_lane_id: `{summary.get('closed_lane_id', '')}`",
        f"- closed_lane_stale_reference_total: `{summary.get('closed_lane_stale_reference_total', 0)}`",
        f"- closed_lane_stale_artifact_total: `{summary.get('closed_lane_stale_artifact_total', 0)}`",
        f"- closed_lane_stale_primary_lane_total: `{summary.get('closed_lane_stale_primary_lane_total', 0)}`",
        f"- closed_lane_stale_system_bottleneck_total: `{summary.get('closed_lane_stale_system_bottleneck_total', 0)}`",
        f"- closed_lane_stale_prompt_bundle_lane_total: `{summary.get('closed_lane_stale_prompt_bundle_lane_total', 0)}`",
        f"- closed_lane_stale_audit_json_path: `{summary.get('closed_lane_stale_audit_json_path', '')}`",
        f"- closed_lane_stale_audit_md_path: `{summary.get('closed_lane_stale_audit_md_path', '')}`",
        f"- surface_drift_digest_ready: `{summary.get('surface_drift_digest_ready', False)}`",
        f"- surface_drift_digest_delta_ready: `{summary.get('surface_drift_digest_delta_ready', False)}`",
        f"- surface_drift_changed_surface_total: `{summary.get('surface_drift_changed_surface_total', 0)}`",
        f"- surface_drift_readiness_flip_total: `{summary.get('surface_drift_readiness_flip_total', 0)}`",
        f"- surface_drift_reasoning_changed_surface_total: `{summary.get('surface_drift_reasoning_changed_surface_total', 0)}`",
        f"- surface_drift_reasoning_regression_total: `{summary.get('surface_drift_reasoning_regression_total', 0)}`",
        f"- surface_drift_digest_json_path: `{summary.get('surface_drift_digest_json_path', '')}`",
        f"- surface_drift_digest_md_path: `{summary.get('surface_drift_digest_md_path', '')}`",
        f"- critical_prompt_doc_ready: `{summary.get('critical_prompt_doc_ready', False)}`",
        f"- critical_prompt_doc_path: `{summary.get('critical_prompt_doc_path', '')}`",
        "",
        "## Steps",
    ]
    for row in list(manifest.get("steps") or []):
        if not isinstance(row, dict):
            continue
        outputs = ", ".join(str(item) for item in list(row.get("outputs") or []) if str(item).strip())
        lines.append(
            f"- `{row.get('name', '')}` ok={row.get('ok', False)} returncode={row.get('returncode', '')} "
            f"duration_sec={row.get('duration_sec', '')}"
            + (f" / outputs {outputs}" if outputs else "")
        )
    partner_qa_snapshot = dict(manifest.get("partner_qa_snapshot") or {})
    lines.extend(
        [
            "",
            "## Partner QA Snapshot",
            f"- release_guard_ready: `{partner_qa_snapshot.get('release_guard_ready', False)}`",
            f"- family_total: `{partner_qa_snapshot.get('family_total', 0)}`",
            f"- case_total: `{partner_qa_snapshot.get('case_total', 0)}`",
            f"- failed_total: `{partner_qa_snapshot.get('failed_total', 0)}`",
            f"- review_case_preset_total: `{partner_qa_snapshot.get('review_case_preset_total', 0)}`",
            f"- case_story_family_total: `{partner_qa_snapshot.get('case_story_family_total', 0)}`",
            f"- case_story_review_reason_total: `{partner_qa_snapshot.get('case_story_review_reason_total', 0)}`",
            f"- case_story_manual_review_family_total: `{partner_qa_snapshot.get('case_story_manual_review_family_total', 0)}`",
            f"- preset_story_release_guard_ready: `{partner_qa_snapshot.get('preset_story_release_guard_ready', False)}`",
            f"- runtime_review_preset_surface_ready: `{partner_qa_snapshot.get('runtime_review_preset_surface_ready', False)}`",
            f"- runtime_case_story_surface_ready: `{partner_qa_snapshot.get('runtime_case_story_surface_ready', False)}`",
            f"- story_contract_parity_ready: `{partner_qa_snapshot.get('story_contract_parity_ready', False)}`",
            f"- operator_demo_ready: `{partner_qa_snapshot.get('operator_demo_ready', False)}`",
            f"- operator_demo_release_surface_ready: `{partner_qa_snapshot.get('operator_demo_release_surface_ready', False)}`",
            f"- operator_demo_family_total: `{partner_qa_snapshot.get('operator_demo_family_total', 0)}`",
            f"- operator_demo_case_total: `{partner_qa_snapshot.get('operator_demo_case_total', 0)}`",
            f"- operator_demo_packet_json_path: `{partner_qa_snapshot.get('operator_demo_packet_json_path', '')}`",
            f"- operator_demo_packet_md_path: `{partner_qa_snapshot.get('operator_demo_packet_md_path', '')}`",
            f"- widget_partner_demo_surface_ready: `{partner_qa_snapshot.get('widget_partner_demo_surface_ready', False)}`",
            f"- api_partner_demo_surface_ready: `{partner_qa_snapshot.get('api_partner_demo_surface_ready', False)}`",
            f"- partner_demo_surface_ready: `{partner_qa_snapshot.get('partner_demo_surface_ready', False)}`",
            f"- widget_partner_binding_surface_ready: `{partner_qa_snapshot.get('widget_partner_binding_surface_ready', False)}`",
            f"- api_partner_binding_surface_ready: `{partner_qa_snapshot.get('api_partner_binding_surface_ready', False)}`",
            f"- partner_binding_surface_ready: `{partner_qa_snapshot.get('partner_binding_surface_ready', False)}`",
            f"- prompt_case_binding_packet_ready: `{partner_qa_snapshot.get('prompt_case_binding_packet_ready', False)}`",
            f"- critical_prompt_surface_packet_ready: `{partner_qa_snapshot.get('critical_prompt_surface_packet_ready', False)}`",
            f"- partner_binding_parity_packet_ready: `{partner_qa_snapshot.get('partner_binding_parity_packet_ready', False)}`",
            f"- thinking_prompt_bundle_ready: `{partner_qa_snapshot.get('thinking_prompt_bundle_ready', False)}`",
            f"- thinking_prompt_bundle_prompt_section_total: `{partner_qa_snapshot.get('thinking_prompt_bundle_prompt_section_total', 0)}`",
            f"- thinking_prompt_bundle_operator_jump_case_total: `{partner_qa_snapshot.get('thinking_prompt_bundle_operator_jump_case_total', 0)}`",
            f"- thinking_prompt_bundle_decision_ladder_row_total: `{partner_qa_snapshot.get('thinking_prompt_bundle_decision_ladder_row_total', 0)}`",
            f"- thinking_prompt_bundle_runtime_target_ready: `{partner_qa_snapshot.get('thinking_prompt_bundle_runtime_target_ready', False)}`",
            f"- thinking_prompt_bundle_release_target_ready: `{partner_qa_snapshot.get('thinking_prompt_bundle_release_target_ready', False)}`",
            f"- thinking_prompt_bundle_operator_target_ready: `{partner_qa_snapshot.get('thinking_prompt_bundle_operator_target_ready', False)}`",
            f"- thinking_prompt_bundle_json_path: `{partner_qa_snapshot.get('thinking_prompt_bundle_json_path', '')}`",
            f"- thinking_prompt_bundle_md_path: `{partner_qa_snapshot.get('thinking_prompt_bundle_md_path', '')}`",
            f"- partner_binding_observability_ready: `{partner_qa_snapshot.get('partner_binding_observability_ready', False)}`",
            f"- partner_binding_expected_family_total: `{partner_qa_snapshot.get('partner_binding_expected_family_total', 0)}`",
            f"- partner_binding_widget_family_total: `{partner_qa_snapshot.get('partner_binding_widget_family_total', 0)}`",
            f"- partner_binding_api_family_total: `{partner_qa_snapshot.get('partner_binding_api_family_total', 0)}`",
            f"- partner_binding_widget_missing_total: `{partner_qa_snapshot.get('partner_binding_widget_missing_total', 0)}`",
            f"- partner_binding_api_missing_total: `{partner_qa_snapshot.get('partner_binding_api_missing_total', 0)}`",
            f"- partner_binding_observability_json_path: `{partner_qa_snapshot.get('partner_binding_observability_json_path', '')}`",
            f"- partner_binding_observability_md_path: `{partner_qa_snapshot.get('partner_binding_observability_md_path', '')}`",
            f"- partner_gap_preview_digest_ready: `{partner_qa_snapshot.get('partner_gap_preview_digest_ready', False)}`",
            f"- partner_gap_preview_blank_binding_preset_total: `{partner_qa_snapshot.get('partner_gap_preview_blank_binding_preset_total', 0)}`",
            f"- partner_gap_preview_widget_preset_mismatch_total: `{partner_qa_snapshot.get('partner_gap_preview_widget_preset_mismatch_total', 0)}`",
            f"- partner_gap_preview_api_preset_mismatch_total: `{partner_qa_snapshot.get('partner_gap_preview_api_preset_mismatch_total', 0)}`",
            f"- partner_gap_preview_json_path: `{partner_qa_snapshot.get('partner_gap_preview_json_path', '')}`",
            f"- partner_gap_preview_md_path: `{partner_qa_snapshot.get('partner_gap_preview_md_path', '')}`",
            f"- capital_registration_logic_packet_ready: `{partner_qa_snapshot.get('capital_registration_logic_packet_ready', False)}`",
        f"- capital_registration_focus_total: `{partner_qa_snapshot.get('capital_registration_focus_total', 0)}`",
        f"- capital_registration_family_total: `{partner_qa_snapshot.get('capital_registration_family_total', 0)}`",
        f"- capital_registration_core_only_guarded_total: `{partner_qa_snapshot.get('capital_registration_core_only_guarded_total', 0)}`",
        f"- capital_evidence_missing_total: `{partner_qa_snapshot.get('capital_evidence_missing_total', 0)}`",
            f"- technical_evidence_missing_total: `{partner_qa_snapshot.get('technical_evidence_missing_total', 0)}`",
            f"- other_evidence_missing_total: `{partner_qa_snapshot.get('other_evidence_missing_total', 0)}`",
            f"- capital_registration_primary_gap_id: `{partner_qa_snapshot.get('capital_registration_primary_gap_id', '')}`",
            f"- review_reason_total: `{partner_qa_snapshot.get('review_reason_total', 0)}`",
            f"- review_reason_manual_review_gate_total: `{partner_qa_snapshot.get('review_reason_manual_review_gate_total', 0)}`",
            f"- review_reason_prompt_bound_total: `{partner_qa_snapshot.get('review_reason_prompt_bound_total', 0)}`",
            f"- review_reason_decision_ladder_ready: `{partner_qa_snapshot.get('review_reason_decision_ladder_ready', False)}`",
            f"- demo_surface_observability_ready: `{partner_qa_snapshot.get('demo_surface_observability_ready', False)}`",
            f"- demo_surface_observability_json_path: `{partner_qa_snapshot.get('demo_surface_observability_json_path', '')}`",
            f"- demo_surface_observability_md_path: `{partner_qa_snapshot.get('demo_surface_observability_md_path', '')}`",
            f"- runtime_reasoning_card_surface_ready: `{partner_qa_snapshot.get('runtime_reasoning_card_surface_ready', False)}`",
            f"- runtime_reasoning_review_reason_total: `{partner_qa_snapshot.get('runtime_reasoning_review_reason_total', 0)}`",
            f"- runtime_reasoning_prompt_bound_total: `{partner_qa_snapshot.get('runtime_reasoning_prompt_bound_total', 0)}`",
            f"- runtime_reasoning_binding_gap_total: `{partner_qa_snapshot.get('runtime_reasoning_binding_gap_total', 0)}`",
            f"- runtime_reasoning_guard_ready: `{partner_qa_snapshot.get('runtime_reasoning_guard_ready', False)}`",
            f"- runtime_reasoning_guard_json_path: `{partner_qa_snapshot.get('runtime_reasoning_guard_json_path', '')}`",
            f"- runtime_reasoning_guard_md_path: `{partner_qa_snapshot.get('runtime_reasoning_guard_md_path', '')}`",
            f"- closed_lane_stale_audit_ready: `{partner_qa_snapshot.get('closed_lane_stale_audit_ready', False)}`",
            f"- closed_lane_id: `{partner_qa_snapshot.get('closed_lane_id', '')}`",
            f"- closed_lane_stale_reference_total: `{partner_qa_snapshot.get('closed_lane_stale_reference_total', 0)}`",
            f"- closed_lane_stale_artifact_total: `{partner_qa_snapshot.get('closed_lane_stale_artifact_total', 0)}`",
            f"- closed_lane_stale_primary_lane_total: `{partner_qa_snapshot.get('closed_lane_stale_primary_lane_total', 0)}`",
            f"- closed_lane_stale_system_bottleneck_total: `{partner_qa_snapshot.get('closed_lane_stale_system_bottleneck_total', 0)}`",
            f"- closed_lane_stale_prompt_bundle_lane_total: `{partner_qa_snapshot.get('closed_lane_stale_prompt_bundle_lane_total', 0)}`",
            f"- closed_lane_stale_audit_json_path: `{partner_qa_snapshot.get('closed_lane_stale_audit_json_path', '')}`",
            f"- closed_lane_stale_audit_md_path: `{partner_qa_snapshot.get('closed_lane_stale_audit_md_path', '')}`",
            f"- surface_drift_digest_ready: `{partner_qa_snapshot.get('surface_drift_digest_ready', False)}`",
            f"- surface_drift_digest_delta_ready: `{partner_qa_snapshot.get('surface_drift_digest_delta_ready', False)}`",
            f"- surface_drift_changed_surface_total: `{partner_qa_snapshot.get('surface_drift_changed_surface_total', 0)}`",
            f"- surface_drift_readiness_flip_total: `{partner_qa_snapshot.get('surface_drift_readiness_flip_total', 0)}`",
            f"- surface_drift_reasoning_changed_surface_total: `{partner_qa_snapshot.get('surface_drift_reasoning_changed_surface_total', 0)}`",
            f"- surface_drift_reasoning_regression_total: `{partner_qa_snapshot.get('surface_drift_reasoning_regression_total', 0)}`",
            f"- surface_drift_digest_json_path: `{partner_qa_snapshot.get('surface_drift_digest_json_path', '')}`",
            f"- surface_drift_digest_md_path: `{partner_qa_snapshot.get('surface_drift_digest_md_path', '')}`",
            f"- critical_prompt_doc_ready: `{partner_qa_snapshot.get('critical_prompt_doc_ready', False)}`",
            f"- critical_prompt_doc_path: `{partner_qa_snapshot.get('critical_prompt_doc_path', '')}`",
            f"- runtime_missing_cases: `{', '.join(partner_qa_snapshot.get('runtime_missing_cases', []))}`",
            f"- widget_missing_cases: `{', '.join(partner_qa_snapshot.get('widget_missing_cases', []))}`",
            f"- api_missing_cases: `{', '.join(partner_qa_snapshot.get('api_missing_cases', []))}`",
            f"- partner_binding_widget_missing_preview: `{', '.join(partner_qa_snapshot.get('partner_binding_widget_missing_preview', []))}`",
            f"- partner_binding_api_missing_preview: `{', '.join(partner_qa_snapshot.get('partner_binding_api_missing_preview', []))}`",
        ]
    )
    critical_prompt_doc_excerpt = summary.get("critical_prompt_doc_excerpt") or ""
    if isinstance(critical_prompt_doc_excerpt, str):
        critical_prompt_doc_excerpt_lines = [
            line.rstrip()
            for line in critical_prompt_doc_excerpt.splitlines()
            if line.strip()
        ]
    else:
        critical_prompt_doc_excerpt_lines = [
            str(line).rstrip()
            for line in list(critical_prompt_doc_excerpt)
            if str(line).strip()
        ]
    if critical_prompt_doc_excerpt_lines:
        lines.extend(
            [
                "",
                "## Critical Prompt Excerpt",
                "```text",
                *critical_prompt_doc_excerpt_lines,
                "```",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the dependent permit release bundle in a stable order.")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    manifest = run_bundle(python_executable=args.python)
    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(manifest), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0 if bool((manifest.get("summary") or {}).get("release_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
