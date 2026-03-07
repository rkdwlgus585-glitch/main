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
    return build_manifest(python_executable=python_executable, step_results=results)


def build_manifest(*, python_executable: str, step_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    failed = [row for row in step_results if not bool(row.get("ok"))]
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
        },
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
