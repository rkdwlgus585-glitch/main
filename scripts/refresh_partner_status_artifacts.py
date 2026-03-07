#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
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


def _run(cmd: List[str], timeout_sec: int = 420) -> Dict[str, Any]:
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
    payload: Dict[str, Any] = {}
    try:
        parsed = json.loads(proc.stdout or "")
        payload = parsed if isinstance(parsed, dict) else {}
    except Exception:
        payload = {}
    return {
        "ok": proc.returncode == 0,
        "returncode": int(proc.returncode),
        "command": cmd,
        "json": payload,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }


def build_refresh_plan(*, offering_id: str, tenant_id: str, channel_id: str, host: str, brand_name: str, registry_path: str = "", channels_path: str = "", env_path: str = "", log_dir: str = "logs", include_simulation_matrix: bool = True) -> List[Dict[str, Any]]:
    registry_args: List[str] = ["--registry", registry_path] if registry_path else []
    channels_args: List[str] = ["--channels", channels_path] if channels_path else []
    env_args: List[str] = ["--env-file", env_path] if env_path else []
    log_root = str(log_dir or "logs").rstrip("\\/")
    plan: List[Dict[str, Any]] = [
        {
            "name": "partner_onboarding_flow",
            "command": _py_cmd(
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
                    "--report",
                    f"{log_root}/partner_onboarding_flow_latest.json",
                    *registry_args,
                    *channels_args,
                    *env_args,
                ]
            ),
        },
        {
            "name": "partner_activation_preview",
            "command": _py_cmd(
                [
                    "scripts/preview_partner_activation_matrix.py",
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
                    "--json",
                    f"{log_root}/partner_activation_preview_latest.json",
                    "--md",
                    f"{log_root}/partner_activation_preview_latest.md",
                    *registry_args,
                    *channels_args,
                    *env_args,
                ]
            ),
        },
        {
            "name": "partner_preview_alignment",
            "command": _py_cmd(
                [
                    "scripts/verify_partner_preview_alignment.py",
                    "--partner-flow",
                    f"{log_root}/partner_onboarding_flow_latest.json",
                    "--partner-preview",
                    f"{log_root}/partner_activation_preview_latest.json",
                    "--json",
                    f"{log_root}/partner_preview_alignment_latest.json",
                    "--md",
                    f"{log_root}/partner_preview_alignment_latest.md",
                ]
            ),
        },
        {
            "name": "partner_activation_resolution",
            "command": _py_cmd(
                [
                    "scripts/verify_partner_activation_resolution.py",
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
                    "--json",
                    f"{log_root}/partner_activation_resolution_latest.json",
                    "--md",
                    f"{log_root}/partner_activation_resolution_latest.md",
                    *registry_args,
                    *channels_args,
                    *env_args,
                ]
            ),
        },
        {
            "name": "partner_input_snapshot",
            "command": _py_cmd(
                [
                    "scripts/generate_partner_input_snapshot.py",
                    *registry_args,
                    *channels_args,
                    *env_args,
                    "--json",
                    f"{log_root}/partner_input_snapshot_latest.json",
                    "--md",
                    f"{log_root}/partner_input_snapshot_latest.md",
                ]
            ),
        },
    ]
    if include_simulation_matrix:
        plan.append(
            {
                "name": "partner_activation_simulation_matrix",
                "command": _py_cmd(
                    [
                        "scripts/generate_partner_activation_simulation_matrix.py",
                        *registry_args,
                        *channels_args,
                        *env_args,
                        "--json",
                        f"{log_root}/partner_activation_simulation_matrix_latest.json",
                        "--md",
                        f"{log_root}/partner_activation_simulation_matrix_latest.md",
                    ]
                ),
            }
        )
    operations_command = [
        "scripts/generate_operations_packet.py",
        "--partner-flow",
        f"{log_root}/partner_onboarding_flow_latest.json",
        "--partner-preview",
        f"{log_root}/partner_activation_preview_latest.json",
        "--partner-preview-alignment",
        f"{log_root}/partner_preview_alignment_latest.json",
        "--partner-resolution",
        f"{log_root}/partner_activation_resolution_latest.json",
        "--partner-input-snapshot",
        f"{log_root}/partner_input_snapshot_latest.json",
    ]
    if include_simulation_matrix:
        operations_command.extend(
            [
                "--partner-simulation-matrix",
                f"{log_root}/partner_activation_simulation_matrix_latest.json",
            ]
        )
    operations_command.extend(
        [
            "--json",
            f"{log_root}/operations_packet_latest.json",
            "--md",
            f"{log_root}/operations_packet_latest.md",
        ]
    )
    plan.append(
        {
            "name": "operations_packet",
            "command": _py_cmd(
                operations_command
            ),
        }
    )
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh partner onboarding artifacts in dependency order")
    parser.add_argument("--offering-id", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--brand-name", required=True)
    parser.add_argument("--registry", default="")
    parser.add_argument("--channels", default="")
    parser.add_argument("--env-file", default="")
    parser.add_argument("--log-dir", default="logs")
    parser.add_argument("--skip-simulation-matrix", action="store_true")
    args = parser.parse_args()

    steps: List[Dict[str, Any]] = []
    exit_code = 0
    partner_flow_ok = True
    for step in build_refresh_plan(
        offering_id=str(args.offering_id),
        tenant_id=str(args.tenant_id),
        channel_id=str(args.channel_id),
        host=str(args.host),
        brand_name=str(args.brand_name),
            registry_path=str(args.registry),
            channels_path=str(args.channels),
            env_path=str(args.env_file),
            log_dir=str(args.log_dir),
            include_simulation_matrix=not bool(args.skip_simulation_matrix),
        ):
        result = _run(step["command"])
        steps.append({"name": step["name"], **result})
        if not result["ok"] and step["name"] != "partner_onboarding_flow":
            exit_code = result["returncode"] or 1
            break
        if not result["ok"] and step["name"] == "partner_onboarding_flow":
            partner_flow_ok = False

    operations_packet = {}
    operations_path = (ROOT / str(args.log_dir) / "operations_packet_latest.json").resolve()
    if operations_path.exists():
        try:
            parsed = json.loads(operations_path.read_text(encoding="utf-8"))
            operations_packet = parsed if isinstance(parsed, dict) else {}
        except Exception:
            operations_packet = {}

    summary = {
        "ok": exit_code == 0,
        "step_count": len(steps),
        "partner_flow_ok": partner_flow_ok,
        "seoul_live_decision": ((operations_packet.get("decisions") or {}).get("seoul_live_decision")),
        "partner_activation_decision": ((operations_packet.get("decisions") or {}).get("partner_activation_decision")),
        "partner_preview_alignment_ok": ((operations_packet.get("decisions") or {}).get("partner_preview_alignment_ok")),
        "partner_resolution_ok": ((operations_packet.get("decisions") or {}).get("partner_resolution_ok")),
        "partner_resolution_actionable": ((operations_packet.get("decisions") or {}).get("partner_resolution_actionable")),
    }
    print(json.dumps({"ok": exit_code == 0, "steps": steps, "summary": summary}, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
