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
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRONT_APP = ROOT / "workspace_partitions" / "site_session" / "kr_platform_front"
DEFAULT_FRONT_ENV = DEFAULT_FRONT_APP / ".env.local"
DEFAULT_FRONT_AUDIT = ROOT / "logs" / "platform_front_audit_latest.json"
DEFAULT_TRAFFIC_AUDIT = ROOT / "logs" / "kr_traffic_gate_audit_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _run(
    cmd: List[str],
    *,
    cwd: Path,
    timeout_sec: int = 120,
) -> Dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    return {
        "ok": proc.returncode == 0,
        "returncode": int(proc.returncode),
        "command": cmd,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }


def resolve_vercel_runner() -> Tuple[List[str], str]:
    vercel_path = shutil.which("vercel")
    if vercel_path:
        return ([vercel_path], "vercel")
    npx_cmd = shutil.which("npx.cmd") or shutil.which("npx")
    if npx_cmd:
        return ([npx_cmd, "--yes", "vercel"], "npx")
    return ([], "")


def inspect_vercel_cli(*, cwd: Path, check_auth: bool = True) -> Dict[str, Any]:
    runner, mode = resolve_vercel_runner()
    if not runner:
        return {
            "available": False,
            "mode": "",
            "version": "",
            "auth_ok": False,
            "identity": "",
            "errors": ["vercel_cli_missing"],
        }

    version_result = _run([*runner, "--version"], cwd=cwd)
    version_text = (version_result.get("stdout") or version_result.get("stderr") or "").strip().splitlines()
    version = version_text[-1].strip() if version_text else ""
    errors: List[str] = []
    if not version_result["ok"]:
        errors.append("vercel_cli_version_check_failed")

    auth_ok = False
    identity = ""
    auth_error = ""
    if check_auth:
        auth_result = _run([*runner, "whoami"], cwd=cwd)
        auth_output = ((auth_result.get("stdout") or "") + "\n" + (auth_result.get("stderr") or "")).strip()
        if auth_result["ok"] and auth_output:
            auth_ok = True
            identity = auth_output.splitlines()[-1].strip()
        else:
            auth_error = auth_output or "vercel_auth_missing"
            errors.append("vercel_auth_missing")
    return {
        "available": True,
        "mode": mode,
        "version": version,
        "auth_ok": auth_ok if check_auth else True,
        "identity": identity,
        "auth_error": auth_error,
        "errors": errors,
    }


def _load_env_keys(path: Path) -> List[str]:
    if not path.exists():
        return []
    keys: List[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        text = str(line or "").strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key = text.split("=", 1)[0].lstrip("\ufeff").strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def _normalize_action(text: str) -> str:
    value = str(text or "").strip()
    if not value:
        return ""
    if "vercel_auth_missing" in value:
        return "Authenticate Vercel CLI for the kr platform front"
    if "vercel_cli_missing" in value:
        return "Install or expose the Vercel CLI runner"
    return value


def build_kr_platform_deploy_ready_report(
    *,
    front_app_path: Path,
    front_env_path: Path,
    front_audit_path: Path,
    traffic_audit_path: Path,
    check_auth: bool = True,
) -> Dict[str, Any]:
    front_audit = _load_json(front_audit_path)
    traffic_audit = _load_json(traffic_audit_path)
    audit_front = front_audit.get("front") if isinstance(front_audit.get("front"), dict) else {}
    audit_summary = (
        front_audit.get("completion_summary")
        if isinstance(front_audit.get("completion_summary"), dict)
        else {}
    )
    traffic_decision = traffic_audit.get("decision") if isinstance(traffic_audit.get("decision"), dict) else {}
    traffic_probe = traffic_audit.get("live_probe") if isinstance(traffic_audit.get("live_probe"), dict) else {}
    required_env = [
        "NEXT_PUBLIC_PLATFORM_FRONT_HOST",
        "NEXT_PUBLIC_LISTING_HOST",
        "NEXT_PUBLIC_CALCULATOR_MOUNT_BASE",
        "NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN",
        "NEXT_PUBLIC_TENANT_ID",
    ]

    env_keys = _load_env_keys(front_env_path)
    env_missing = [key for key in required_env if key not in env_keys]
    vercel = inspect_vercel_cli(cwd=front_app_path, check_auth=check_auth)

    blockers: List[str] = []
    if not front_app_path.exists():
        blockers.append("front_app_missing")
    if not (front_app_path / "package.json").exists():
        blockers.append("front_package_missing")
    if not (front_app_path / "vercel.json").exists():
        blockers.append("front_vercel_config_missing")
    if not (front_app_path / ".next" / "build-manifest.json").exists():
        blockers.append("front_build_artifacts_missing")
    if not front_env_path.exists():
        blockers.append("front_env_missing")
    if env_missing:
        blockers.append("front_env_incomplete")
    if str(audit_front.get("channel_role") or "").strip().lower() != "platform_front":
        blockers.append("front_channel_role_invalid")
    if str(audit_front.get("canonical_public_host") or "").strip().lower() != "seoulmna.kr":
        blockers.append("front_canonical_host_invalid")
    if str(audit_front.get("listing_market_host") or audit_front.get("current_content_host") or "").strip().lower() != "seoulmna.co.kr":
        blockers.append("front_listing_market_host_invalid")
    if str(audit_front.get("public_calculator_mount_base") or "").strip().lower() != "https://seoulmna.kr/_calc":
        blockers.append("front_public_calculator_mount_invalid")
    if not bool(front_audit.get("front_app", {}).get("build_artifacts_ready")):
        blockers.append("front_audit_build_not_ready")
    if not traffic_audit:
        blockers.append("traffic_gate_audit_missing")
    elif not bool(traffic_decision.get("traffic_leak_blocked")):
        blockers.append("traffic_gate_not_ready")
    elif list(traffic_decision.get("remaining_risks") or []):
        blockers.append("traffic_gate_remaining_risks")
    if traffic_audit and not bool(traffic_probe.get("server_started")):
        blockers.append("traffic_gate_live_probe_missing")
    if not vercel.get("available"):
        blockers.append("vercel_cli_missing")
    elif check_auth and not vercel.get("auth_ok"):
        blockers.append("vercel_auth_missing")

    unique_blockers: List[str] = []
    for item in blockers:
        if item and item not in unique_blockers:
            unique_blockers.append(item)

    next_actions: List[str] = []
    if "front_env_missing" in unique_blockers or "front_env_incomplete" in unique_blockers:
        next_actions.append("Run sync_kr_platform_front_env.py and regenerate .env.local")
    if "front_build_artifacts_missing" in unique_blockers or "front_audit_build_not_ready" in unique_blockers:
        next_actions.append("Run npm.cmd run build in the kr platform front workspace")
    if "traffic_gate_audit_missing" in unique_blockers or "traffic_gate_not_ready" in unique_blockers or "traffic_gate_remaining_risks" in unique_blockers or "traffic_gate_live_probe_missing" in unique_blockers:
        next_actions.append("Run validate_kr_traffic_gate.py and clear remaining iframe leak risks before preview deploy")
    if "vercel_cli_missing" in unique_blockers:
        next_actions.append("Expose Vercel CLI via vercel or npx.cmd")
    if "vercel_auth_missing" in unique_blockers:
        next_actions.append("Authenticate Vercel CLI for the kr platform front")
    if not next_actions and unique_blockers:
        next_actions.append("Review kr platform deploy blockers and rerun validation")
    if not unique_blockers:
        next_actions.append("Run deploy_kr_platform_front_preview.py to create a preview deployment")

    preview_deploy_ready = not unique_blockers
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": preview_deploy_ready,
        "front_app": {
            "path": str(front_app_path.resolve()),
            "exists": front_app_path.exists(),
            "env_path": str(front_env_path.resolve()),
            "env_exists": front_env_path.exists(),
            "env_keys": env_keys,
            "env_missing_keys": env_missing,
            "build_artifacts_ready": (front_app_path / ".next" / "build-manifest.json").exists(),
            "vercel_config_ready": (front_app_path / "vercel.json").exists(),
        },
        "topology": {
            "front_channel_role": str(audit_front.get("channel_role") or ""),
            "canonical_public_host": str(audit_front.get("canonical_public_host") or ""),
            "listing_market_host": str(audit_front.get("listing_market_host") or audit_front.get("current_content_host") or ""),
            "public_calculator_mount_base": str(audit_front.get("public_calculator_mount_base") or ""),
            "engine_origin": str(audit_front.get("engine_origin") or ""),
            "front_platform_status": str(audit_summary.get("front_platform_status") or ""),
        },
        "traffic_gate": {
            "audit_path": str(traffic_audit_path.resolve()),
            "traffic_leak_blocked": bool(traffic_decision.get("traffic_leak_blocked")),
            "remaining_risks": list(traffic_decision.get("remaining_risks") or []),
            "server_started": bool(traffic_probe.get("server_started")),
            "all_routes_no_iframe": bool(traffic_probe.get("all_routes_no_iframe")),
        },
        "vercel": vercel,
        "blocking_issues": unique_blockers,
        "handoff": {
            "preview_deploy_ready": preview_deploy_ready,
            "next_actions": [_normalize_action(item) for item in next_actions if _normalize_action(item)],
        },
    }


def _to_markdown(data: Dict[str, Any]) -> str:
    front = data.get("front_app") if isinstance(data.get("front_app"), dict) else {}
    topology = data.get("topology") if isinstance(data.get("topology"), dict) else {}
    traffic_gate = data.get("traffic_gate") if isinstance(data.get("traffic_gate"), dict) else {}
    vercel = data.get("vercel") if isinstance(data.get("vercel"), dict) else {}
    lines = [
        "# KR Platform Deploy Readiness",
        "",
        "## Topology",
        f"- front_channel_role: {topology.get('front_channel_role', '')}",
        f"- canonical_public_host: {topology.get('canonical_public_host', '')}",
        f"- listing_market_host: {topology.get('listing_market_host', '')}",
        f"- public_calculator_mount_base: {topology.get('public_calculator_mount_base', '')}",
        f"- engine_origin: {topology.get('engine_origin', '')}",
        f"- front_platform_status: {topology.get('front_platform_status', '')}",
        "",
        "## Traffic Gate",
        f"- traffic_leak_blocked: {traffic_gate.get('traffic_leak_blocked', False)}",
        f"- remaining_risks: {', '.join(traffic_gate.get('remaining_risks', [])) or '(none)'}",
        f"- server_started: {traffic_gate.get('server_started', False)}",
        f"- all_routes_no_iframe: {traffic_gate.get('all_routes_no_iframe', False)}",
        "",
        "## Front App",
        f"- path: {front.get('path', '')}",
        f"- env_exists: {front.get('env_exists', False)}",
        f"- build_artifacts_ready: {front.get('build_artifacts_ready', False)}",
        f"- vercel_config_ready: {front.get('vercel_config_ready', False)}",
        f"- env_missing_keys: {', '.join(front.get('env_missing_keys', [])) or '(none)'}",
        "",
        "## Vercel",
        f"- available: {vercel.get('available', False)}",
        f"- mode: {vercel.get('mode', '')}",
        f"- version: {vercel.get('version', '')}",
        f"- auth_ok: {vercel.get('auth_ok', False)}",
        f"- identity: {vercel.get('identity', '')}",
        "",
        "## Blockers",
    ]
    blockers = data.get("blocking_issues") if isinstance(data.get("blocking_issues"), list) else []
    if blockers:
        for item in blockers:
            lines.append(f"- {item}")
    else:
        lines.append("- (none)")
    lines.extend(
        [
            "",
            "## Next Actions",
        ]
    )
    actions = (
        (data.get("handoff") or {}).get("next_actions")
        if isinstance(data.get("handoff"), dict)
        else []
    )
    if actions:
        for item in actions:
            lines.append(f"- {item}")
    else:
        lines.append("- (none)")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate whether the kr platform front is ready for Vercel preview deploy")
    parser.add_argument("--front-app", default=str(DEFAULT_FRONT_APP))
    parser.add_argument("--front-env", default=str(DEFAULT_FRONT_ENV))
    parser.add_argument("--front-audit", default=str(DEFAULT_FRONT_AUDIT))
    parser.add_argument("--traffic-audit", default=str(DEFAULT_TRAFFIC_AUDIT))
    parser.add_argument("--skip-auth-check", action="store_true")
    parser.add_argument("--json", default="logs/kr_platform_deploy_ready_latest.json")
    parser.add_argument("--md", default="logs/kr_platform_deploy_ready_latest.md")
    args = parser.parse_args()

    payload = build_kr_platform_deploy_ready_report(
        front_app_path=Path(str(args.front_app)).resolve(),
        front_env_path=Path(str(args.front_env)).resolve(),
        front_audit_path=Path(str(args.front_audit)).resolve(),
        traffic_audit_path=Path(str(args.traffic_audit)).resolve(),
        check_auth=not bool(args.skip_auth_check),
    )
    json_path = (ROOT / str(args.json)).resolve()
    md_path = (ROOT / str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": bool(payload.get("ok")),
                "json": str(json_path),
                "md": str(md_path),
                "blocker_count": len(payload.get("blocking_issues") or []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
