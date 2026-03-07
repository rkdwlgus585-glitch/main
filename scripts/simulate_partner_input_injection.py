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

from scripts.validate_tenant_onboarding import _load_env_file, _load_json


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
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
        "json": payload,
    }


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        dst.write_text("", encoding="utf-8")


def _update_env_file(path: Path, env_name: str, env_value: str) -> None:
    lines: List[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    updated = False
    out: List[str] = []
    for line in lines:
        raw = str(line or "")
        stripped = raw.strip()
        if stripped and not stripped.startswith("#") and "=" in raw:
            key = raw.split("=", 1)[0].strip().lstrip("\ufeff")
            if key == env_name:
                out.append(f"{env_name}={env_value}")
                updated = True
                continue
        out.append(raw)
    if not updated:
        out.append(f"{env_name}={env_value}")
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _inject_partner_inputs(*, registry_path: Path, env_path: Path, tenant_id: str, proof_url: str, api_key_value: str, approve_source: bool) -> Dict[str, Any]:
    registry = _load_json(registry_path)
    tenants = registry.get("tenants") if isinstance(registry.get("tenants"), list) else []
    target = next(
        (
            row for row in tenants
            if isinstance(row, dict) and str(row.get("tenant_id") or "").strip().lower() == str(tenant_id or "").strip().lower()
        ),
        {},
    )
    if not target:
        return {"ok": False, "error": "tenant_not_found", "tenant_id": tenant_id}

    source_updated = False
    if proof_url or approve_source:
        sources = target.get("data_sources") if isinstance(target.get("data_sources"), list) else []
        for src in sources:
            if not isinstance(src, dict):
                continue
            access_mode = str(src.get("access_mode") or "").strip().lower()
            if access_mode != "partner_contract":
                continue
            if proof_url:
                src["proof_url"] = proof_url
            if approve_source:
                src["status"] = "approved"
                src["allows_commercial_use"] = True
            source_updated = True
            break

    api_key_env = ""
    if api_key_value:
        envs = target.get("api_key_envs") if isinstance(target.get("api_key_envs"), list) else []
        if envs:
            api_key_env = str(envs[0] or "").strip()
            if api_key_env:
                _update_env_file(env_path, api_key_env, api_key_value)

    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "tenant_id": tenant_id,
        "proof_url_injected": bool(proof_url) and source_updated,
        "approval_injected": bool(approve_source) and source_updated,
        "api_key_env": api_key_env,
        "api_key_injected": bool(api_key_value and api_key_env),
    }


def _load_packet(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    payload = _load_json(path)
    return payload if isinstance(payload, dict) else {}


def build_simulation_report(*, offering_id: str, tenant_id: str, channel_id: str, host: str, brand_name: str, proof_url: str, api_key_value: str, approve_source: bool, registry_path: Path, channels_path: Path, env_path: Path) -> Dict[str, Any]:
    current_packet = _load_packet(ROOT / "logs" / "operations_packet_latest.json")
    current_snapshot = _load_json(ROOT / "logs" / "partner_input_snapshot_latest.json")

    with tempfile.TemporaryDirectory(prefix="partner_input_simulation_") as td:
        temp_root = Path(td)
        temp_registry = temp_root / "tenant_registry.json"
        temp_channels = temp_root / "channel_profiles.json"
        temp_env = temp_root / ".env"
        temp_logs = temp_root / "logs"
        temp_logs.mkdir(parents=True, exist_ok=True)
        _copy_if_exists(registry_path, temp_registry)
        _copy_if_exists(channels_path, temp_channels)
        _copy_if_exists(env_path, temp_env)

        injection = _inject_partner_inputs(
            registry_path=temp_registry,
            env_path=temp_env,
            tenant_id=tenant_id,
            proof_url=proof_url,
            api_key_value=api_key_value,
            approve_source=approve_source,
        )
        if not injection.get("ok"):
            return {
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ok": False,
                "error": injection.get("error"),
                "tenant_id": tenant_id,
            }

        refresh = _run(
            _py_cmd(
                [
                    "scripts/refresh_partner_status_artifacts.py",
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
                    "--registry",
                    str(temp_registry),
                    "--channels",
                    str(temp_channels),
                    "--env-file",
                    str(temp_env),
                    "--log-dir",
                    str(temp_logs),
                    "--skip-simulation-matrix",
                ]
            ),
            timeout_sec=420,
        )

        simulated_packet = _load_packet(temp_logs / "operations_packet_latest.json")
        simulated_snapshot = _load_json(temp_logs / "partner_input_snapshot_latest.json")

    current_partner = ((current_packet.get("summaries") or {}).get("partner") or {}) if isinstance((current_packet.get("summaries") or {}).get("partner"), dict) else {}
    simulated_partner = ((simulated_packet.get("summaries") or {}).get("partner") or {}) if isinstance((simulated_packet.get("summaries") or {}).get("partner"), dict) else {}
    current_remaining = _as_list(current_partner.get("latest_flow_remaining_required_inputs"))
    simulated_remaining = _as_list(simulated_partner.get("latest_flow_remaining_required_inputs"))
    removed = [item for item in current_remaining if item not in simulated_remaining]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": bool(simulated_packet),
        "scope": {
            "offering_id": offering_id,
            "tenant_id": tenant_id,
            "channel_id": channel_id,
            "host": host,
            "brand_name": brand_name,
        },
        "injection": injection,
        "refresh_summary": refresh.get("json", {}).get("summary") if isinstance(refresh.get("json"), dict) else {},
        "current": {
            "partner_activation_decision": (current_packet.get("decisions") or {}).get("partner_activation_decision"),
            "remaining_required_inputs": current_remaining,
            "input_snapshot_summary": current_snapshot.get("summary") if isinstance(current_snapshot.get("summary"), dict) else {},
        },
        "simulated": {
            "partner_activation_decision": (simulated_packet.get("decisions") or {}).get("partner_activation_decision"),
            "remaining_required_inputs": simulated_remaining,
            "preview_alignment_ok": (simulated_packet.get("decisions") or {}).get("partner_preview_alignment_ok"),
            "resolution_ok": (simulated_packet.get("decisions") or {}).get("partner_resolution_ok"),
            "input_snapshot_summary": simulated_snapshot.get("summary") if isinstance(simulated_snapshot.get("summary"), dict) else {},
        },
        "delta": {
            "removed_required_inputs": removed,
            "current_required_count": len(current_remaining),
            "simulated_required_count": len(simulated_remaining),
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    current = payload.get("current") if isinstance(payload.get("current"), dict) else {}
    simulated = payload.get("simulated") if isinstance(payload.get("simulated"), dict) else {}
    delta = payload.get("delta") if isinstance(payload.get("delta"), dict) else {}
    injection = payload.get("injection") if isinstance(payload.get("injection"), dict) else {}
    lines = [
        "# Partner Input Injection Simulation",
        "",
        f"- tenant_id: {(payload.get('scope') or {}).get('tenant_id')}",
        f"- current_decision: {current.get('partner_activation_decision')}",
        f"- simulated_decision: {simulated.get('partner_activation_decision')}",
        "",
        "## Injected Inputs",
        f"- proof_url_injected: {injection.get('proof_url_injected')}",
        f"- api_key_injected: {injection.get('api_key_injected')}",
        f"- approval_injected: {injection.get('approval_injected')}",
        "",
        "## Required Inputs Delta",
        f"- current_remaining_required_inputs: {', '.join(current.get('remaining_required_inputs') or []) or '(none)'}",
        f"- simulated_remaining_required_inputs: {', '.join(simulated.get('remaining_required_inputs') or []) or '(none)'}",
        f"- removed_required_inputs: {', '.join(delta.get('removed_required_inputs') or []) or '(none)'}",
        "",
        "## Simulated Consistency",
        f"- preview_alignment_ok: {simulated.get('preview_alignment_ok')}",
        f"- resolution_ok: {simulated.get('resolution_ok')}",
    ]
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate injecting partner inputs into temp registry/env and compare resulting partner artifacts")
    parser.add_argument("--offering-id", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--brand-name", required=True)
    parser.add_argument("--proof-url", default="")
    parser.add_argument("--api-key-value", default="")
    parser.add_argument("--approve-source", action="store_true", default=False)
    parser.add_argument("--registry", default=str(ROOT / "tenant_config" / "tenant_registry.json"))
    parser.add_argument("--channels", default=str(ROOT / "tenant_config" / "channel_profiles.json"))
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument("--json", default="logs/partner_input_injection_simulation_latest.json")
    parser.add_argument("--md", default="logs/partner_input_injection_simulation_latest.md")
    args = parser.parse_args()

    payload = build_simulation_report(
        offering_id=str(args.offering_id),
        tenant_id=str(args.tenant_id),
        channel_id=str(args.channel_id),
        host=str(args.host),
        brand_name=str(args.brand_name),
        proof_url=str(args.proof_url),
        api_key_value=str(args.api_key_value),
        approve_source=bool(args.approve_source),
        registry_path=Path(str(args.registry)).resolve(),
        channels_path=Path(str(args.channels)).resolve(),
        env_path=Path(str(args.env_file)).resolve(),
    )

    json_path = (ROOT / str(args.json)).resolve()
    md_path = (ROOT / str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": bool(payload.get("ok")), "json": str(json_path), "md": str(md_path)}, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
