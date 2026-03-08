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
VERIFY_RUNTIME_REPORT = LOG_DIR / "verify_calculator_runtime_latest.json"
DEFAULT_REPORT = LOG_DIR / "public_calculator_post_publish_verify_latest.json"


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


def _trim(text: str, limit: int = 1600) -> str:
    value = str(text or "")
    if len(value) <= limit:
        return value
    head = max(250, limit // 2)
    return value[:head] + "\n... [trimmed] ...\n" + value[-head:]


def _select_checks(checks: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    picked: Dict[str, Dict[str, Any]] = {}
    for row in checks:
        url = str(row.get("url") or "")
        kind = str(row.get("kind") or "")
        mode = str(row.get("mode") or "")
        if url.endswith("/yangdo-ai-customer/"):
            key = f"customer_{kind}"
        elif url.endswith("/ai-license-acquisition-calculator/"):
            key = f"permit_{kind}"
        else:
            continue
        if kind == "interaction" and mode:
            key = f"{key}_{mode}"
        picked[key] = {
            "ok": bool(row.get("ok")),
            "url": url,
            "kind": kind,
            "mode": mode,
            "status_code": int(row.get("status_code") or 0) if row.get("status_code") is not None else 0,
            "length": int(row.get("length") or 0) if row.get("length") is not None else 0,
            "error": str(row.get("error") or ""),
            "preflight": dict(row.get("preflight") or {}) if isinstance(row.get("preflight"), dict) else {},
        }
    return picked


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify live public SeoulMNA calculator pages immediately after deploy.")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--customer-url", default="https://seoulmna.kr/yangdo-ai-customer/")
    parser.add_argument("--permit-url", default="https://seoulmna.kr/ai-license-acquisition-calculator/")
    args = parser.parse_args()

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "verify_calculator_runtime.py"),
        "--kr-only",
        "--kr-customer-url",
        str(args.customer_url),
        "--kr-acquisition-url",
        str(args.permit_url),
        "--report",
        str(VERIFY_RUNTIME_REPORT),
    ]
    run = _run(cmd, timeout=1800)
    verify = _load_json(VERIFY_RUNTIME_REPORT)
    checks = list(verify.get("checks") or []) if isinstance(verify.get("checks"), list) else []
    selected = _select_checks([row for row in checks if isinstance(row, dict)])
    blocking_issues: List[str] = []
    if not bool(run.get("ok")):
        blocking_issues.append("verify_runtime_command_failed")
    if not bool(verify.get("ok")):
        blocking_issues.append("verify_runtime_report_failed")
    for name, row in selected.items():
        if not bool(row.get("ok")):
            blocking_issues.append(f"{name}_failed")

    report: Dict[str, Any] = {
        "generated_at": _now(),
        "ok": not blocking_issues,
        "blocking_issues": blocking_issues,
        "command": cmd,
        "command_ok": bool(run.get("ok")),
        "command_returncode": int(run.get("returncode") or 0),
        "stdout_preview": _trim(str(run.get("stdout") or "")),
        "stderr_preview": _trim(str(run.get("stderr") or "")),
        "verify_report_path": str(VERIFY_RUNTIME_REPORT),
        "health_contract": dict(verify.get("health_contract") or {}),
        "selected_checks": selected,
        "brainstorming": {
            "goal": "public deploy 직후 live URL이 실제로 살아 있는지, permit/customer 양쪽을 같은 계약으로 즉시 검증",
            "design": [
                "public deploy 성공과 public runtime 정상은 별개로 본다",
                "post-publish 검증은 기존 verify_calculator_runtime 결과를 재사용해 중복 구현을 피한다",
                "운영자에게는 customer/permit 핵심 체크만 축약해서 보여준다",
            ],
        },
    }
    _save_json(Path(str(args.report)).resolve(), report)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    try:
        sys.stdout.write(rendered)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(rendered.encode("utf-8", errors="replace"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
