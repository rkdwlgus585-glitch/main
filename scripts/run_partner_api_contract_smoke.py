#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_partner_api_smoke import run_smoke


LOG_DIR = ROOT / "logs"
DEFAULT_REPORT = LOG_DIR / "partner_api_contract_smoke_latest.json"
ENV_PATH = ROOT / ".env"
PERMIT_STDOUT_LOG = LOG_DIR / "partner_permit_ephemeral_stdout.log"
PERMIT_STDERR_LOG = LOG_DIR / "partner_permit_ephemeral_stderr.log"


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_env_value(key: str) -> str:
    raw = str(os.getenv(key) or "").strip()
    if raw:
        return raw
    if not ENV_PATH.exists():
        return ""
    try:
        for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
            text = str(line or "").strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            env_key, env_value = text.split("=", 1)
            if str(env_key).strip() == key:
                return str(env_value).strip().strip('"').strip("'")
    except Exception:
        return ""
    return ""


def _is_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", int(port))) != 0


def _pick_free_port() -> int:
    for port in (8792, 8796, 8798, 8892):
        if _is_port_free(port):
            return int(port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_health(url: str, *, timeout_sec: int = 25) -> Tuple[bool, str]:
    deadline = time.time() + max(1, int(timeout_sec))
    last_error = ""
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=4) as response:
                if int(response.status) == 200:
                    return True, ""
        except urllib.error.HTTPError as exc:
            last_error = f"http_{int(exc.code)}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(0.5)
    return False, last_error


def _creationflags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))


def _start_permit_ephemeral(port: int) -> Tuple[subprocess.Popen[str], Dict[str, Any]]:
    PERMIT_STDOUT_LOG.parent.mkdir(parents=True, exist_ok=True)
    stdout_handle = PERMIT_STDOUT_LOG.open("a", encoding="utf-8")
    stderr_handle = PERMIT_STDERR_LOG.open("a", encoding="utf-8")
    cmd = [
        sys.executable,
        str(ROOT / "permit_precheck_api.py"),
        "--host",
        "127.0.0.1",
        "--port",
        str(int(port)),
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        stdout=stdout_handle,
        stderr=stderr_handle,
        text=True,
        creationflags=_creationflags(),
    )
    ok, error = _wait_health(f"http://127.0.0.1:{int(port)}/v1/health", timeout_sec=25)
    info = {
        "command": cmd,
        "pid": int(proc.pid),
        "base_url": f"http://127.0.0.1:{int(port)}",
        "stdout_log": str(PERMIT_STDOUT_LOG),
        "stderr_log": str(PERMIT_STDERR_LOG),
        "started_ok": bool(ok),
        "startup_error": str(error or ""),
    }
    if not ok:
        try:
            proc.terminate()
            proc.wait(timeout=8)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        stdout_handle.close()
        stderr_handle.close()
        raise RuntimeError(f"permit_precheck_api ephemeral start failed: {error or 'health_timeout'}")
    proc._partner_stdout_handle = stdout_handle  # type: ignore[attr-defined]
    proc._partner_stderr_handle = stderr_handle  # type: ignore[attr-defined]
    return proc, info


def _stop_process(proc: subprocess.Popen[str] | None) -> None:
    if proc is None:
        return
    try:
        if proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=8)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    finally:
        for attr in ("_partner_stdout_handle", "_partner_stderr_handle"):
            handle = getattr(proc, attr, None)
            if handle is not None:
                try:
                    handle.close()
                except Exception:
                    pass


def run_contract_smoke(*, report_path: Path | None = None) -> Dict[str, Any]:
    started_total = time.perf_counter()
    blackbox_key = _read_env_value("YANGDO_BLACKBOX_API_KEY")
    permit_key = _read_env_value("PERMIT_PRECHECK_API_KEY")
    out: Dict[str, Any] = {
        "generated_at": _now(),
        "ok": False,
        "report_path": str(Path(report_path or DEFAULT_REPORT).resolve()),
        "blocking_issues": [],
        "live_blackbox": {},
        "ephemeral_permit": {},
        "timing": {},
        "brainstorming": {
            "goal": "Validate the shared widget health contract against live blackbox and ephemeral permit endpoints before partner-facing changes go out.",
            "design": [
                "Use the real 8790 live blackbox response instead of a preview stub.",
                "Start permit_precheck_api on an ephemeral localhost port and run the same contract smoke there.",
                "Reuse run_partner_api_smoke so health_contract and business endpoint checks stay aligned.",
            ]
        },
    }

    out["live_blackbox"] = {
        "mode": "live",
        "base_url": "http://127.0.0.1:8790",
        "api_key_present": bool(blackbox_key),
    }
    started_live = time.perf_counter()
    live_result = run_smoke(
        base_url="http://127.0.0.1:8790",
        service="yangdo",
        api_key=blackbox_key,
        origin="https://seoulmna.kr",
        channel_id="seoul_web",
        timeout=20,
    )
    out["timing"]["live_blackbox_sec"] = round(time.perf_counter() - started_live, 3)
    out["live_blackbox"]["result"] = live_result
    out["live_blackbox"]["ok"] = bool(live_result.get("ok"))
    if not out["live_blackbox"]["ok"]:
        out["blocking_issues"].append("partner_live_blackbox_failed")

    proc: subprocess.Popen[str] | None = None
    try:
        permit_port = _pick_free_port()
        started_ephemeral_start = time.perf_counter()
        proc, startup = _start_permit_ephemeral(permit_port)
        out["timing"]["ephemeral_permit_start_sec"] = round(time.perf_counter() - started_ephemeral_start, 3)
        started_ephemeral_smoke = time.perf_counter()
        permit_result = run_smoke(
            base_url=str(startup.get("base_url") or ""),
            service="permit",
            api_key=permit_key,
            origin="https://seoulmna.kr",
            channel_id="seoul_web",
            timeout=20,
        )
        out["timing"]["ephemeral_permit_smoke_sec"] = round(time.perf_counter() - started_ephemeral_smoke, 3)
        out["ephemeral_permit"] = {
            "mode": "ephemeral",
            **startup,
            "api_key_present": bool(permit_key),
            "result": permit_result,
            "ok": bool(permit_result.get("ok")),
        }
        if not out["ephemeral_permit"]["ok"]:
            out["blocking_issues"].append("partner_ephemeral_permit_failed")
    except Exception as exc:  # noqa: BLE001
        out["ephemeral_permit"] = {
            "mode": "ephemeral",
            "ok": False,
            "startup_error": str(exc),
            "stdout_log": str(PERMIT_STDOUT_LOG),
            "stderr_log": str(PERMIT_STDERR_LOG),
        }
        out["blocking_issues"].append("partner_ephemeral_permit_failed")
    finally:
        _stop_process(proc)

    out["timing"]["total_duration_sec"] = round(time.perf_counter() - started_total, 3)
    out["ok"] = not out["blocking_issues"]
    final_path = Path(report_path or DEFAULT_REPORT).resolve()
    _save_json(final_path, out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Run partner API contract smoke against live blackbox and ephemeral permit endpoints")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()
    result = run_contract_smoke(report_path=Path(str(args.report)).resolve())
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    try:
        sys.stdout.write(rendered)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(rendered.encode("utf-8", errors="replace"))
    return 0 if bool(result.get("ok")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
