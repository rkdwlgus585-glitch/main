#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_VALIDATION = ROOT / "logs" / "wp_surface_lab_runtime_validation_latest.json"
DEFAULT_PHP_FALLBACK = ROOT / "logs" / "wp_surface_lab_php_fallback_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _run(command: List[str], *, cwd: Path | None = None) -> Dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": " ".join(command),
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _probe_runtime_validation(runtime_validation_path: Path) -> Dict[str, Any]:
    payload = _load_json(runtime_validation_path)
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    handoff = payload.get("handoff") if isinstance(payload.get("handoff"), dict) else {}
    return {
        "runtime_ready": bool(summary.get("runtime_ready")),
        "runtime_running": bool(summary.get("runtime_running")),
        "runtime_mode": str(summary.get("runtime_mode") or "none"),
        "localhost_url": str(handoff.get("localhost_url") or ""),
        "blockers": list(summary.get("blockers") or []),
    }


def _probe_localhost(url: str) -> Dict[str, Any]:
    url = str(url or "").strip()
    if not url:
        return {"ok": False, "status": 0, "error": "missing_localhost_url"}
    last_result: Dict[str, Any] = {"ok": False, "status": 0}
    for attempt in range(4):
        try:
            with urlopen(url, timeout=8) as response:
                return {
                    "ok": True,
                    "status": int(getattr(response, "status", 200) or 200),
                }
        except HTTPError as exc:
            last_result = {"ok": False, "status": int(exc.code)}
            if exc.code < 500 or attempt == 3:
                return last_result
        except Exception as exc:
            last_result = {"ok": False, "status": 0, "error": str(exc)}
            if attempt == 3:
                return last_result
        time.sleep(0.8 * (attempt + 1))
    return last_result


def _reconcile_runtime_probe(runtime_probe: Dict[str, Any], verify_payload: Dict[str, Any]) -> Dict[str, Any]:
    reconciled = dict(runtime_probe)
    verify_summary = verify_payload.get("summary") if isinstance(verify_payload.get("summary"), dict) else {}
    page_checks = verify_payload.get("page_checks") if isinstance(verify_payload.get("page_checks"), list) else []
    if bool(reconciled.get("runtime_running")):
        reconciled["runtime_running_source"] = "runtime_validation"
        return reconciled

    if bool(verify_summary.get("verification_ok")) and any(bool(row.get("reachable")) for row in page_checks if isinstance(row, dict)):
        reconciled["runtime_running"] = True
        reconciled["runtime_running_source"] = "page_verification"
        return reconciled

    localhost_url = str(reconciled.get("localhost_url") or "").strip()
    if localhost_url:
        live_probe = _probe_localhost(localhost_url)
        reconciled["live_probe"] = live_probe
        if bool(live_probe.get("ok")):
            reconciled["runtime_running"] = True
            reconciled["runtime_running_source"] = "cycle_localhost_probe"
            return reconciled

    reconciled["runtime_running_source"] = "runtime_validation"
    return reconciled


def build_cycle_payload(
    *,
    runtime_probe_before: Dict[str, Any],
    runtime_probe_after: Dict[str, Any],
    apply_payload: Dict[str, Any],
    verify_payload: Dict[str, Any],
    steps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    runtime_effective_after = _reconcile_runtime_probe(runtime_probe_after, verify_payload)
    verify_summary = verify_payload.get("summary") if isinstance(verify_payload.get("summary"), dict) else {}
    apply_result = apply_payload.get("apply_result") if isinstance(apply_payload.get("apply_result"), dict) else {}
    apply_step = next((row for row in steps if row.get("name") == "apply_blueprints"), {})
    blockers: List[str] = []
    if not runtime_effective_after.get("runtime_ready"):
        blockers.append("runtime_not_ready")
    if not runtime_effective_after.get("runtime_running"):
        blockers.append("runtime_not_running")
    if apply_step and not apply_step.get("ok"):
        blockers.append("apply_execution_failed")
    if not apply_result.get("ok"):
        blockers.extend([str(x) for x in apply_result.get("blockers") or []])
    if not verify_summary.get("verification_ok"):
        blockers.extend([str(x) for x in verify_summary.get("blockers") or []])
    deduped: List[str] = []
    for item in blockers:
        if item and item not in deduped:
            deduped.append(item)
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "ok": not deduped,
            "runtime_mode": runtime_effective_after.get("runtime_mode") or runtime_probe_before.get("runtime_mode") or "none",
            "runtime_running_before": bool(runtime_probe_before.get("runtime_running")),
            "runtime_running_after": bool(runtime_effective_after.get("runtime_running")),
            "runtime_running_source": str(runtime_effective_after.get("runtime_running_source") or "runtime_validation"),
            "apply_ok": bool(apply_step.get("ok", True)) and bool(apply_result.get("ok")),
            "apply_step_ok": bool(apply_step.get("ok", True)),
            "verification_ok": bool(verify_summary.get("verification_ok")),
            "blockers": deduped,
            "step_count": len(steps),
        },
        "runtime": {
            "before": runtime_probe_before,
            "after": runtime_effective_after,
        },
        "steps": steps,
        "apply": apply_payload,
        "verify": verify_payload,
        "next_actions": (
            ["Runtime/apply/verify cycle is green. Regenerate operations packet only when live inputs change."]
            if not deduped
            else [
                "Inspect the failed step logs in this cycle output.",
                "Keep the php fallback runtime on 127.0.0.1 only.",
                "Rerun the cycle after clearing the blockers.",
            ]
        ),
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# WordPress Surface Lab Apply Verify Cycle",
        "",
        f"- ok: {summary.get('ok')}",
        f"- runtime_mode: {summary.get('runtime_mode')}",
        f"- runtime_running_before: {summary.get('runtime_running_before')}",
        f"- runtime_running_after: {summary.get('runtime_running_after')}",
        f"- apply_ok: {summary.get('apply_ok')}",
        f"- verification_ok: {summary.get('verification_ok')}",
        f"- blockers: {', '.join(summary.get('blockers') or []) or '(none)'}",
        "",
        "## Steps",
    ]
    for step in payload.get("steps", []):
        lines.append(f"- {step.get('name')}: ok={step.get('ok')} command={step.get('command')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local WordPress lab cycle: runtime start -> apply -> verify -> packet refresh.")
    parser.add_argument("--runtime-validation", type=Path, default=DEFAULT_RUNTIME_VALIDATION)
    parser.add_argument("--php-fallback", type=Path, default=DEFAULT_PHP_FALLBACK)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wp_surface_lab_apply_verify_cycle_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wp_surface_lab_apply_verify_cycle_latest.md")
    parser.add_argument("--skip-apply", action="store_true")
    args = parser.parse_args()

    steps: List[Dict[str, Any]] = []
    runtime_before = _probe_runtime_validation(args.runtime_validation)

    if runtime_before.get("runtime_mode") == "php_fallback" and not runtime_before.get("runtime_running"):
        php_fallback = _load_json(args.php_fallback)
        start_script = str(((php_fallback.get("paths") or {}).get("start_script")) or "").strip()
        if start_script:
            step = _run(["powershell", "-ExecutionPolicy", "Bypass", "-File", start_script])
            step["name"] = "start_php_fallback"
            steps.append(step)
            time.sleep(2.0)

    step = _run([sys.executable, str(ROOT / "scripts" / "validate_wp_surface_lab_runtime.py")])
    step["name"] = "validate_runtime"
    steps.append(step)
    runtime_after = _probe_runtime_validation(args.runtime_validation)

    if args.skip_apply:
        apply_payload = _load_json(ROOT / "logs" / "wp_surface_lab_apply_latest.json")
    else:
        step = _run([sys.executable, str(ROOT / "scripts" / "apply_wp_surface_lab_blueprints.py"), "--apply"])
        step["name"] = "apply_blueprints"
        steps.append(step)
        apply_payload = _load_json(ROOT / "logs" / "wp_surface_lab_apply_latest.json")

    step = _run([sys.executable, str(ROOT / "scripts" / "verify_wp_surface_lab_pages.py")])
    step["name"] = "verify_pages"
    steps.append(step)
    verify_payload = _load_json(ROOT / "logs" / "wp_surface_lab_page_verify_latest.json")

    for name in ("generate_program_improvement_loop.py", "generate_operations_packet.py"):
        step = _run([sys.executable, str(ROOT / "scripts" / name)])
        step["name"] = name.replace(".py", "")
        steps.append(step)

    payload = build_cycle_payload(
        runtime_probe_before=runtime_before,
        runtime_probe_after=runtime_after,
        apply_payload=apply_payload,
        verify_payload=verify_payload,
        steps=steps,
    )

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if payload.get("summary", {}).get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
