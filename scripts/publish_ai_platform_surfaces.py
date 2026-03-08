#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_REPORT = LOG_DIR / "ai_platform_publish_latest.json"
PRIVATE_REPORT = LOG_DIR / "wp_private_ai_pages_latest.json"
PUBLIC_REPORT = LOG_DIR / "yangdo_kr_bridge_latest.json"
PUBLIC_VERIFY_REPORT = LOG_DIR / "public_calculator_post_publish_verify_latest.json"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            data = json.loads(path.read_text(encoding=encoding))
            return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


def _run(cmd: List[str], *, timeout: int = 1800) -> Dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(1, int(timeout)),
    )
    return {
        "command": cmd,
        "returncode": int(proc.returncode),
        "ok": proc.returncode == 0,
        "stdout": str(proc.stdout or ""),
        "stderr": str(proc.stderr or ""),
    }


def _trim(text: str, limit: int = 1800) -> str:
    value = str(text or "")
    if len(value) <= limit:
        return value
    head = max(300, limit // 2)
    return value[:head] + "\n... [trimmed] ...\n" + value[-head:]


def main() -> int:
    parser = argparse.ArgumentParser(description="Orchestrate private/public SeoulMNA calculator publishing from a single entrypoint.")
    parser.add_argument("--mode", choices=["private", "public", "both"], default="private")
    parser.add_argument("--skip-regression", action="store_true", default=False)
    parser.add_argument("--confirm-live", default="", help="Required for public mode: pass YES to allow live public publish")
    parser.add_argument("--publish-co", action="store_true", default=False, help="Allow .co bridge publish in public mode")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    mode = str(args.mode or "private")
    report_path = Path(str(args.report)).resolve()
    report: Dict[str, Any] = {
        "generated_at": _now(),
        "ok": False,
        "mode": mode,
        "blocking_issues": [],
        "private": {},
        "public": {},
        "public_verify": {},
        "brainstorming": {
            "goal": "public/private calculator deploy를 단일 진입점으로 묶고, live 반영 뒤에는 바로 public 검증까지 닫는다",
            "design": [
                "private publish는 기존 regression gate를 그대로 재사용한다",
                "public publish는 기존 bridge deploy 스크립트를 래핑해 로직 중복을 피한다",
                "public live 변경은 confirm-live YES 없이는 절대 실행하지 않는다",
                "public 반영 뒤에는 live URL 검증을 다시 실행해 deploy 성공과 runtime 정상 여부를 분리해 본다",
            ],
        },
    }

    if mode in {"private", "both"}:
        private_cmd = [sys.executable, str(ROOT / "scripts" / "publish_private_ai_admin_pages.py")]
        if bool(args.skip_regression):
            private_cmd.append("--skip-regression")
        private_run = _run(private_cmd, timeout=1800)
        private_report = _load_json(PRIVATE_REPORT)
        report["private"] = {
            "command": private_cmd,
            "result": private_run,
            "report": private_report,
            "ok": bool(private_run.get("ok")) and bool(private_report.get("ok")),
            "stdout_preview": _trim(str(private_run.get("stdout") or "")),
            "stderr_preview": _trim(str(private_run.get("stderr") or "")),
        }
        if not report["private"]["ok"]:
            report["blocking_issues"].append("private_publish_failed")

    if mode in {"public", "both"}:
        if str(args.confirm_live or "").strip().upper() != "YES":
            report["public"] = {
                "ok": False,
                "skipped": True,
                "reason": "confirm_live_missing",
            }
            report["blocking_issues"].append("public_confirm_live_missing")
        else:
            public_cmd = [
                sys.executable,
                str(ROOT / "scripts" / "deploy_yangdo_kr_banner_bridge.py"),
                "--confirm-live",
                "YES",
                "--report",
                str(PUBLIC_REPORT),
            ]
            if bool(args.publish_co):
                public_cmd.append("--publish-co")
            public_run = _run(public_cmd, timeout=2400)
            public_report = _load_json(PUBLIC_REPORT)
            report["public"] = {
                "command": public_cmd,
                "result": public_run,
                "report": public_report,
                "ok": bool(public_run.get("ok")) and bool(public_report.get("ok")),
                "stdout_preview": _trim(str(public_run.get("stdout") or "")),
                "stderr_preview": _trim(str(public_run.get("stderr") or "")),
            }
            if not report["public"]["ok"]:
                report["blocking_issues"].append("public_publish_failed")
            else:
                public_verify_cmd = [
                    sys.executable,
                    str(ROOT / "scripts" / "run_public_calculator_post_publish_verify.py"),
                    "--report",
                    str(PUBLIC_VERIFY_REPORT),
                ]
                public_verify_run = _run(public_verify_cmd, timeout=1800)
                public_verify_report = _load_json(PUBLIC_VERIFY_REPORT)
                report["public_verify"] = {
                    "command": public_verify_cmd,
                    "result": public_verify_run,
                    "report": public_verify_report,
                    "ok": bool(public_verify_run.get("ok")) and bool(public_verify_report.get("ok")),
                    "stdout_preview": _trim(str(public_verify_run.get("stdout") or "")),
                    "stderr_preview": _trim(str(public_verify_run.get("stderr") or "")),
                }
                if not report["public_verify"]["ok"]:
                    report["blocking_issues"].append("public_post_publish_verify_failed")

    report["ok"] = not report["blocking_issues"]
    _save_json(report_path, report)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    try:
        sys.stdout.write(rendered)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(rendered.encode("utf-8", errors="replace"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
