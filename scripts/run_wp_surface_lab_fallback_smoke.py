#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple


ROOT = Path(__file__).resolve().parents[1]
LAB_RUNTIME = ROOT / "workspace_partitions" / "site_session" / "wp_surface_lab" / "runtime" / "php_fallback"
BOOTSTRAP_SCRIPT = ROOT / "scripts" / "bootstrap_wp_surface_lab_php_fallback.py"
BOOTSTRAP_JSON = ROOT / "logs" / "wp_surface_lab_php_fallback_latest.json"
BOOTSTRAP_MD = ROOT / "logs" / "wp_surface_lab_php_fallback_latest.md"
DEFAULT_REPORT = ROOT / "logs" / "wp_surface_lab_fallback_smoke_latest.json"
START_SCRIPT = LAB_RUNTIME / "start-wordpress-php-fallback.ps1"
STOP_SCRIPT = LAB_RUNTIME / "stop-wordpress-php-fallback.ps1"
PID_FILE = LAB_RUNTIME / "php-site.pid"
DEFAULT_BASE_URL = "http://127.0.0.1:18081"


def _body_has_bootstrap_error(body: str) -> bool:
    lowered = str(body or "").lower()
    needles = (
        "fatal error",
        "failed opening required",
        "warning</b>:  require(",
        "warning: require(",
        "uncaught error",
    )
    return any(token in lowered for token in needles)


def _probe_ok(probe: Dict[str, Any]) -> bool:
    status = int(probe.get("status") or 0)
    body_excerpt = str(probe.get("body_excerpt") or "")
    return bool(probe.get("ok")) and 200 <= status < 400 and not _body_has_bootstrap_error(body_excerpt)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _elapsed(started_at: float) -> float:
    return round(time.perf_counter() - started_at, 3)


def _run_command(cmd: list[str], *, timeout: int = 180) -> Dict[str, Any]:
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


def _run_powershell(script_path: Path, *, timeout: int = 180) -> Dict[str, Any]:
    return _run_command(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ],
        timeout=timeout,
    )


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


def _request(url: str, *, timeout: int = 12) -> Tuple[int, str, str]:
    try:
        with urllib.request.urlopen(url, timeout=max(1, int(timeout))) as response:
            body = response.read(65536).decode("utf-8", errors="replace")
            return int(response.status), str(response.geturl()), body
    except urllib.error.HTTPError as exc:
        body = exc.read(65536).decode("utf-8", errors="replace")
        return int(exc.code), str(exc.geturl()), body
    except Exception as exc:  # noqa: BLE001
        return 0, url, str(exc)


def _wait_for_http(url: str, *, timeout_sec: int = 20) -> Dict[str, Any]:
    deadline = time.time() + max(1, int(timeout_sec))
    last_status = 0
    last_url = url
    last_body = ""
    while time.time() < deadline:
        status, final_url, body = _request(url, timeout=12)
        last_status = status
        last_url = final_url
        last_body = body
        if 200 <= status < 500:
            return {
                "ok": True,
                "status": status,
                "final_url": final_url,
                "body_excerpt": body[:400],
            }
        time.sleep(0.5)
    return {
        "ok": False,
        "status": last_status,
        "final_url": last_url,
        "body_excerpt": last_body[:400],
    }


def _wait_until_down(url: str, *, timeout_sec: int = 12) -> bool:
    deadline = time.time() + max(1, int(timeout_sec))
    while time.time() < deadline:
        status, _, _ = _request(url, timeout=4)
        if status == 0:
            return True
        time.sleep(0.4)
    return False


def _bootstrap() -> Dict[str, Any]:
    started = time.perf_counter()
    run = _run_command(
        [
            "py",
            "-3",
            str(BOOTSTRAP_SCRIPT),
            "--json",
            str(BOOTSTRAP_JSON),
            "--md",
            str(BOOTSTRAP_MD),
        ],
        timeout=300,
    )
    payload = _load_json(BOOTSTRAP_JSON)
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    return {
        "duration_sec": _elapsed(started),
        "command": run,
        "result": payload,
        "ok": bool(run.get("ok")) and bool(summary.get("bootstrap_ready")),
    }


def run_smoke(*, report_path: Path | None = None, base_url: str = DEFAULT_BASE_URL) -> Dict[str, Any]:
    started_total = time.perf_counter()
    home_url = str(base_url or DEFAULT_BASE_URL).rstrip("/") + "/"
    admin_url = str(base_url or DEFAULT_BASE_URL).rstrip("/") + "/wp-admin/"
    install_url = str(base_url or DEFAULT_BASE_URL).rstrip("/") + "/wp-admin/install.php"

    out: Dict[str, Any] = {
        "generated_at": _now(),
        "ok": False,
        "blocking_issues": [],
        "timing": {},
        "bootstrap": {},
        "stop_before_start": {},
        "start": {},
        "probes": {},
        "stop_after_probe": {},
        "brainstorming": {
            "goal": "Validate that the WordPress surface-lab PHP fallback can bootstrap, listen on localhost, and serve core routes after the H:\\auto path migration.",
            "design": [
                "Rebuild the fallback site root first so the smoke always tests the latest router, db drop-in, and launch scripts.",
                "Treat the fallback as an ops-only lab path, not a publish-critical path, unless it becomes part of operator-facing production flow.",
                "Require start, HTTP reachability, and clean stop so stale pid or site-path drift fails immediately.",
            ],
        },
    }

    started = time.perf_counter()
    out["bootstrap"] = _bootstrap()
    out["timing"]["bootstrap_sec"] = _elapsed(started)
    if not out["bootstrap"].get("ok"):
        out["blocking_issues"].append("bootstrap_failed")

    started = time.perf_counter()
    out["stop_before_start"] = _run_powershell(STOP_SCRIPT, timeout=60)
    out["timing"]["stop_before_start_sec"] = _elapsed(started)

    started = time.perf_counter()
    start_run = _run_powershell(START_SCRIPT, timeout=60)
    start_pid = ""
    if start_run.get("ok"):
        start_pid = str(start_run.get("stdout") or "").strip().splitlines()[-1].strip()
    pid_exists = PID_FILE.exists()
    pid_file_value = PID_FILE.read_text(encoding="utf-8", errors="replace").strip() if pid_exists else ""
    out["start"] = {
        "command": start_run,
        "pid_file_exists": pid_exists,
        "pid_file_value": pid_file_value,
        "reported_pid": start_pid,
        "ok": bool(start_run.get("ok")) and pid_exists and bool(pid_file_value),
    }
    out["timing"]["start_sec"] = _elapsed(started)
    if not out["start"].get("ok"):
        out["blocking_issues"].append("start_failed")

    started = time.perf_counter()
    home_probe = _wait_for_http(home_url, timeout_sec=20)
    admin_probe = _wait_for_http(admin_url, timeout_sec=20)
    install_probe = _wait_for_http(install_url, timeout_sec=20)
    home_ok = _probe_ok(home_probe)
    admin_ok = _probe_ok(admin_probe)
    install_ok = _probe_ok(install_probe)
    out["probes"] = {
        "home": home_probe,
        "admin": admin_probe,
        "install": install_probe,
        "home_ok": home_ok,
        "admin_ok": admin_ok,
        "install_ok": install_ok,
        "ok": home_ok and admin_ok and install_ok,
    }
    out["timing"]["probe_sec"] = _elapsed(started)
    if not out["probes"].get("ok"):
        out["blocking_issues"].append("http_probe_failed")

    started = time.perf_counter()
    stop_run = _run_powershell(STOP_SCRIPT, timeout=60)
    down_ok = _wait_until_down(home_url, timeout_sec=12)
    out["stop_after_probe"] = {
        "command": stop_run,
        "server_down": down_ok,
        "ok": bool(stop_run.get("ok")) and down_ok,
    }
    out["timing"]["stop_after_probe_sec"] = _elapsed(started)
    if not out["stop_after_probe"].get("ok"):
        out["blocking_issues"].append("stop_failed")

    out["timing"]["total_duration_sec"] = _elapsed(started_total)
    out["ok"] = not out["blocking_issues"]
    final_path = Path(report_path or DEFAULT_REPORT).resolve()
    _save_json(final_path, out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the WordPress surface-lab PHP fallback bootstrap and local server lifecycle.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()
    result = run_smoke(report_path=Path(str(args.report)).resolve(), base_url=str(args.base_url or DEFAULT_BASE_URL))
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(rendered, end="")
    return 0 if bool(result.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
