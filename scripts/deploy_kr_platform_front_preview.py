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

from scripts.validate_kr_platform_deploy_ready import inspect_vercel_cli  # noqa: E402

DEFAULT_FRONT_APP = ROOT / "workspace_partitions" / "site_session" / "kr_platform_front"


def _run(
    cmd: List[str],
    *,
    cwd: Path,
    timeout_sec: int = 900,
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
        "stdout": stdout_text,
        "stderr": stderr_text,
        "json": parsed,
    }


def _extract_preview_url(text: str) -> str:
    tokens = [segment.strip() for segment in str(text or "").replace("\n", " ").split(" ") if segment.strip()]
    for token in tokens:
        if token.startswith("https://") and ".vercel.app" in token:
            return token.rstrip(".,")
    return ""


def _normalize_blockers(items: List[str]) -> List[str]:
    out: List[str] = []
    for item in items or []:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _extract_sync_output(step: Dict[str, Any]) -> Dict[str, Any]:
    payload = step.get("json") if isinstance(step.get("json"), dict) else {}
    return payload if payload else {}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_preview_report(
    *,
    sync_step: Dict[str, Any],
    readiness_payload: Dict[str, Any],
    deploy_step: Dict[str, Any],
    front_app_path: Path,
) -> Dict[str, Any]:
    blockers = _normalize_blockers(list(readiness_payload.get("blocking_issues") or []))
    deploy_stdout = str(deploy_step.get("stdout") or "")
    deploy_stderr = str(deploy_step.get("stderr") or "")
    preview_url = _extract_preview_url(f"{deploy_stdout}\n{deploy_stderr}")
    if not deploy_step.get("ok") and "vercel_auth_missing" not in blockers:
        combined = f"{deploy_stdout}\n{deploy_stderr}".lower()
        if "not logged in" in combined or "no existing credentials found" in combined:
            blockers.append("vercel_auth_missing")
    ok = bool(deploy_step.get("ok")) and bool(preview_url)
    next_actions: List[str] = []
    if "vercel_auth_missing" in blockers:
        next_actions.append("Authenticate Vercel CLI and rerun the kr preview deploy")
    if "vercel_cli_missing" in blockers:
        next_actions.append("Expose vercel or npx.cmd before running the kr preview deploy")
    if not blockers and not ok:
        next_actions.append("Review Vercel deploy stderr and rerun the preview deploy")
    if ok:
        next_actions.append("Review the preview URL and then decide whether to promote the kr front to canonical")
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": ok,
        "front_app": str(front_app_path.resolve()),
        "topology": {
            "public_front_host": "seoulmna.kr",
            "internal_widget_host": "seoulmna.co.kr",
            "engine_mode": "private",
        },
        "steps": {
            "sync_env": {
                "ok": bool(sync_step.get("ok")),
                "output": _extract_sync_output(sync_step),
            },
            "validate_readiness": readiness_payload,
            "deploy_preview": {
                "ok": bool(deploy_step.get("ok")),
                "returncode": int(deploy_step.get("returncode") or 0),
                "preview_url": preview_url,
                "stdout_tail": "\n".join(deploy_stdout.splitlines()[-40:]),
                "stderr_tail": "\n".join(deploy_stderr.splitlines()[-40:]),
            },
        },
        "blocking_issues": blockers,
        "handoff": {
            "preview_url": preview_url,
            "preview_deployed": ok,
            "traffic_gate_ok": bool(((readiness_payload.get("traffic_gate") or {}) if isinstance(readiness_payload.get("traffic_gate"), dict) else {}).get("traffic_leak_blocked")),
            "next_actions": next_actions,
        },
    }


def _to_markdown(data: Dict[str, Any]) -> str:
    handoff = data.get("handoff") if isinstance(data.get("handoff"), dict) else {}
    steps = data.get("steps") if isinstance(data.get("steps"), dict) else {}
    deploy_preview = steps.get("deploy_preview") if isinstance(steps.get("deploy_preview"), dict) else {}
    lines = [
        "# KR Platform Preview Deploy",
        "",
        f"- ok: {data.get('ok')}",
        f"- preview_deployed: {handoff.get('preview_deployed')}",
        f"- preview_url: {handoff.get('preview_url', '')}",
        "",
        "## Topology",
        f"- public_front_host: {(data.get('topology') or {}).get('public_front_host', '')}",
        f"- internal_widget_host: {(data.get('topology') or {}).get('internal_widget_host', '')}",
        f"- engine_mode: {(data.get('topology') or {}).get('engine_mode', '')}",
        "",
        "## Traffic Gate",
        f"- traffic_gate_ok: {handoff.get('traffic_gate_ok')}",
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
            "## Deploy Output",
            f"- returncode: {deploy_preview.get('returncode')}",
            f"- stdout_tail: {deploy_preview.get('stdout_tail', '').replace(chr(10), ' | ')}",
            f"- stderr_tail: {deploy_preview.get('stderr_tail', '').replace(chr(10), ' | ')}",
            "",
            "## Next Actions",
        ]
    )
    for item in handoff.get("next_actions") or []:
        lines.append(f"- {item}")
    if not (handoff.get("next_actions") or []):
        lines.append("- (none)")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy the kr platform front to a Vercel preview")
    parser.add_argument("--front-app", default=str(DEFAULT_FRONT_APP))
    parser.add_argument("--sync-script", default="scripts/sync_kr_platform_front_env.py")
    parser.add_argument("--readiness-script", default="scripts/validate_kr_platform_deploy_ready.py")
    parser.add_argument("--readiness-json", default="logs/kr_platform_deploy_ready_latest.json")
    parser.add_argument("--readiness-md", default="logs/kr_platform_deploy_ready_latest.md")
    parser.add_argument("--json", default="logs/kr_platform_front_preview_latest.json")
    parser.add_argument("--md", default="logs/kr_platform_front_preview_latest.md")
    args = parser.parse_args()

    front_app_path = Path(str(args.front_app)).resolve()
    sync_step = _run([sys.executable, str((ROOT / str(args.sync_script)).resolve())], cwd=ROOT)
    readiness_json_path = (ROOT / str(args.readiness_json)).resolve()
    readiness_step = _run(
        [
            sys.executable,
            str((ROOT / str(args.readiness_script)).resolve()),
            "--json",
            str(args.readiness_json),
            "--md",
            str(args.readiness_md),
        ],
        cwd=ROOT,
    )
    readiness_payload = _load_json(readiness_json_path)
    blockers = list(readiness_payload.get("blocking_issues") or [])
    if blockers:
        deploy_step = {
            "ok": False,
            "returncode": 2,
            "stdout": "",
            "stderr": "preview deploy blocked by readiness validation",
        }
    else:
        vercel_info = inspect_vercel_cli(cwd=front_app_path, check_auth=False)
        runner = vercel_info.get("mode")
        cmd = []
        if runner == "vercel":
            cmd = [shutil.which("vercel") or "vercel", "deploy", "-y"]  # type: ignore[name-defined]
        else:
            npx_cmd = shutil.which("npx.cmd") or shutil.which("npx")  # type: ignore[name-defined]
            cmd = [npx_cmd or "npx", "--yes", "vercel", "deploy", "-y"]
        deploy_step = _run(cmd, cwd=front_app_path, timeout_sec=1200)

    payload = build_preview_report(
        sync_step=sync_step,
        readiness_payload=readiness_payload,
        deploy_step=deploy_step,
        front_app_path=front_app_path,
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
                "preview_url": ((payload.get("handoff") or {}) if isinstance(payload.get("handoff"), dict) else {}).get("preview_url", ""),
                "blocker_count": len(payload.get("blocking_issues") or []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if payload.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
