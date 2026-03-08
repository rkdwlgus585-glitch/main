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
            "name": "permit_next_action_brainstorm",
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
    operator_demo_release_surface_ready = bool(
        operator_demo_summary.get("operator_demo_ready", False) and operator_demo_packet_md_path
    )
    widget_partner_demo_surface_ready = bool(widget_summary.get("permit_partner_demo_surface_ready", False))
    api_partner_demo_surface_ready = bool(api_contract_master_summary.get("partner_demo_surface_ready", False))
    partner_demo_surface_ready = widget_partner_demo_surface_ready and api_partner_demo_surface_ready
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
            f"- critical_prompt_doc_ready: `{partner_qa_snapshot.get('critical_prompt_doc_ready', False)}`",
            f"- critical_prompt_doc_path: `{partner_qa_snapshot.get('critical_prompt_doc_path', '')}`",
            f"- runtime_missing_cases: `{', '.join(partner_qa_snapshot.get('runtime_missing_cases', []))}`",
            f"- widget_missing_cases: `{', '.join(partner_qa_snapshot.get('widget_missing_cases', []))}`",
            f"- api_missing_cases: `{', '.join(partner_qa_snapshot.get('api_missing_cases', []))}`",
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
