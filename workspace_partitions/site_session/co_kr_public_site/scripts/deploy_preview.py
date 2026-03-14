#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from validate_deploy_ready import build_report, resolve_vercel_runner, run_command

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_BIN = sys.executable or "python"
PREFLIGHT_STEPS = [
    {
        "name": "sync_env",
        "command": [PYTHON_BIN, "scripts/sync_env_local.py", "--mode", "preview"],
    },
    {
        "name": "local_release_check",
        "command": [
            PYTHON_BIN,
            "scripts/run_local_release_check.py",
            "--dist-dir",
            ".next-stage",
            "--port",
            "3027",
        ],
    },
]


def extract_preview_url(text: str) -> str:
    matches = re.findall(r"https://[^\s\"']+\.vercel\.app", text)
    return matches[-1] if matches else ""


def sanitize_console_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    encoding = sys.stdout.encoding or "utf-8"
    return value.encode(encoding, errors="replace").decode(encoding, errors="replace")


def sanitize_payload(payload: dict[str, object]) -> dict[str, object]:
    sanitized: dict[str, object] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            sanitized[key] = sanitize_payload(value)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_payload(item) if isinstance(item, dict) else sanitize_console_text(item) for item in value]
        else:
            sanitized[key] = sanitize_console_text(value)
    return sanitized


def run_preflight_steps() -> tuple[bool, list[dict[str, object]], dict[str, object] | None]:
    results: list[dict[str, object]] = []
    for step in PREFLIGHT_STEPS:
        result = run_command([str(part) for part in step["command"]], cwd=PROJECT_ROOT, timeout_sec=1800)
        payload = {
            "name": step["name"],
            "command": result["command"],
            "ok": bool(result["ok"]),
            "returncode": result["returncode"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
        }
        results.append(payload)
        if not result["ok"]:
            return False, results, payload
    return True, results, None


def should_skip_preflight(argv: list[str]) -> bool:
    return "--skip-preflight" in argv


def main() -> int:
    skip_preflight = should_skip_preflight(sys.argv[1:])
    preflight_results: list[dict[str, object]] = []
    if not skip_preflight:
        ok, preflight_results, failed_step = run_preflight_steps()
        if not ok:
            print(
                json.dumps(
                    sanitize_payload(
                        {
                            "ok": False,
                            "reason": "preflight_failed",
                            "failedStep": failed_step,
                            "preflight": preflight_results,
                        }
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 1

    report = build_report(check_auth=True)
    if report["blockingIssues"]:
        print(
            json.dumps(
                sanitize_payload(
                    {
                        "ok": False,
                        "reason": "deploy_blocked",
                        "blockingIssues": report["blockingIssues"],
                        "nextActions": report["nextActions"],
                        "preflight": preflight_results,
                    }
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    runner, mode = resolve_vercel_runner()
    if not runner:
        print(json.dumps({"ok": False, "reason": "vercel_cli_missing"}, ensure_ascii=False, indent=2))
        return 1

    result = run_command([*runner, "deploy", "-y"], cwd=PROJECT_ROOT, timeout_sec=1800)
    combined = ((result.get("stdout") or "") + "\n" + (result.get("stderr") or "")).strip()
    preview_url = extract_preview_url(combined)
    payload = {
        "ok": bool(result["ok"]),
        "mode": mode,
        "command": result["command"],
        "preflight": preflight_results,
        "previewUrl": preview_url,
        "stdout": result["stdout"],
        "stderr": result["stderr"],
    }
    print(json.dumps(sanitize_payload(payload), ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
