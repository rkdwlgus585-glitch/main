#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_BIN = sys.executable or "python"
NPM_BIN = "npm.cmd" if sys.platform.startswith("win") else "npm"
DEFAULT_DIST_DIR = ".next-stage"
DEFAULT_PORT = 3027


def sanitize_console_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    encoding = sys.stdout.encoding or "utf-8"
    return value.encode(encoding, errors="replace").decode(encoding, errors="replace")


def sanitize_payload(payload: object) -> object:
    if isinstance(payload, dict):
        return {str(key): sanitize_payload(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    return sanitize_console_text(payload)


def print_json(payload: object) -> None:
    print(json.dumps(sanitize_payload(payload), ensure_ascii=False, indent=2))


def run_command(
    cmd: list[str],
    *,
    cwd: Path,
    timeout_sec: int = 1800,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.setdefault("CI", "1")
    if extra_env:
        env.update(extra_env)

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
        "returncode": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "command": cmd,
    }


def parse_json_output(text: str) -> Any:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def read_log_tail(path: Path, lines: int = 40) -> str:
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(content[-lines:])


def wait_for_server(base_url: str, *, timeout_sec: int, process: subprocess.Popen[str], log_path: Path) -> dict[str, Any]:
    deadline = time.time() + timeout_sec
    last_error = ""
    while time.time() < deadline:
        if process.poll() is not None:
            return {
                "ok": False,
                "reason": "server_exited_early",
                "returncode": process.returncode,
                "logTail": read_log_tail(log_path),
            }

        try:
            response = requests.get(base_url, timeout=10)
            if response.status_code < 500:
                return {
                    "ok": True,
                    "status": response.status_code,
                }
        except requests.RequestException as exc:
            last_error = str(exc)

        time.sleep(1)

    return {
        "ok": False,
        "reason": "server_start_timeout",
        "error": last_error,
        "logTail": read_log_tail(log_path),
    }


def start_server(*, dist_dir: str, port: int) -> tuple[subprocess.Popen[str], Any, Path]:
    env = os.environ.copy()
    env["BUILD_DIST_DIR"] = dist_dir
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.setdefault("CI", "1")

    log_path = PROJECT_ROOT / f"release-check-{port}.log"
    log_handle = log_path.open("w", encoding="utf-8", errors="replace")
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    process = subprocess.Popen(
        [NPM_BIN, "run", "start", "--", "--hostname", "127.0.0.1", "--port", str(port)],
        cwd=str(PROJECT_ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        creationflags=creationflags,
    )
    return process, log_handle, log_path


def stop_server(process: subprocess.Popen[str], log_handle: Any) -> None:
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
    finally:
        log_handle.close()


def build_steps(*, dist_dir: str, sync_env_preview: bool) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if sync_env_preview:
        steps.append(
            {
                "name": "sync_env_preview",
                "command": [PYTHON_BIN, "scripts/sync_env_local.py", "--mode", "preview"],
            }
        )

    steps.extend(
        [
            {"name": "export_sheet_listings", "command": [NPM_BIN, "run", "export:listings:sheet"]},
            {"name": "verify_legacy", "command": [NPM_BIN, "run", "verify:legacy"]},
            {"name": "verify_market", "command": [NPM_BIN, "run", "verify:market"]},
            {"name": "verify_regulatory", "command": [NPM_BIN, "run", "verify:regulatory"]},
            {"name": "lint", "command": [NPM_BIN, "run", "lint"]},
            {
                "name": "build",
                "command": [NPM_BIN, "run", "build"],
                "extraEnv": {"BUILD_DIST_DIR": dist_dir},
            },
        ]
    )
    return steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a full local release check for co_kr_public_site.")
    parser.add_argument("--dist-dir", default=DEFAULT_DIST_DIR)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--server-timeout-sec", type=int, default=90)
    parser.add_argument("--smoke-timeout-sec", type=int, default=90)
    parser.add_argument("--skip-smoke", action="store_true")
    parser.add_argument("--sync-env-preview", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dist_dir = str(args.dist_dir or DEFAULT_DIST_DIR).strip() or DEFAULT_DIST_DIR
    port = int(args.port or DEFAULT_PORT)
    base_url = f"http://127.0.0.1:{port}"

    step_results: list[dict[str, Any]] = []
    for step in build_steps(dist_dir=dist_dir, sync_env_preview=bool(args.sync_env_preview)):
        result = run_command(
            [str(part) for part in step["command"]],
            cwd=PROJECT_ROOT,
            timeout_sec=1800,
            extra_env=step.get("extraEnv"),
        )
        payload = {
            "name": step["name"],
            "command": result["command"],
            "ok": bool(result["ok"]),
            "returncode": result["returncode"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
        }
        parsed = parse_json_output(result["stdout"])
        if parsed is not None:
            payload["parsed"] = parsed
        step_results.append(payload)
        if not result["ok"]:
            print_json(
                {
                    "ok": False,
                    "reason": "step_failed",
                    "failedStep": payload,
                    "steps": step_results,
                    "distDir": dist_dir,
                    "baseUrl": base_url,
                }
            )
            return 1

    if args.skip_smoke:
        print_json(
            {
                "ok": True,
                "mode": "preflight_only",
                "steps": step_results,
                "distDir": dist_dir,
                "baseUrl": base_url,
            }
        )
        return 0

    process, log_handle, log_path = start_server(dist_dir=dist_dir, port=port)
    try:
        server_ready = wait_for_server(
            base_url,
            timeout_sec=max(15, int(args.server_timeout_sec or 90)),
            process=process,
            log_path=log_path,
        )
        if not server_ready["ok"]:
            print_json(
                {
                    "ok": False,
                    "reason": "server_not_ready",
                    "steps": step_results,
                    "server": server_ready,
                    "distDir": dist_dir,
                    "baseUrl": base_url,
                    "logPath": str(log_path),
                }
            )
            return 1

        smoke = run_command(
            [
                PYTHON_BIN,
                "scripts/smoke_test_local.py",
                "--base-url",
                base_url,
                "--timeout-sec",
                str(max(10, int(args.smoke_timeout_sec or 90))),
            ],
            cwd=PROJECT_ROOT,
            timeout_sec=max(60, int(args.smoke_timeout_sec or 90) + 30),
        )
        smoke_payload = {
            "ok": bool(smoke["ok"]),
            "returncode": smoke["returncode"],
            "command": smoke["command"],
            "stdout": smoke["stdout"],
            "stderr": smoke["stderr"],
            "parsed": parse_json_output(smoke["stdout"]),
        }

        if not smoke["ok"]:
            print_json(
                {
                    "ok": False,
                    "reason": "smoke_failed",
                    "steps": step_results,
                    "server": server_ready,
                    "smoke": smoke_payload,
                    "distDir": dist_dir,
                    "baseUrl": base_url,
                    "logPath": str(log_path),
                }
            )
            return 1

        print_json(
            {
                "ok": True,
                "mode": "full_local_release_check",
                "steps": step_results,
                "server": server_ready,
                "smoke": smoke_payload,
                "distDir": dist_dir,
                "baseUrl": base_url,
                "logPath": str(log_path),
            }
        )
        return 0
    finally:
        stop_server(process, log_handle)


if __name__ == "__main__":
    sys.exit(main())
