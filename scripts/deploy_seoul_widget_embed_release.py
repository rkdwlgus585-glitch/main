#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _py_cmd(args: List[str]) -> List[str]:
    if shutil.which("py"):
        return ["py", "-3", *args]
    return [sys.executable, *args]


def _run(cmd: List[str], timeout_sec: int = 420) -> Dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        encoding="utf-8",
        errors="replace",
    )
    stdout_text = proc.stdout or ""
    stderr_text = proc.stderr or ""
    parsed = None
    if stdout_text.strip():
        try:
            parsed = json.loads(stdout_text)
        except Exception:
            parsed = None
    return {
        "ok": proc.returncode == 0,
        "returncode": int(proc.returncode),
        "command": cmd,
        "stdout_tail": "\n".join(stdout_text.splitlines()[-80:]),
        "stderr_tail": "\n".join(stderr_text.splitlines()[-80:]),
        "json": parsed,
    }


def build_release_plan(
    *,
    channel_id: str,
    confirm_live: str,
    bundle_manifest: str,
    runtime_report: str,
    content_report: str,
    preflight_report: str,
) -> List[Dict[str, Any]]:
    confirm = str(confirm_live or "").strip().upper()
    return [
        {
            "name": "validate_live_release_ready",
            "command": _py_cmd(
                [
                    "scripts/validate_live_release_ready.py",
                    "--channel-id",
                    str(channel_id),
                    "--report",
                    str(preflight_report),
                ]
            ),
            "requires_confirm": False,
        },
        {
            "name": "validate_tenant_onboarding",
            "command": _py_cmd(["scripts/validate_tenant_onboarding.py", "--strict"]),
            "requires_confirm": False,
        },
        {
            "name": "publish_widget_bundle",
            "command": _py_cmd(["scripts/publish_widget_bundle.py", "--channel-id", str(channel_id)]),
            "requires_confirm": False,
        },
        {
            "name": "deploy_co_content_pages",
            "command": _py_cmd(
                [
                    "scripts/deploy_co_content_pages.py",
                    "--bundle-manifest",
                    str(bundle_manifest),
                    "--confirm-live",
                    confirm,
                    "--report",
                    str(content_report),
                ]
            ),
            "requires_confirm": True,
        },
        {
            "name": "verify_calculator_runtime",
            "command": _py_cmd(["scripts/verify_calculator_runtime.py", "--report", str(runtime_report)]),
            "requires_confirm": False,
        },
    ]


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _create_bundle_backup(*, bundle_manifest_path: Path, channel_id: str) -> Dict[str, Any]:
    bundle_dir = bundle_manifest_path.parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = ROOT / "output" / "widget" / "release_backups" / str(channel_id or "channel").strip().lower()
    backup_dir = backup_root / timestamp
    if not bundle_dir.exists():
        return {
            "created": False,
            "bundle_dir_exists": False,
            "backup_dir": str(backup_dir.resolve()),
            "backup_manifest": str((backup_dir / "manifest.json").resolve()),
        }
    backup_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle_dir, backup_dir, dirs_exist_ok=True)
    return {
        "created": True,
        "bundle_dir_exists": True,
        "backup_dir": str(backup_dir.resolve()),
        "backup_manifest": str((backup_dir / "manifest.json").resolve()),
    }


def _artifact_summary(*, artifact_paths: Dict[str, str], report: Dict[str, Any]) -> Dict[str, Any]:
    preflight_path = Path(str(artifact_paths.get("preflight_report") or "")).resolve()
    content_path = Path(str(artifact_paths.get("content_report") or "")).resolve()
    runtime_path = Path(str(artifact_paths.get("runtime_report") or "")).resolve()
    bundle_path = Path(str(artifact_paths.get("bundle_manifest") or "")).resolve()
    checklist_path = Path(str(artifact_paths.get("kr_live_operator_checklist") or "")).resolve()

    preflight = _load_json_if_exists(preflight_path)
    content = _load_json_if_exists(content_path)
    runtime = _load_json_if_exists(runtime_path)
    bundle = _load_json_if_exists(bundle_path)
    checklist = _load_json_if_exists(checklist_path)

    widgets = bundle.get("widgets") if isinstance(bundle.get("widgets"), list) else []
    bundle_ok_widgets = [
        str(item.get("widget") or "").strip()
        for item in widgets
        if isinstance(item, dict) and bool(item.get("ok")) and str(item.get("widget") or "").strip()
    ]
    content_results = content.get("results") if isinstance(content.get("results"), list) else []
    content_ok_ids = [
        str(item.get("co_id") or "").strip()
        for item in content_results
        if isinstance(item, dict)
        and bool(item.get("subject_ok"))
        and bool(item.get("content_ok"))
        and str(item.get("co_id") or "").strip()
    ]
    content_failed_ids = [
        str(item.get("co_id") or "").strip()
        for item in content_results
        if isinstance(item, dict)
        and not (bool(item.get("subject_ok")) and bool(item.get("content_ok")))
        and str(item.get("co_id") or "").strip()
    ]
    runtime_checks = runtime.get("checks") if isinstance(runtime.get("checks"), list) else []
    runtime_failed = [
        {
            "kind": str(item.get("kind") or "").strip(),
            "url": str(item.get("url") or "").strip(),
        }
        for item in runtime_checks
        if isinstance(item, dict) and not bool(item.get("ok"))
    ]
    preflight_handoff = preflight.get("handoff") if isinstance(preflight.get("handoff"), dict) else {}
    handoff = report.get("handoff") if isinstance(report.get("handoff"), dict) else {}

    return {
        "preflight": {
            "ok": bool(preflight.get("ok")),
            "release_ready": bool(preflight_handoff.get("release_ready")),
            "next_actions": [str(x) for x in (preflight_handoff.get("next_actions") or []) if str(x).strip()],
            "blocking_issues": [str(x) for x in (preflight.get("blocking_issues") or []) if str(x).strip()],
        },
        "bundle": {
            "exists": bundle_path.exists(),
            "ok_widget_count": len(bundle_ok_widgets),
            "ok_widgets": bundle_ok_widgets,
        },
        "content": {
            "ok": bool(content.get("ok")),
            "page_count": len(content_results),
            "ok_ids": content_ok_ids,
            "failed_ids": content_failed_ids,
        },
        "runtime": {
            "ok": bool(runtime.get("ok")),
            "check_count": len(runtime_checks),
            "warning_count": len(runtime.get("warnings") or []),
            "failed_checks": runtime_failed,
            "blocking_issues": [str(x) for x in (runtime.get("blocking_issues") or []) if str(x).strip()],
        },
        "operator_checklist": {
            "exists": checklist_path.exists(),
            "checklist_ready": bool(((checklist.get("summary") or {}) if isinstance(checklist.get("summary"), dict) else {}).get("checklist_ready")),
            "operator_input_count": int((((checklist.get("summary") or {}) if isinstance(checklist.get("summary"), dict) else {}).get("operator_input_count")) or 0),
            "blockers": [str(x) for x in (((checklist.get("summary") or {}) if isinstance(checklist.get("summary"), dict) else {}).get("blockers") or []) if str(x).strip()],
        },
        "release": {
            "ok": bool(report.get("ok")),
            "blocking_issues": [str(x) for x in (report.get("blocking_issues") or []) if str(x).strip()],
            "runtime_verified": bool(handoff.get("runtime_verified")),
        },
    }


def _extract_release_handoff(report: Dict[str, Any]) -> Dict[str, Any]:
    preflight = report.get("preflight") if isinstance(report.get("preflight"), dict) else {}
    runtime = report.get("runtime_verify") if isinstance(report.get("runtime_verify"), dict) else {}
    checklist = report.get("kr_live_operator_checklist") if isinstance(report.get("kr_live_operator_checklist"), dict) else {}
    blockers = [str(x) for x in (report.get("blocking_issues") or []) if str(x).strip()]
    next_actions = []
    if isinstance(preflight, dict):
        next_actions.extend([str(x) for x in (((preflight.get("handoff") or {}) if isinstance(preflight.get("handoff"), dict) else {}).get("next_actions") or []) if str(x).strip()])
    if isinstance(checklist, dict):
        next_actions.extend([str(x) for x in (checklist.get("next_actions") or []) if str(x).strip()])
    if blockers and not next_actions:
        next_actions.append("blocking_issues 해소 후 release 재실행")
    if not blockers and not next_actions:
        next_actions.append("서울건설정보 release 완료 상태 검토")
    return {
        "release_ready": bool(((preflight.get("handoff") or {}) if isinstance(preflight, dict) else {}).get("release_ready")) if preflight else False,
        "runtime_verified": bool(runtime.get("ok")) if isinstance(runtime, dict) else False,
        "operator_checklist_ready": bool(((checklist.get("summary") or {}) if isinstance(checklist.get("summary"), dict) else {}).get("checklist_ready")),
        "blocking_issues": blockers,
        "next_actions": list(dict.fromkeys(next_actions)),
    }


def _build_rollback_summary(*, report: Dict[str, Any], bundle_backup: Dict[str, Any]) -> Dict[str, Any]:
    steps = report.get("steps") if isinstance(report.get("steps"), list) else []
    executed_names = [str(item.get("name") or "").strip() for item in steps if isinstance(item, dict)]
    content_step = next((item for item in steps if isinstance(item, dict) and str(item.get("name") or "").strip() == "deploy_co_content_pages"), {})
    runtime_step = next((item for item in steps if isinstance(item, dict) and str(item.get("name") or "").strip() == "verify_calculator_runtime"), {})
    content_attempted = bool(content_step)
    content_ok = bool(content_step.get("ok")) if isinstance(content_step, dict) else False
    runtime_attempted = bool(runtime_step)
    runtime_ok = bool(runtime_step.get("ok")) if isinstance(runtime_step, dict) else False
    backup_manifest = str(bundle_backup.get("backup_manifest") or "").strip()
    backup_available = bool(bundle_backup.get("created")) and bool(backup_manifest) and Path(backup_manifest).exists()

    rollback_required = False
    rollback_reason = "not_started"
    recommended_actions: List[str] = []
    rollback_command = ""

    if not executed_names:
        rollback_reason = "release_not_started"
    elif not content_attempted:
        rollback_reason = "no_live_content_change"
    elif content_ok and runtime_attempted and not runtime_ok:
        rollback_required = True
        rollback_reason = "runtime_verification_failed_after_live_publish"
    elif not content_ok:
        rollback_reason = "content_publish_failed_before_live_completion"
    else:
        rollback_reason = "live_release_succeeded"

    if rollback_required:
        if backup_available:
            rollback_command = (
                f"py -3 scripts/deploy_co_content_pages.py --bundle-manifest \"{backup_manifest}\" --confirm-live YES"
            )
            recommended_actions.append("Redeploy co.kr content with the previous bundle manifest")
            recommended_actions.append(rollback_command)
        else:
            recommended_actions.append("No automatic rollback backup available; redeploy the last known good content manually")
    elif rollback_reason == "no_live_content_change":
        recommended_actions.append("Stopped before any public content change; rollback not required")
    elif rollback_reason == "release_not_started":
        recommended_actions.append("Live release not started; rollback not required")
    elif rollback_reason == "live_release_succeeded" and backup_available:
        recommended_actions.append("If needed, redeploy the previous state with the backup manifest")

    return {
        "rollback_required": rollback_required,
        "rollback_reason": rollback_reason,
        "content_attempted": content_attempted,
        "content_ok": content_ok,
        "runtime_attempted": runtime_attempted,
        "runtime_ok": runtime_ok,
        "backup_available": backup_available,
        "backup_dir": str(bundle_backup.get("backup_dir") or ""),
        "backup_manifest": backup_manifest,
        "recommended_actions": recommended_actions,
        "rollback_command": rollback_command,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Release SeoulMNA widget bundle -> co content pages -> runtime verify")
    parser.add_argument("--channel-id", default="seoul_widget_internal")
    parser.add_argument("--confirm-live", default="", help="실서비스 반영 승인 토큰 (`--confirm-live YES`)")
    parser.add_argument("--bundle-manifest", default="output/widget/bundles/seoul_widget_internal/manifest.json")
    parser.add_argument("--content-report", default="logs/co_content_pages_deploy_latest.json")
    parser.add_argument("--runtime-report", default="logs/verify_calculator_runtime_latest.json")
    parser.add_argument("--preflight-report", default="logs/live_release_readiness_latest.json")
    parser.add_argument("--kr-live-operator-checklist", default="logs/kr_live_operator_checklist_latest.json")
    parser.add_argument("--report", default="logs/seoul_widget_embed_release_latest.json")
    args = parser.parse_args()

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": False,
        "channel_id": str(args.channel_id or "").strip().lower(),
        "steps": [],
        "blocking_issues": [],
        "artifacts": {
            "preflight_report": str((ROOT / str(args.preflight_report)).resolve()),
            "content_report": str((ROOT / str(args.content_report)).resolve()),
            "runtime_report": str((ROOT / str(args.runtime_report)).resolve()),
            "bundle_manifest": str((ROOT / str(args.bundle_manifest)).resolve()),
            "kr_live_operator_checklist": str((ROOT / str(args.kr_live_operator_checklist)).resolve()),
        },
    }
    confirm = str(args.confirm_live or "").strip().upper()
    if confirm != "YES":
        report["blocking_issues"].append("confirm_live_missing")
        report["error"] = "release blocked: add --confirm-live YES"
        report["rollback"] = _build_rollback_summary(report=report, bundle_backup={})
        report["artifact_summary"] = _artifact_summary(artifact_paths=report["artifacts"], report=report)
        _save_json((ROOT / str(args.report)).resolve(), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    checklist_path = (ROOT / str(args.kr_live_operator_checklist)).resolve()
    checklist_payload = _load_json_if_exists(checklist_path)
    report["kr_live_operator_checklist"] = checklist_payload
    checklist_summary = checklist_payload.get("summary") if isinstance(checklist_payload.get("summary"), dict) else {}
    if not bool(checklist_summary.get("checklist_ready")):
        report["blocking_issues"].append("kr_live_operator_checklist_not_ready")
        report["error"] = "release blocked: operator checklist is not ready"
        report["handoff"] = _extract_release_handoff(report)
        report["rollback"] = _build_rollback_summary(report=report, bundle_backup={})
        report["artifact_summary"] = _artifact_summary(artifact_paths=report["artifacts"], report=report)
        _save_json((ROOT / str(args.report)).resolve(), report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2

    report["bundle_backup"] = _create_bundle_backup(
        bundle_manifest_path=(ROOT / str(args.bundle_manifest)).resolve(),
        channel_id=str(args.channel_id or "").strip().lower(),
    )

    plan = build_release_plan(
        channel_id=str(args.channel_id or "").strip().lower(),
        confirm_live=confirm,
        bundle_manifest=str(args.bundle_manifest),
        runtime_report=str(args.runtime_report),
        content_report=str(args.content_report),
        preflight_report=str(args.preflight_report),
    )
    for step in plan:
        result = _run(step["command"])
        report["steps"].append({"name": step["name"], **result})
        payload = result.get("json") if isinstance(result.get("json"), dict) else {}
        if step["name"] == "validate_live_release_ready":
            report["preflight"] = payload
        elif step["name"] == "verify_calculator_runtime":
            report["runtime_verify"] = payload
        elif step["name"] == "deploy_co_content_pages":
            report["content_deploy"] = payload
        if not result["ok"]:
            report["blocking_issues"].append(f"step_failed:{step['name']}")
            report["ok"] = False
            break
    else:
        report["ok"] = True

    report["handoff"] = _extract_release_handoff(report)
    report["rollback"] = _build_rollback_summary(
        report=report,
        bundle_backup=report.get("bundle_backup") if isinstance(report.get("bundle_backup"), dict) else {},
    )
    report["artifact_summary"] = _artifact_summary(artifact_paths=report["artifacts"], report=report)

    out_path = (ROOT / str(args.report)).resolve()
    _save_json(out_path, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
