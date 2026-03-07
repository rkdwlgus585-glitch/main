#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FRONT_APP = ROOT / "workspace_partitions" / "site_session" / "kr_platform_front"


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _contains(text: str, token: str) -> bool:
    return str(token or "") in str(text or "")


def build_static_audit(front_app_path: Path) -> Dict[str, Any]:
    widget_frame = _read_text(front_app_path / "components" / "widget-frame.tsx")
    yangdo_page = _read_text(front_app_path / "app" / "yangdo" / "page.tsx")
    permit_page = _read_text(front_app_path / "app" / "permit" / "page.tsx")
    widget_yangdo = _read_text(front_app_path / "app" / "widget" / "yangdo" / "page.tsx")
    widget_permit = _read_text(front_app_path / "app" / "widget" / "permit" / "page.tsx")

    return {
        "widget_frame_gate_ready": (
            _contains(widget_frame, '"use client"')
            and _contains(widget_frame, "useState")
            and _contains(widget_frame, "widget-gate")
            and _contains(widget_frame, "!isExpanded")
            and _contains(widget_frame, "<iframe")
        ),
        "public_pages_use_gate_copy": (
            _contains(yangdo_page, "gateNote={")
            and _contains(permit_page, "gateNote={")
            and _contains(yangdo_page, "launchLabel={")
            and _contains(permit_page, "launchLabel={")
        ),
        "widget_pages_noindex_ready": (
            _contains(widget_yangdo, "robots:")
            and _contains(widget_permit, "robots:")
            and _contains(widget_yangdo, "index: false")
            and _contains(widget_permit, "index: false")
        ),
    }


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as handle:
        handle.bind(("127.0.0.1", 0))
        return int(handle.getsockname()[1])


def _wait_http(url: str, timeout_sec: int) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            res = requests.get(url, timeout=3)
            if res.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _kill_process_tree(proc: subprocess.Popen[Any]) -> None:
    if proc.poll() is not None:
        return
    try:
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass


def _run_cmd(args: List[str], cwd: Path, timeout_sec: int) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    return subprocess.run(
        args,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="ignore",
        timeout=timeout_sec,
        env=env,
        check=False,
    )


def _fetch_route(url: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {"url": url, "ok": False}
    try:
        res = requests.get(url, timeout=10)
        text = res.text or ""
        out.update(
            {
                "ok": res.status_code == 200,
                "status_code": int(res.status_code),
                "contains_iframe": "<iframe" in text.lower(),
                "contains_launch_button_marker": 'data-traffic-gate-launch="true"' in text,
            }
        )
        return out
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)
        return out


def run_live_probe(front_app_path: Path, port: int, timeout_sec: int, skip_build: bool) -> Dict[str, Any]:
    build_result: Dict[str, Any] = {"skipped": bool(skip_build), "ok": True}
    if not skip_build:
        build = _run_cmd(["npm.cmd", "run", "build"], front_app_path, timeout_sec)
        build_result = {
            "skipped": False,
            "ok": build.returncode == 0,
            "returncode": build.returncode,
            "stdout_tail": "\n".join((build.stdout or "").splitlines()[-20:]),
            "stderr_tail": "\n".join((build.stderr or "").splitlines()[-20:]),
        }
        if build.returncode != 0:
            return {"build": build_result, "server_started": False, "routes": []}

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    proc = subprocess.Popen(
        ["npm.cmd", "run", "start", "--", "--hostname", "127.0.0.1", "--port", str(port)],
        cwd=str(front_app_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore",
        env=env,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        started = _wait_http(base_url, timeout_sec)
        routes: List[Dict[str, Any]] = []
        if started:
            for route in ("/yangdo", "/permit", "/widget/yangdo", "/widget/permit"):
                routes.append(_fetch_route(f"{base_url}{route}"))
        return {
            "build": build_result,
            "server_started": started,
            "base_url": base_url,
            "routes": routes,
            "all_routes_no_iframe": all(not bool(row.get("contains_iframe")) for row in routes) if routes else False,
        }
    finally:
        _kill_process_tree(proc)


def build_traffic_gate_report(front_app_path: Path, skip_build: bool, timeout_sec: int, port: int | None) -> Dict[str, Any]:
    static_audit = build_static_audit(front_app_path)
    live_probe = run_live_probe(front_app_path, port or _find_free_port(), timeout_sec, skip_build)
    decision = {
        "traffic_leak_blocked": bool(static_audit.get("widget_frame_gate_ready")) and bool(live_probe.get("all_routes_no_iframe")),
        "remaining_risks": [],
    }
    if not static_audit.get("widget_pages_noindex_ready"):
        decision["remaining_risks"].append("widget_noindex_missing")
    if not live_probe.get("server_started"):
        decision["remaining_risks"].append("local_probe_not_started")
    if live_probe.get("routes") and not live_probe.get("all_routes_no_iframe"):
        decision["remaining_risks"].append("iframe_present_in_initial_html")

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "front_app_path": str(front_app_path),
        "static_audit": static_audit,
        "live_probe": live_probe,
        "decision": decision,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# KR Traffic Gate Audit",
        "",
        "## Static Audit",
        f"- widget_frame_gate_ready: {payload.get('static_audit', {}).get('widget_frame_gate_ready')}",
        f"- public_pages_use_gate_copy: {payload.get('static_audit', {}).get('public_pages_use_gate_copy')}",
        f"- widget_pages_noindex_ready: {payload.get('static_audit', {}).get('widget_pages_noindex_ready')}",
        "",
        "## Live Probe",
        f"- server_started: {payload.get('live_probe', {}).get('server_started')}",
        f"- all_routes_no_iframe: {payload.get('live_probe', {}).get('all_routes_no_iframe')}",
    ]
    for row in payload.get("live_probe", {}).get("routes") or []:
        lines.append(
            f"- {row.get('url')}: ok={row.get('ok')} contains_iframe={row.get('contains_iframe')} contains_launch_button_marker={row.get('contains_launch_button_marker')}"
        )
    lines.extend(
        [
            "",
            "## Decision",
            f"- traffic_leak_blocked: {payload.get('decision', {}).get('traffic_leak_blocked')}",
            f"- remaining_risks: {', '.join(payload.get('decision', {}).get('remaining_risks') or []) or '(none)'}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate that kr platform routes do not create widget traffic before explicit user action.")
    parser.add_argument("--front-app", type=Path, default=DEFAULT_FRONT_APP)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "kr_traffic_gate_audit_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "kr_traffic_gate_audit_latest.md")
    args = parser.parse_args()

    payload = build_traffic_gate_report(
        front_app_path=args.front_app,
        skip_build=bool(args.skip_build),
        timeout_sec=max(30, int(args.timeout_sec)),
        port=int(args.port) or None,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

