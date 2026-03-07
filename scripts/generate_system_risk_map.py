#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]

ISSUE_RE = __import__("re").compile(r"^(FAIL|ERROR):\s+([^\s]+)\s+\(([^)]+)\)$", __import__("re").MULTILINE)
RAN_RE = __import__("re").compile(r"^Ran\s+(\d+)\s+tests\s+in\s+([0-9.]+)s$", __import__("re").MULTILINE)
FAILED_RE = __import__("re").compile(r"^FAILED\s+\(([^)]+)\)$", __import__("re").MULTILINE)

GROUPS = {
    "core_calculator_platform": {
        "priority": "release_blocking",
        "business_impact": "high",
        "tokens": [
            "acquisition_",
            "permit_",
            "yangdo_",
            "widget",
            "tenant_",
            "activate_partner",
            "channel_profiles",
            "api_response_contract",
            "deploy_seoul_widget_embed_release",
            "deploy_co_content_pages",
            "publish_widget_bundle",
            "validate_live_release_ready",
            "verify_calculator_runtime",
            "run_partner_onboarding_flow",
            "scaffold_partner_offering",
            "generate_attorney_handoff",
            "generate_patent_system_brief",
        ],
    },
    "listing_support_pipeline": {
        "priority": "supporting",
        "business_impact": "medium",
        "tokens": [
            "test_all_",
            "listing_",
            "lead_intake",
            "gabji",
            "quote_engine",
            "sales_pipeline",
            "consult",
        ],
    },
    "legacy_blog_tistory": {
        "priority": "non_blocking_legacy",
        "business_impact": "low",
        "tokens": [
            "tistory",
            "mnakr",
            "premium_auto",
            "internal_linker",
            "kb_fact_validation",
            "encoding_guard",
        ],
    },
    "legacy_content_reporting": {
        "priority": "non_blocking_legacy",
        "business_impact": "low",
        "tokens": [
            "monthly_market_report",
            "monthly_notice",
            "notice_keyword_report",
            "review_monthly_",
            "publish_monthly_",
            "build_monthly_",
        ],
    },
    "ops_hygiene": {
        "priority": "operational_hygiene",
        "business_impact": "low",
        "tokens": [
            "quality_ops",
            "quality_gate_runner",
            "run_paid_cli",
            "verify_paid_legacy_split",
            "show_entrypoints",
        ],
    },
}


def _run_discover(timeout_sec: int = 180) -> Dict[str, Any]:
    py_cmd = ["py", "-3"] if shutil.which("py") else [sys.executable]
    cmd = [*py_cmd, "-m", "unittest", "discover", "tests"]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
        check=False,
    )
    combined = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    return {
        "command": cmd,
        "returncode": int(proc.returncode),
        "output": combined,
    }


def _extract_counter(expr: str, name: str) -> int:
    if not expr:
        return 0
    import re

    match = re.search(rf"{name}=(\d+)", expr)
    return int(match.group(1)) if match else 0


def _classify_module(module_name: str) -> str:
    src = str(module_name or "").strip().lower()
    for group, meta in GROUPS.items():
        for token in meta["tokens"]:
            if token in src:
                return group
    return "unclassified"


def parse_discover_output(output: str, returncode: int) -> Dict[str, Any]:
    issues: List[Dict[str, Any]] = []
    for match in ISSUE_RE.finditer(str(output or "")):
        status = str(match.group(1) or "").strip().lower()
        test_name = str(match.group(2) or "").strip()
        module_qual = str(match.group(3) or "").strip()
        module_name = module_qual.split(".", 1)[0] if "." in module_qual else module_qual
        group = _classify_module(module_name)
        group_meta = GROUPS.get(group, {})
        issues.append(
            {
                "status": status,
                "test_name": test_name,
                "module_name": module_name,
                "module_qualname": module_qual,
                "group": group,
                "priority": group_meta.get("priority", "unknown"),
                "business_impact": group_meta.get("business_impact", "unknown"),
            }
        )

    ran_match = RAN_RE.search(str(output or ""))
    failed_match = FAILED_RE.search(str(output or ""))
    counters_expr = str(failed_match.group(1) or "") if failed_match else ""

    group_summary: Dict[str, Dict[str, Any]] = {}
    for issue in issues:
        key = str(issue["group"])
        bucket = group_summary.setdefault(
            key,
            {
                "issue_count": 0,
                "modules": [],
                "priority": issue.get("priority"),
                "business_impact": issue.get("business_impact"),
            },
        )
        bucket["issue_count"] += 1
        module_name = str(issue["module_name"])
        if module_name not in bucket["modules"]:
            bucket["modules"].append(module_name)

    core_issue_count = int(group_summary.get("core_calculator_platform", {}).get("issue_count", 0) or 0)
    return {
        "ok": int(returncode) == 0,
        "run_summary": {
            "returncode": int(returncode),
            "ran_tests": int(ran_match.group(1)) if ran_match else 0,
            "duration_sec": float(ran_match.group(2)) if ran_match else 0.0,
            "failures": _extract_counter(counters_expr, "failures"),
            "errors": _extract_counter(counters_expr, "errors"),
            "issue_count": len(issues),
        },
        "business_core_status": "green" if core_issue_count == 0 else "red",
        "issues": issues,
        "group_summary": group_summary,
    }


def _to_markdown(data: Dict[str, Any], raw_output_path: str) -> str:
    lines: List[str] = []
    summary = data.get("run_summary") if isinstance(data.get("run_summary"), dict) else {}
    lines.append("# System Risk Map")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- business_core_status: {data.get('business_core_status')}")
    lines.append(f"- returncode: {summary.get('returncode', 0)}")
    lines.append(f"- ran_tests: {summary.get('ran_tests', 0)}")
    lines.append(f"- failures: {summary.get('failures', 0)}")
    lines.append(f"- errors: {summary.get('errors', 0)}")
    lines.append(f"- issue_count: {summary.get('issue_count', 0)}")
    lines.append(f"- raw_output: {raw_output_path}")
    lines.append("")
    lines.append("## Group Summary")
    for key, meta in sorted((data.get("group_summary") or {}).items()):
        lines.append(
            f"- {key}: issue_count={meta.get('issue_count', 0)} "
            f"priority={meta.get('priority', '')} impact={meta.get('business_impact', '')} "
            f"modules={', '.join(meta.get('modules', []))}"
        )
    lines.append("")
    lines.append("## Issues")
    for issue in data.get("issues", []):
        lines.append(
            f"- {issue.get('status')} {issue.get('module_name')}::{issue.get('test_name')} "
            f"[group={issue.get('group')} priority={issue.get('priority')}]"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate objective core-vs-legacy risk map from unittest discover output")
    parser.add_argument("--json", default="logs/system_risk_map_latest.json")
    parser.add_argument("--md", default="logs/system_risk_map_latest.md")
    parser.add_argument("--raw", default="logs/system_risk_map_latest.txt")
    parser.add_argument("--input-file", default="", help="Parse an existing unittest output file instead of executing discover")
    parser.add_argument("--timeout-sec", type=int, default=180)
    args = parser.parse_args()

    if str(args.input_file or "").strip():
        raw_path = Path(str(args.input_file)).resolve()
        output = raw_path.read_text(encoding="utf-8", errors="replace")
        run_payload = {"command": [], "returncode": 1, "output": output}
    else:
        run_payload = _run_discover(timeout_sec=int(args.timeout_sec))
        raw_path = (ROOT / str(args.raw)).resolve()
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(str(run_payload.get("output") or ""), encoding="utf-8")

    parsed = parse_discover_output(str(run_payload.get("output") or ""), int(run_payload.get("returncode", 1)))
    parsed.update(
        {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "workspace": str(ROOT),
            "command": list(run_payload.get("command") or []),
            "raw_output_path": str(raw_path),
        }
    )

    json_path = (ROOT / str(args.json)).resolve()
    md_path = (ROOT / str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(parsed, str(raw_path)), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "json": str(json_path),
                "md": str(md_path),
                "raw": str(raw_path),
                "business_core_status": parsed.get("business_core_status"),
                "issue_count": (parsed.get("run_summary") or {}).get("issue_count", 0),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
