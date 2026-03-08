#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRAINSTORM_INPUT = ROOT / "logs" / "permit_next_action_brainstorm_latest.json"
DEFAULT_OPERATOR_DEMO_PACKET_INPUT = ROOT / "logs" / "permit_operator_demo_packet_latest.json"
DEFAULT_REVIEW_REASON_DECISION_LADDER_INPUT = ROOT / "logs" / "permit_review_reason_decision_ladder_latest.json"
DEFAULT_CRITICAL_PROMPT_SURFACE_PACKET_INPUT = ROOT / "logs" / "permit_critical_prompt_surface_packet_latest.json"
DEFAULT_WIDGET_INPUT = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_API_CONTRACT_INPUT = ROOT / "logs" / "api_contract_spec_latest.json"
DEFAULT_CASE_RELEASE_GUARD_INPUT = ROOT / "logs" / "permit_case_release_guard_latest.json"
DEFAULT_PRESET_STORY_GUARD_INPUT = ROOT / "logs" / "permit_preset_story_release_guard_latest.json"
DEFAULT_CLOSED_LANE_STALE_AUDIT_INPUT = ROOT / "logs" / "permit_closed_lane_stale_audit_latest.json"
DEFAULT_RUNTIME_HTML_INPUT = ROOT / "output" / "ai_permit_precheck.html"
DEFAULT_PROMPT_DOC_INPUT = ROOT / "docs" / "permit_critical_thinking_prompt.md"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_demo_surface_observability_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_demo_surface_observability_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _expand_runtime_html_text(html: str) -> str:
    text = str(html or "")
    sources = [text]
    for encoded in re.findall(r'const encoded="([^"]+)";', text):
        try:
            decoded = base64.b64decode(str(encoded or "").strip()).decode("utf-8")
        except Exception:
            continue
        if decoded:
            sources.append(decoded)
    return "\n".join(sources)


def _runtime_operator_demo_surface_ready(html: str) -> bool:
    text = _expand_runtime_html_text(html)
    markers = (
        'id="operatorDemoBox"',
        "const renderOperatorDemoSurface = (industry) => {",
        "const getOperatorDemoSurface = (row) => (",
        "operator_demo_surface",
    )
    return all(marker in text for marker in markers)


def _runtime_critical_prompt_surface_ready(html: str) -> bool:
    text = _expand_runtime_html_text(html)
    markers = (
        "runtime_critical_prompt_excerpt",
        "runtime_critical_prompt_lens",
        "const renderOperatorDemoSurface = (industry) => {",
        'id="operatorDemoBox"',
    )
    return all(marker in text for marker in markers)


def _runtime_prompt_case_binding_surface_ready(html: str) -> bool:
    text = _expand_runtime_html_text(html)
    markers = (
        "prompt_case_binding",
        "data-prompt-preset-id",
        "const renderOperatorDemoSurface = (industry) => {",
    )
    return all(marker in text for marker in markers)


def _runtime_reasoning_card_surface_ready(html: str) -> bool:
    text = _expand_runtime_html_text(html)
    markers = (
        'id="runtimeReasoningCardBox"',
        "const renderRuntimeReasoningCard = (industry, typedEval, context = {}) => {",
        "data-runtime-preset-id",
        "runtime_reasoning_ladder_map",
    )
    return all(marker in text for marker in markers)


def _api_master_summary(api_contract_spec: Dict[str, Any]) -> Dict[str, Any]:
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
    master_contract = (
        catalog_contracts.get("master_catalog") if isinstance(catalog_contracts.get("master_catalog"), dict) else {}
    )
    return (
        master_contract.get("current_summary")
        if isinstance(master_contract.get("current_summary"), dict)
        else {}
    )


def _closed_lane_surface_ready(
    *,
    brainstorm_summary: Dict[str, Any],
    closed_lane_stale_audit_summary: Dict[str, Any],
) -> bool:
    stale_reference_total = int(closed_lane_stale_audit_summary.get("stale_reference_total", 0) or 0)
    if (
        bool(brainstorm_summary.get("closed_lane_stale_audit_ready", False))
        and int(brainstorm_summary.get("closed_lane_stale_reference_total", 0) or 0) == 0
    ):
        return True
    runtime_reasoning_guard_exit_ready = bool(
        brainstorm_summary.get(
            "runtime_reasoning_guard_exit_ready",
            closed_lane_stale_audit_summary.get("runtime_reasoning_guard_exit_ready", False),
        )
    )
    if _safe_str(brainstorm_summary.get("execution_lane")) == "runtime_reasoning_guard" and not runtime_reasoning_guard_exit_ready:
        return True
    if bool(closed_lane_stale_audit_summary.get("audit_skipped", False)):
        return True
    if not bool(closed_lane_stale_audit_summary.get("runtime_reasoning_guard_exit_ready", True)):
        return True
    return bool(closed_lane_stale_audit_summary.get("audit_ready", False)) and stale_reference_total == 0


def _health_digest_rows(
    *,
    active_execution_lane_id: str,
    brainstorm_summary: Dict[str, Any],
    critical_prompt_packet_summary: Dict[str, Any],
    widget_summary: Dict[str, Any],
    api_master_summary: Dict[str, Any],
    case_guard_summary: Dict[str, Any],
    preset_story_guard_summary: Dict[str, Any],
    review_reason_decision_ladder_summary: Dict[str, Any],
    runtime_html: str,
    closed_lane_stale_audit_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    prompt_contract_ready = all(
        [
            bool(critical_prompt_packet_summary.get("compact_lens_ready", False)),
            bool(critical_prompt_packet_summary.get("runtime_surface_contract_ready", False)),
            bool(critical_prompt_packet_summary.get("release_surface_contract_ready", False)),
            bool(critical_prompt_packet_summary.get("operator_surface_contract_ready", False)),
            _runtime_critical_prompt_surface_ready(runtime_html),
        ]
    )
    demo_parity_ready = all(
        [
            bool(widget_summary.get("permit_partner_demo_surface_ready", False)),
            bool(api_master_summary.get("partner_demo_surface_ready", False)),
            bool(case_guard_summary.get("release_guard_ready", False)),
            bool(preset_story_guard_summary.get("preset_story_guard_ready", False)),
        ]
    )
    reasoning_parity_ready = all(
        [
            _runtime_reasoning_card_surface_ready(runtime_html),
            int(review_reason_decision_ladder_summary.get("review_reason_total", 0) or 0) > 0,
            int(review_reason_decision_ladder_summary.get("review_reason_total", 0) or 0)
            == int(review_reason_decision_ladder_summary.get("prompt_bound_reason_total", 0) or 0),
        ]
    )
    closed_lane_ready = _closed_lane_surface_ready(
        brainstorm_summary=brainstorm_summary,
        closed_lane_stale_audit_summary=closed_lane_stale_audit_summary,
    )
    return [
        {
            "digest_id": "active_lane_surface_contract",
            "active_lane_id": active_execution_lane_id,
            "ready": prompt_contract_ready,
            "notes": "critical prompt lens must survive runtime, operator, and release surfaces",
        },
        {
            "digest_id": "operator_partner_demo_parity",
            "active_lane_id": active_execution_lane_id,
            "ready": demo_parity_ready,
            "notes": "operator, widget, and API demo surfaces must stay in parity",
        },
        {
            "digest_id": "runtime_reasoning_binding",
            "active_lane_id": active_execution_lane_id,
            "ready": reasoning_parity_ready,
            "notes": "runtime reasoning card must keep prompt-bound review reasons aligned",
        },
        {
            "digest_id": "closed_lane_staleness",
            "active_lane_id": active_execution_lane_id,
            "ready": closed_lane_ready,
            "notes": "closed lanes must not leak back into authoritative packet surfaces",
        },
    ]


def _surface_rows(
    *,
    brainstorm_summary: Dict[str, Any],
    operator_demo_summary: Dict[str, Any],
    review_reason_decision_ladder_summary: Dict[str, Any],
    critical_prompt_packet_summary: Dict[str, Any],
    widget_summary: Dict[str, Any],
    api_master_summary: Dict[str, Any],
    case_guard_summary: Dict[str, Any],
    preset_story_guard_summary: Dict[str, Any],
    runtime_html: str,
    prompt_doc_text: str,
    closed_lane_stale_audit_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    closed_lane_ready = _closed_lane_surface_ready(
        brainstorm_summary=brainstorm_summary,
        closed_lane_stale_audit_summary=closed_lane_stale_audit_summary,
    )
    rows = [
        {
            "surface_id": "operator_demo_packet",
            "label": "Operator demo packet",
            "ready": bool(operator_demo_summary.get("operator_demo_ready", False)),
            "coverage_total": int(operator_demo_summary.get("family_total", 0) or 0),
            "sample_total": int(operator_demo_summary.get("demo_case_total", 0) or 0),
            "notes": "compact operator walkthrough grouped by law family",
        },
        {
            "surface_id": "runtime_operator_demo",
            "label": "Runtime operator demo surface",
            "ready": _runtime_operator_demo_surface_ready(runtime_html),
            "coverage_total": int(operator_demo_summary.get("family_total", 0) or 0),
            "sample_total": int(operator_demo_summary.get("demo_case_total", 0) or 0),
            "notes": "result card exposes operator demo summary and packet link",
        },
        {
            "surface_id": "runtime_critical_prompt",
            "label": "Runtime critical prompt surface",
            "ready": _runtime_critical_prompt_surface_ready(runtime_html) and bool(prompt_doc_text.strip()),
            "coverage_total": 1 if prompt_doc_text.strip() else 0,
            "sample_total": 0,
            "notes": "operator result surface exposes first-principles prompt block",
        },
        {
            "surface_id": "critical_prompt_packet",
            "label": "Critical prompt packet",
            "ready": bool(critical_prompt_packet_summary.get("packet_ready", False))
            and bool(critical_prompt_packet_summary.get("compact_lens_ready", False)),
            "coverage_total": int(critical_prompt_packet_summary.get("founder_question_total", 0) or 0),
            "sample_total": 1 if critical_prompt_packet_summary.get("compact_lens_ready", False) else 0,
            "notes": "compact decision lens is canonicalized for runtime/release/operator reuse",
        },
        {
            "surface_id": "runtime_prompt_case_binding",
            "label": "Runtime prompt-case binding",
            "ready": _runtime_prompt_case_binding_surface_ready(runtime_html)
            and int(operator_demo_summary.get("prompt_case_binding_total", 0) or 0) > 0,
            "coverage_total": int(operator_demo_summary.get("prompt_case_binding_total", 0) or 0),
            "sample_total": 0,
            "notes": "operator result surface jumps from prompt lens to a representative preset",
        },
        {
            "surface_id": "runtime_reasoning_card",
            "label": "Runtime reasoning card",
            "ready": _runtime_reasoning_card_surface_ready(runtime_html)
            and int(review_reason_decision_ladder_summary.get("review_reason_total", 0) or 0) > 0,
            "coverage_total": int(review_reason_decision_ladder_summary.get("review_reason_total", 0) or 0),
            "sample_total": int(review_reason_decision_ladder_summary.get("prompt_bound_reason_total", 0) or 0),
            "notes": "runtime card binds reasoning ladder, inspect-first action, and preset jump",
        },
        {
            "surface_id": "widget_partner_demo",
            "label": "Widget partner demo surface",
            "ready": bool(widget_summary.get("permit_partner_demo_surface_ready", False)),
            "coverage_total": int(widget_summary.get("permit_operator_demo_family_total", 0) or 0),
            "sample_total": int(widget_summary.get("permit_partner_demo_sample_total", 0) or 0),
            "notes": "partner-safe demo summary for rental widgets",
        },
        {
            "surface_id": "api_partner_demo",
            "label": "API partner demo surface",
            "ready": bool(api_master_summary.get("partner_demo_surface_ready", False)),
            "coverage_total": int(api_master_summary.get("partner_demo_family_total", 0) or 0),
            "sample_total": int(api_master_summary.get("partner_demo_sample_total", 0) or 0),
            "notes": "partner-safe demo summary for API contract consumers",
        },
        {
            "surface_id": "case_release_guard",
            "label": "Case release guard",
            "ready": bool(case_guard_summary.get("release_guard_ready", False)),
            "coverage_total": int(case_guard_summary.get("family_total", 0) or 0),
            "sample_total": int(case_guard_summary.get("case_total", 0) or 0),
            "notes": "runtime/widget/api parity lock over family cases",
        },
        {
            "surface_id": "preset_story_guard",
            "label": "Preset/story guard",
            "ready": bool(preset_story_guard_summary.get("preset_story_guard_ready", False)),
            "coverage_total": 1 if preset_story_guard_summary else 0,
            "sample_total": 0,
            "notes": "preset and story parity lock across runtime and contracts",
        },
        {
            "surface_id": "closed_lane_stale_audit",
            "label": "Closed-lane stale audit",
            "ready": closed_lane_ready,
            "coverage_total": 1 if brainstorm_summary.get("closed_lane_id") else 0,
            "sample_total": int(
                brainstorm_summary.get(
                    "closed_lane_stale_reference_total",
                    closed_lane_stale_audit_summary.get("stale_reference_total", 0),
                )
                or 0
            ),
            "notes": "active lane is protected from stale closed-lane leakage",
        },
    ]
    return rows


def build_observability_report(
    *,
    brainstorm: Dict[str, Any],
    operator_demo_packet: Dict[str, Any],
    permit_review_reason_decision_ladder: Dict[str, Any],
    permit_critical_prompt_surface_packet: Dict[str, Any],
    widget_rental_catalog: Dict[str, Any],
    api_contract_spec: Dict[str, Any],
    permit_case_release_guard: Dict[str, Any],
    permit_preset_story_release_guard: Dict[str, Any],
    permit_closed_lane_stale_audit: Dict[str, Any],
    runtime_html: str,
    prompt_doc_text: str,
) -> Dict[str, Any]:
    brainstorm_summary = (
        brainstorm.get("summary")
        if isinstance(brainstorm.get("summary"), dict)
        else {}
    )
    operator_demo_summary = (
        operator_demo_packet.get("summary")
        if isinstance(operator_demo_packet.get("summary"), dict)
        else {}
    )
    review_reason_decision_ladder_summary = (
        permit_review_reason_decision_ladder.get("summary")
        if isinstance(permit_review_reason_decision_ladder.get("summary"), dict)
        else {}
    )
    critical_prompt_packet_summary = (
        permit_critical_prompt_surface_packet.get("summary")
        if isinstance(permit_critical_prompt_surface_packet.get("summary"), dict)
        else {}
    )
    widget_summary = (
        widget_rental_catalog.get("summary")
        if isinstance(widget_rental_catalog.get("summary"), dict)
        else {}
    )
    api_summary = _api_master_summary(api_contract_spec)
    case_guard_summary = (
        permit_case_release_guard.get("summary")
        if isinstance(permit_case_release_guard.get("summary"), dict)
        else {}
    )
    preset_story_guard_summary = (
        permit_preset_story_release_guard.get("summary")
        if isinstance(permit_preset_story_release_guard.get("summary"), dict)
        else {}
    )
    closed_lane_stale_audit_summary = (
        permit_closed_lane_stale_audit.get("summary")
        if isinstance(permit_closed_lane_stale_audit.get("summary"), dict)
        else {}
    )
    surfaces = _surface_rows(
        brainstorm_summary=brainstorm_summary,
        operator_demo_summary=operator_demo_summary,
        review_reason_decision_ladder_summary=review_reason_decision_ladder_summary,
        critical_prompt_packet_summary=critical_prompt_packet_summary,
        widget_summary=widget_summary,
        api_master_summary=api_summary,
        case_guard_summary=case_guard_summary,
        preset_story_guard_summary=preset_story_guard_summary,
        runtime_html=runtime_html,
        prompt_doc_text=prompt_doc_text,
        closed_lane_stale_audit_summary=closed_lane_stale_audit_summary,
    )
    active_execution_lane_id = str(brainstorm_summary.get("execution_lane", "") or "").strip()
    active_parallel_lane_id = str(brainstorm_summary.get("parallel_lane", "") or "").strip()
    surface_health_digest = _health_digest_rows(
        active_execution_lane_id=active_execution_lane_id,
        brainstorm_summary=brainstorm_summary,
        critical_prompt_packet_summary=critical_prompt_packet_summary,
        widget_summary=widget_summary,
        api_master_summary=api_summary,
        case_guard_summary=case_guard_summary,
        preset_story_guard_summary=preset_story_guard_summary,
        review_reason_decision_ladder_summary=review_reason_decision_ladder_summary,
        runtime_html=runtime_html,
        closed_lane_stale_audit_summary=closed_lane_stale_audit_summary,
    )
    missing_surfaces = [row["surface_id"] for row in surfaces if not bool(row.get("ready"))]
    summary = {
        "surface_total": len(surfaces),
        "ready_surface_total": sum(1 for row in surfaces if bool(row.get("ready"))),
        "missing_surface_total": len(missing_surfaces),
        "active_execution_lane_id": active_execution_lane_id,
        "active_parallel_lane_id": active_parallel_lane_id,
        "operator_demo_family_total": int(operator_demo_summary.get("family_total", 0) or 0),
        "operator_demo_case_total": int(operator_demo_summary.get("demo_case_total", 0) or 0),
        "prompt_case_binding_total": int(operator_demo_summary.get("prompt_case_binding_total", 0) or 0),
        "runtime_reasoning_review_reason_total": int(
            review_reason_decision_ladder_summary.get("review_reason_total", 0) or 0
        ),
        "runtime_reasoning_prompt_bound_total": int(
            review_reason_decision_ladder_summary.get("prompt_bound_reason_total", 0) or 0
        ),
        "runtime_reasoning_binding_gap_total": max(
            0,
            int(review_reason_decision_ladder_summary.get("review_reason_total", 0) or 0)
            - int(review_reason_decision_ladder_summary.get("prompt_bound_reason_total", 0) or 0),
        ),
        "runtime_operator_demo_surface_ready": _runtime_operator_demo_surface_ready(runtime_html),
        "runtime_critical_prompt_surface_ready": _runtime_critical_prompt_surface_ready(runtime_html)
        and bool(prompt_doc_text.strip()),
        "critical_prompt_packet_ready": bool(critical_prompt_packet_summary.get("packet_ready", False)),
        "critical_prompt_compact_lens_ready": bool(
            critical_prompt_packet_summary.get("compact_lens_ready", False)
        ),
        "critical_prompt_runtime_contract_ready": bool(
            critical_prompt_packet_summary.get("runtime_surface_contract_ready", False)
        ),
        "critical_prompt_release_contract_ready": bool(
            critical_prompt_packet_summary.get("release_surface_contract_ready", False)
        ),
        "critical_prompt_operator_contract_ready": bool(
            critical_prompt_packet_summary.get("operator_surface_contract_ready", False)
        ),
        "runtime_prompt_case_binding_surface_ready": _runtime_prompt_case_binding_surface_ready(runtime_html)
        and int(operator_demo_summary.get("prompt_case_binding_total", 0) or 0) > 0,
        "runtime_reasoning_card_surface_ready": _runtime_reasoning_card_surface_ready(runtime_html)
        and int(review_reason_decision_ladder_summary.get("review_reason_total", 0) or 0) > 0,
        "widget_partner_demo_surface_ready": bool(widget_summary.get("permit_partner_demo_surface_ready", False)),
        "api_partner_demo_surface_ready": bool(api_summary.get("partner_demo_surface_ready", False)),
        "partner_demo_surface_ready": bool(widget_summary.get("permit_partner_demo_surface_ready", False))
        and bool(api_summary.get("partner_demo_surface_ready", False)),
        "case_release_guard_ready": bool(case_guard_summary.get("release_guard_ready", False)),
        "preset_story_guard_ready": bool(preset_story_guard_summary.get("preset_story_guard_ready", False)),
        "critical_prompt_doc_ready": bool(prompt_doc_text.strip()),
        "closed_lane_stale_audit_ready": _closed_lane_surface_ready(
            brainstorm_summary=brainstorm_summary,
            closed_lane_stale_audit_summary=closed_lane_stale_audit_summary,
        ),
        "closed_lane_stale_reference_total": int(
            brainstorm_summary.get(
                "closed_lane_stale_reference_total",
                closed_lane_stale_audit_summary.get("stale_reference_total", 0),
            )
            or 0
        ),
        "surface_health_digest_total": len(surface_health_digest),
        "surface_health_digest_ready": all(bool(row.get("ready")) for row in surface_health_digest),
        "observability_ready": (not missing_surfaces)
        and all(bool(row.get("ready")) for row in surface_health_digest),
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "missing_surfaces": missing_surfaces,
        "surfaces": surfaces,
        "surface_health_digest": surface_health_digest,
        "source_paths": {
            "brainstorm": str(DEFAULT_BRAINSTORM_INPUT.resolve()),
            "operator_demo_packet": str(DEFAULT_OPERATOR_DEMO_PACKET_INPUT.resolve()),
            "permit_review_reason_decision_ladder": str(DEFAULT_REVIEW_REASON_DECISION_LADDER_INPUT.resolve()),
            "permit_critical_prompt_surface_packet": str(DEFAULT_CRITICAL_PROMPT_SURFACE_PACKET_INPUT.resolve()),
            "widget_rental_catalog": str(DEFAULT_WIDGET_INPUT.resolve()),
            "api_contract_spec": str(DEFAULT_API_CONTRACT_INPUT.resolve()),
            "permit_case_release_guard": str(DEFAULT_CASE_RELEASE_GUARD_INPUT.resolve()),
            "permit_preset_story_release_guard": str(DEFAULT_PRESET_STORY_GUARD_INPUT.resolve()),
            "permit_closed_lane_stale_audit": str(DEFAULT_CLOSED_LANE_STALE_AUDIT_INPUT.resolve()),
            "runtime_html": str(DEFAULT_RUNTIME_HTML_INPUT.resolve()),
            "critical_prompt_doc": str(DEFAULT_PROMPT_DOC_INPUT.resolve()),
        },
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    lines = [
        "# Permit Demo Surface Observability",
        "",
        "## Summary",
        f"- surface_total: `{summary.get('surface_total', 0)}`",
        f"- ready_surface_total: `{summary.get('ready_surface_total', 0)}`",
        f"- missing_surface_total: `{summary.get('missing_surface_total', 0)}`",
        f"- active_execution_lane_id: `{summary.get('active_execution_lane_id', '')}`",
        f"- active_parallel_lane_id: `{summary.get('active_parallel_lane_id', '')}`",
        f"- operator_demo_family_total: `{summary.get('operator_demo_family_total', 0)}`",
        f"- operator_demo_case_total: `{summary.get('operator_demo_case_total', 0)}`",
        f"- prompt_case_binding_total: `{summary.get('prompt_case_binding_total', 0)}`",
        f"- runtime_reasoning_review_reason_total: `{summary.get('runtime_reasoning_review_reason_total', 0)}`",
        f"- runtime_reasoning_prompt_bound_total: `{summary.get('runtime_reasoning_prompt_bound_total', 0)}`",
        f"- runtime_reasoning_binding_gap_total: `{summary.get('runtime_reasoning_binding_gap_total', 0)}`",
        f"- runtime_operator_demo_surface_ready: `{summary.get('runtime_operator_demo_surface_ready', False)}`",
        f"- runtime_critical_prompt_surface_ready: `{summary.get('runtime_critical_prompt_surface_ready', False)}`",
        f"- critical_prompt_packet_ready: `{summary.get('critical_prompt_packet_ready', False)}`",
        f"- critical_prompt_compact_lens_ready: `{summary.get('critical_prompt_compact_lens_ready', False)}`",
        f"- critical_prompt_runtime_contract_ready: `{summary.get('critical_prompt_runtime_contract_ready', False)}`",
        f"- critical_prompt_release_contract_ready: `{summary.get('critical_prompt_release_contract_ready', False)}`",
        f"- critical_prompt_operator_contract_ready: `{summary.get('critical_prompt_operator_contract_ready', False)}`",
        f"- runtime_prompt_case_binding_surface_ready: `{summary.get('runtime_prompt_case_binding_surface_ready', False)}`",
        f"- runtime_reasoning_card_surface_ready: `{summary.get('runtime_reasoning_card_surface_ready', False)}`",
        f"- widget_partner_demo_surface_ready: `{summary.get('widget_partner_demo_surface_ready', False)}`",
        f"- api_partner_demo_surface_ready: `{summary.get('api_partner_demo_surface_ready', False)}`",
        f"- partner_demo_surface_ready: `{summary.get('partner_demo_surface_ready', False)}`",
        f"- case_release_guard_ready: `{summary.get('case_release_guard_ready', False)}`",
        f"- preset_story_guard_ready: `{summary.get('preset_story_guard_ready', False)}`",
        f"- critical_prompt_doc_ready: `{summary.get('critical_prompt_doc_ready', False)}`",
        f"- closed_lane_stale_audit_ready: `{summary.get('closed_lane_stale_audit_ready', False)}`",
        f"- closed_lane_stale_reference_total: `{summary.get('closed_lane_stale_reference_total', 0)}`",
        f"- surface_health_digest_total: `{summary.get('surface_health_digest_total', 0)}`",
        f"- surface_health_digest_ready: `{summary.get('surface_health_digest_ready', False)}`",
        f"- observability_ready: `{summary.get('observability_ready', False)}`",
        "",
        "## Surface Matrix",
    ]
    for surface in [row for row in list(report.get("surfaces") or []) if isinstance(row, dict)]:
        lines.append(
            f"- `{surface.get('surface_id', '')}` ready={surface.get('ready', False)} "
            f"/ coverage={surface.get('coverage_total', 0)} / samples={surface.get('sample_total', 0)} "
            f"/ {surface.get('notes', '')}"
        )
    missing = [str(item) for item in list(report.get("missing_surfaces") or []) if str(item).strip()]
    if missing:
        lines.extend(["", "## Missing Surfaces", *[f"- `{item}`" for item in missing]])
    digest_rows = [row for row in list(report.get("surface_health_digest") or []) if isinstance(row, dict)]
    if digest_rows:
        lines.extend(["", "## Surface Health Digest"])
        for row in digest_rows:
            lines.append(
                f"- `{row.get('digest_id', '')}` ready={row.get('ready', False)} / lane={row.get('active_lane_id', '')} / {row.get('notes', '')}"
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a compact observability report for permit demo surfaces.")
    parser.add_argument("--brainstorm-input", type=Path, default=DEFAULT_BRAINSTORM_INPUT)
    parser.add_argument("--operator-demo-packet", type=Path, default=DEFAULT_OPERATOR_DEMO_PACKET_INPUT)
    parser.add_argument(
        "--review-reason-decision-ladder",
        type=Path,
        default=DEFAULT_REVIEW_REASON_DECISION_LADDER_INPUT,
    )
    parser.add_argument("--critical-prompt-surface-packet-input", type=Path, default=DEFAULT_CRITICAL_PROMPT_SURFACE_PACKET_INPUT)
    parser.add_argument("--widget-input", type=Path, default=DEFAULT_WIDGET_INPUT)
    parser.add_argument("--api-contract-input", type=Path, default=DEFAULT_API_CONTRACT_INPUT)
    parser.add_argument("--case-release-guard-input", type=Path, default=DEFAULT_CASE_RELEASE_GUARD_INPUT)
    parser.add_argument("--preset-story-guard-input", type=Path, default=DEFAULT_PRESET_STORY_GUARD_INPUT)
    parser.add_argument("--closed-lane-stale-audit-input", type=Path, default=DEFAULT_CLOSED_LANE_STALE_AUDIT_INPUT)
    parser.add_argument("--runtime-html", type=Path, default=DEFAULT_RUNTIME_HTML_INPUT)
    parser.add_argument("--prompt-doc", type=Path, default=DEFAULT_PROMPT_DOC_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    report = build_observability_report(
        brainstorm=_load_json(args.brainstorm_input.resolve()),
        operator_demo_packet=_load_json(args.operator_demo_packet.resolve()),
        permit_review_reason_decision_ladder=_load_json(args.review_reason_decision_ladder.resolve()),
        permit_critical_prompt_surface_packet=_load_json(args.critical_prompt_surface_packet_input.resolve()),
        widget_rental_catalog=_load_json(args.widget_input.resolve()),
        api_contract_spec=_load_json(args.api_contract_input.resolve()),
        permit_case_release_guard=_load_json(args.case_release_guard_input.resolve()),
        permit_preset_story_release_guard=_load_json(args.preset_story_guard_input.resolve()),
        permit_closed_lane_stale_audit=_load_json(args.closed_lane_stale_audit_input.resolve()),
        runtime_html=_load_text(args.runtime_html.resolve()),
        prompt_doc_text=_load_text(args.prompt_doc.resolve()),
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
