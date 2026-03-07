#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _py_cmd(args: List[str]) -> List[str]:
    py = shutil.which("py")
    if py:
        return [py, "-3", *args]
    return [sys.executable, *args]


def _run_flow(cmd: List[str], timeout_sec: int = 420) -> Dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    stdout_text = proc.stdout or ""
    parsed: Dict[str, Any] | None = None
    try:
        parsed = json.loads(stdout_text) if stdout_text.strip() else None
    except Exception:
        parsed = None
    return {
        "ok": proc.returncode == 0,
        "returncode": int(proc.returncode),
        "stdout": stdout_text,
        "stderr": proc.stderr or "",
        "json": parsed if isinstance(parsed, dict) else {},
    }


def _scenario_cmd(
    *,
    offering_id: str,
    tenant_id: str,
    channel_id: str,
    host: str,
    brand_name: str,
    proof_url: str = "",
    api_key_value: str = "",
    approve_source: bool = False,
    smoke: bool = False,
    smoke_base_url: str = "",
    report_path: str = "",
    registry_path: str = "",
    channels_path: str = "",
    env_path: str = "",
) -> List[str]:
    cmd = _py_cmd(
        [
            "scripts/run_partner_onboarding_flow.py",
            "--offering-id",
            offering_id,
            "--tenant-id",
            tenant_id,
            "--channel-id",
            channel_id,
            "--host",
            host,
            "--brand-name",
            brand_name,
        ]
    )
    if proof_url:
        cmd.extend(["--proof-url", proof_url])
    if api_key_value:
        cmd.extend(["--api-key-value", api_key_value])
    if approve_source:
        cmd.append("--approve-source")
    if smoke_base_url:
        cmd.extend(["--smoke-base-url", smoke_base_url])
    if smoke:
        cmd.append("--run-smoke-in-dry-run")
    if report_path:
        cmd.extend(["--report", report_path])
    if registry_path:
        cmd.extend(["--registry", registry_path])
    if channels_path:
        cmd.extend(["--channels", channels_path])
    if env_path:
        cmd.extend(["--env-file", env_path])
    return cmd


def _extract_summary(name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    payload = result.get("json") if isinstance(result.get("json"), dict) else {}
    steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
    activation_step_found = any(isinstance(row, dict) and str(row.get("name") or "").strip() == "activate_partner_tenant" for row in steps)
    handoff = payload.get("handoff") if isinstance(payload.get("handoff"), dict) else {}
    blockers = [str(x) for x in (payload.get("activation_blockers") or []) if str(x).strip()]
    if (not activation_step_found) and (not blockers) and (not result.get("ok")):
        blockers = ["flow_terminated_before_activation"]
    remaining = [str(x) for x in (handoff.get("remaining_required_inputs") or []) if str(x).strip()]
    resolved = [str(x) for x in (handoff.get("resolved_inputs") or []) if str(x).strip()]
    return {
        "scenario": name,
        "ok": bool(payload.get("ok")),
        "activation_ready": bool(handoff.get("activation_ready")) and activation_step_found,
        "activation_step_found": activation_step_found,
        "remaining_required_inputs": remaining,
        "resolved_inputs": resolved,
        "blocker_count": len(blockers),
        "blockers": blockers,
        "next_actions": [str(x) for x in (handoff.get("next_actions") or []) if str(x).strip()],
    }


def build_preview_matrix(
    *,
    offering_id: str,
    tenant_id: str,
    channel_id: str,
    host: str,
    brand_name: str,
    proof_url: str,
    api_key_value: str,
    smoke_base_url: str,
    registry_path: str = "",
    channels_path: str = "",
    env_path: str = "",
) -> Dict[str, Any]:
    scenarios = [
        {
            "name": "baseline",
            "proof_url": "",
            "api_key_value": "",
            "approve_source": False,
            "smoke": False,
        },
        {
            "name": "proof_only",
            "proof_url": proof_url,
            "api_key_value": "",
            "approve_source": False,
            "smoke": False,
        },
        {
            "name": "proof_and_key",
            "proof_url": proof_url,
            "api_key_value": api_key_value,
            "approve_source": False,
            "smoke": False,
        },
        {
            "name": "proof_key_and_approval",
            "proof_url": proof_url,
            "api_key_value": api_key_value,
            "approve_source": True,
            "smoke": False,
        },
    ]
    if smoke_base_url:
        scenarios.append(
            {
                "name": "proof_key_approval_and_smoke",
                "proof_url": proof_url,
                "api_key_value": api_key_value,
                "approve_source": True,
                "smoke": True,
            }
        )

    results: List[Dict[str, Any]] = []
    previous_remaining: List[str] = []
    for spec in scenarios:
        with tempfile.TemporaryDirectory(prefix="partner_preview_") as td:
            report_path = str((Path(td) / f"{spec['name']}.json").resolve())
            cmd = _scenario_cmd(
                offering_id=offering_id,
                tenant_id=tenant_id,
                channel_id=channel_id,
                host=host,
                brand_name=brand_name,
                proof_url=str(spec.get("proof_url") or ""),
                api_key_value=str(spec.get("api_key_value") or ""),
                approve_source=bool(spec.get("approve_source")),
                smoke=bool(spec.get("smoke")),
                smoke_base_url=smoke_base_url,
                report_path=report_path,
                registry_path=registry_path,
                channels_path=channels_path,
                env_path=env_path,
            )
            result = _run_flow(cmd)
            summary = _extract_summary(str(spec["name"]), result)
            current_remaining = list(summary.get("remaining_required_inputs") or [])
            summary["removed_inputs_since_previous"] = [x for x in previous_remaining if x not in current_remaining]
            previous_remaining = current_remaining
            results.append(summary)

    best = min(results, key=lambda item: (len(item.get("remaining_required_inputs") or []), item.get("blocker_count", 0)))
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "offering_id": offering_id,
        "tenant_id": tenant_id,
        "channel_id": channel_id,
        "host": host,
        "scenarios": results,
        "recommended_path": {
            "scenario": best.get("scenario"),
            "remaining_required_inputs": best.get("remaining_required_inputs") or [],
            "next_actions": best.get("next_actions") or [],
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Partner Activation Preview")
    lines.append("")
    lines.append(f"- offering_id: {payload.get('offering_id')}")
    lines.append(f"- tenant_id: {payload.get('tenant_id')}")
    lines.append(f"- channel_id: {payload.get('channel_id')}")
    lines.append(f"- host: {payload.get('host')}")
    lines.append("")
    lines.append("## Scenarios")
    for row in payload.get("scenarios") or []:
        lines.append(
            f"- {row.get('scenario')}: ready={row.get('activation_ready')} "
            f"remaining={', '.join(row.get('remaining_required_inputs') or []) or '(none)'} "
            f"removed={', '.join(row.get('removed_inputs_since_previous') or []) or '(none)'}"
        )
    lines.append("")
    lines.append("## Recommended Path")
    recommended = payload.get("recommended_path") if isinstance(payload.get("recommended_path"), dict) else {}
    lines.append(f"- scenario: {recommended.get('scenario')}")
    lines.append(f"- remaining_required_inputs: {', '.join(recommended.get('remaining_required_inputs') or []) or '(none)'}")
    for item in recommended.get("next_actions") or []:
        lines.append(f"- next_action: {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview which partner onboarding inputs remove which blockers")
    parser.add_argument("--offering-id", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--brand-name", required=True)
    parser.add_argument("--proof-url", default="https://example.com/partner-contract")
    parser.add_argument("--api-key-value", default="preview-test-key")
    parser.add_argument("--smoke-base-url", default="")
    parser.add_argument("--registry", default="")
    parser.add_argument("--channels", default="")
    parser.add_argument("--env-file", default="")
    parser.add_argument("--json", default="logs/partner_activation_preview_latest.json")
    parser.add_argument("--md", default="logs/partner_activation_preview_latest.md")
    args = parser.parse_args()

    payload = build_preview_matrix(
        offering_id=str(args.offering_id),
        tenant_id=str(args.tenant_id),
        channel_id=str(args.channel_id),
        host=str(args.host),
        brand_name=str(args.brand_name),
        proof_url=str(args.proof_url),
        api_key_value=str(args.api_key_value),
        smoke_base_url=str(args.smoke_base_url),
        registry_path=str(args.registry),
        channels_path=str(args.channels),
        env_path=str(args.env_file),
    )

    json_path = (ROOT / str(args.json)).resolve()
    md_path = (ROOT / str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_path), "md": str(md_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
