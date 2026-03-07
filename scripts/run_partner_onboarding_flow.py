#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
    stdout_text = proc.stdout or ""
    stderr_text = proc.stderr or ""
    parsed: Dict[str, Any] | None = None
    try:
        parsed = json.loads(stdout_text) if stdout_text.strip() else None
    except Exception:
        parsed = None
    return {
        "ok": proc.returncode == 0,
        "returncode": int(proc.returncode),
        "command": cmd,
        "stdout": stdout_text,
        "stderr": stderr_text,
        "stdout_tail": "\n".join(stdout_text.splitlines()[-80:]),
        "stderr_tail": "\n".join(stderr_text.splitlines()[-80:]),
        "json": parsed,
    }


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        dst.write_text("", encoding="utf-8")


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item or "").strip().lower()
        if text and text not in out:
            out.append(text)
    return out


def _systems_from_offering_json(payload: Dict[str, Any] | None) -> List[str]:
    if not isinstance(payload, dict):
        return []
    tenant = payload.get("tenant") if isinstance(payload.get("tenant"), dict) else {}
    systems = tenant.get("allowed_systems") if isinstance(tenant, dict) else []
    return [str(x or "").strip().lower() for x in (systems or []) if str(x or "").strip()]


def _load_offering_systems(registry_path: str, offering_id: str) -> List[str]:
    registry = _load_json(Path(str(registry_path)).resolve())
    rows = registry.get("offering_templates") if isinstance(registry.get("offering_templates"), list) else []
    wanted = str(offering_id or "").strip().lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("offering_id") or "").strip().lower() != wanted:
            continue
        return _as_list(row.get("allowed_systems"))
    return []


def _can_reuse_existing_scope(*, registry_path: str, channels_path: str, tenant_id: str, channel_id: str, host: str, offering_id: str) -> bool:
    registry = _load_json(Path(str(registry_path)).resolve())
    channel_registry = _load_json(Path(str(channels_path)).resolve())
    tenants = registry.get("tenants") if isinstance(registry.get("tenants"), list) else []
    channels = channel_registry.get("channels") if isinstance(channel_registry.get("channels"), list) else []
    wanted_tenant = str(tenant_id or "").strip().lower()
    wanted_channel = str(channel_id or "").strip().lower()
    wanted_host = str(host or "").strip().lower()

    tenant = next(
        (
            row for row in tenants
            if isinstance(row, dict) and str(row.get("tenant_id") or "").strip().lower() == wanted_tenant
        ),
        {},
    )
    channel = next(
        (
            row for row in channels
            if isinstance(row, dict) and str(row.get("channel_id") or "").strip().lower() == wanted_channel
        ),
        {},
    )
    if not tenant or not channel:
        return False
    if str(channel.get("default_tenant_id") or "").strip().lower() != wanted_tenant:
        return False
    channel_hosts = _as_list(channel.get("channel_hosts"))
    if wanted_host and wanted_host not in channel_hosts:
        return False
    requested_systems = sorted(_load_offering_systems(registry_path, offering_id))
    tenant_systems = sorted(_as_list(tenant.get("allowed_systems")))
    channel_systems = sorted(_as_list(channel.get("exposed_systems")))
    if requested_systems and tenant_systems != requested_systems:
        return False
    if requested_systems and channel_systems and channel_systems != requested_systems:
        return False
    return True


def _is_reusable_scaffold_conflict(*, payload: Dict[str, Any], registry_path: str, channels_path: str, tenant_id: str, channel_id: str, host: str, offering_id: str) -> bool:
    error = str(payload.get("error") or "").strip().lower()
    if error not in {"tenant_exists", "channel_exists"}:
        return False
    return _can_reuse_existing_scope(
        registry_path=registry_path,
        channels_path=channels_path,
        tenant_id=tenant_id,
        channel_id=channel_id,
        host=host,
        offering_id=offering_id,
    )


def _derive_failure_blockers(step_name: str, payload: Dict[str, Any]) -> List[str]:
    blockers = [str(x) for x in (payload.get("activation_blockers") or []) if str(x).strip()]
    if blockers:
        return sorted(set(blockers))
    error = str(payload.get("error") or "").strip().lower()
    if step_name == "scaffold_partner_offering":
        if error in {"tenant_exists", "channel_exists"}:
            return ["existing_scope_conflict"]
        if error == "offering_not_found":
            return ["offering_not_found"]
    if step_name == "validate_tenant_onboarding":
        return ["onboarding_validation_failed"]
    if step_name == "activate_partner_tenant":
        return ["activation_failed"]
    return [f"{step_name}_failed"]


def _required_inputs_from_blockers(blockers: List[str]) -> List[str]:
    keys: List[str] = []
    blocker_set = {str(x or "").strip() for x in (blockers or []) if str(x or "").strip()}
    if any("missing_source_proof_url" in item for item in blocker_set):
        keys.append("partner_proof_url")
    if any("missing_api_key" in item or "disabled_missing_api_key" in item for item in blocker_set):
        keys.append("partner_api_key")
    if "commercial_use_not_allowed" in blocker_set or "missing_approved_data_source" in blocker_set or "non_approved_source_in_enabled_tenant" in blocker_set:
        keys.append("partner_data_source_approval")
    if "smoke_failed" in blocker_set:
        keys.append("partner_live_smoke_retry")
    return keys


def _resolved_inputs(*, proof_url: str, api_key_value: str, approve_source: bool, smoke_requested: bool, smoke_ok: Any) -> List[str]:
    keys: List[str] = []
    if str(proof_url or "").strip():
        keys.append("partner_proof_url")
    if str(api_key_value or "").strip():
        keys.append("partner_api_key")
    if approve_source:
        keys.append("partner_data_source_approval")
    if smoke_requested and smoke_ok is True:
        keys.append("partner_live_smoke_retry")
    return keys


def _build_handoff_summary(
    blockers: List[str],
    *,
    proof_url: str,
    api_key_value: str,
    approve_source: bool,
    smoke_requested: bool,
    smoke_ok: Any,
) -> Dict[str, Any]:
    blocker_set = {str(x or "").strip() for x in (blockers or []) if str(x or "").strip()}
    remaining_required_inputs = _required_inputs_from_blockers(list(blocker_set))
    resolved_inputs = _resolved_inputs(
        proof_url=proof_url,
        api_key_value=api_key_value,
        approve_source=approve_source,
        smoke_requested=smoke_requested,
        smoke_ok=smoke_ok,
    )
    next_actions: List[str] = []
    if "missing_source_proof_url_pending" in blocker_set or "missing_source_proof_url" in blocker_set:
        next_actions.append("Provide partner contract proof URL")
    if "missing_api_key_value" in blocker_set or "disabled_missing_api_key" in blocker_set:
        next_actions.append("Issue partner API key and inject env")
    if "non_approved_source_in_enabled_tenant" in blocker_set or "commercial_use_not_allowed" in blocker_set:
        next_actions.append("Approve data source for commercial use")
    if "smoke_failed" in blocker_set:
        next_actions.append("Retry live smoke with verified endpoint/origin/host")
    if not next_actions and blocker_set:
        next_actions.append("Resolve activation blockers and rerun")
    if not blocker_set:
        next_actions.append("Deliver widget/API handoff after activation")
    return {
        "proof_url_supplied": bool(str(proof_url or "").strip()),
        "api_key_supplied": bool(str(api_key_value or "").strip()),
        "smoke_requested": bool(smoke_requested),
        "smoke_ok": smoke_ok,
        "resolved_inputs": resolved_inputs,
        "remaining_required_inputs": remaining_required_inputs,
        "activation_ready": len(blocker_set) == 0,
        "embed_handoff_ready": len(blocker_set) == 0,
        "next_actions": next_actions,
    }


def build_onboarding_plan(
    *,
    offering_id: str,
    tenant_id: str,
    channel_id: str,
    host: str,
    brand_name: str,
    brand_label: str = "",
    contact_email: str = "",
    contact_phone: str = "010-0000-0000",
    site_url: str = "",
    notice_url: str = "",
    registry_path: str = "",
    channels_path: str = "",
    env_path: str = "",
    proof_url: str = "",
    source_id: str = "",
    approve_source: bool = False,
    api_key_env: str = "",
    api_key_value: str = "",
    smoke_base_url: str = "",
    smoke_service: str = "",
    smoke_origin: str = "",
    smoke_host: str = "",
    smoke_channel_id: str = "",
    smoke_timeout: int = 15,
    apply: bool = False,
    run_smoke_in_dry_run: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    registry_file = Path(str(registry_path or (ROOT / "tenant_config" / "tenant_registry.json"))).resolve()
    channels_file = Path(str(channels_path or (ROOT / "tenant_config" / "channel_profiles.json"))).resolve()
    env_file = Path(str(env_path or (ROOT / ".env"))).resolve()

    if apply:
        active_paths = {
            "registry": str(registry_file),
            "channels": str(channels_file),
            "env_file": str(env_file),
        }
    else:
        tempdir = tempfile.mkdtemp(prefix="partner_onboarding_flow_")
        temp_root = Path(tempdir)
        registry_copy = temp_root / "tenant_registry.json"
        channels_copy = temp_root / "channel_profiles.json"
        env_copy = temp_root / ".env"
        validation_report = temp_root / "tenant_onboarding_validation.json"
        _copy_if_exists(registry_file, registry_copy)
        _copy_if_exists(channels_file, channels_copy)
        _copy_if_exists(env_file, env_copy)
        active_paths = {
            "registry": str(registry_copy),
            "channels": str(channels_copy),
            "env_file": str(env_copy),
            "validation_report": str(validation_report),
            "tempdir": str(temp_root),
        }

    scaffold_cmd = _py_cmd(
        [
            "scripts/scaffold_partner_offering.py",
            "--offering-id",
            str(offering_id),
            "--tenant-id",
            str(tenant_id),
            "--channel-id",
            str(channel_id),
            "--host",
            str(host),
            "--brand-name",
            str(brand_name),
            "--contact-phone",
            str(contact_phone),
            "--registry",
            active_paths["registry"],
            "--channels",
            active_paths["channels"],
            "--env-file",
            active_paths["env_file"],
            "--apply",
        ]
    )
    if brand_label:
        scaffold_cmd.extend(["--brand-label", str(brand_label)])
    if contact_email:
        scaffold_cmd.extend(["--contact-email", str(contact_email)])
    if site_url:
        scaffold_cmd.extend(["--site-url", str(site_url)])
    if notice_url:
        scaffold_cmd.extend(["--notice-url", str(notice_url)])

    validate_cmd = _py_cmd(
        [
            "scripts/validate_tenant_onboarding.py",
            "--registry",
            active_paths["registry"],
            "--channels",
            active_paths["channels"],
            "--env-file",
            active_paths["env_file"],
            "--report",
            active_paths.get("validation_report", str(ROOT / "logs" / "tenant_onboarding_validation_latest.json")),
        ]
    )

    activate_cmd = _py_cmd(
        [
            "scripts/activate_partner_tenant.py",
            "--tenant-id",
            str(tenant_id),
            "--channel-id",
            str(channel_id),
            "--offering-id",
            str(offering_id),
            "--registry",
            active_paths["registry"],
            "--channels",
            active_paths["channels"],
            "--env-file",
            active_paths["env_file"],
            "--apply",
        ]
    )
    if proof_url:
        activate_cmd.extend(["--proof-url", str(proof_url)])
    if source_id:
        activate_cmd.extend(["--source-id", str(source_id)])
    if approve_source:
        activate_cmd.append("--approve-source")
    if api_key_env:
        activate_cmd.extend(["--api-key-env", str(api_key_env)])
    if api_key_value:
        activate_cmd.extend(["--api-key-value", str(api_key_value)])
    if smoke_base_url:
        activate_cmd.extend(["--smoke-base-url", str(smoke_base_url)])
    if smoke_service:
        activate_cmd.extend(["--smoke-service", str(smoke_service)])
    if smoke_origin:
        activate_cmd.extend(["--smoke-origin", str(smoke_origin)])
    if smoke_host:
        activate_cmd.extend(["--smoke-host", str(smoke_host)])
    if smoke_channel_id:
        activate_cmd.extend(["--smoke-channel-id", str(smoke_channel_id)])
    if smoke_timeout:
        activate_cmd.extend(["--smoke-timeout", str(int(smoke_timeout))])
    if (not apply) and (not run_smoke_in_dry_run):
        activate_cmd.append("--skip-smoke")

    return [
        {"name": "scaffold_partner_offering", "command": scaffold_cmd},
        {"name": "validate_tenant_onboarding", "command": validate_cmd},
        {"name": "activate_partner_tenant", "command": activate_cmd},
    ], active_paths


def _append_embed_steps(plan: List[Dict[str, Any]], systems: List[str], *, host: str, tenant_id: str, active_paths: Dict[str, str]) -> None:
    for system in systems:
        widget = "permit" if system == "permit" else "yangdo"
        plan.append(
            {
                "name": f"plan_channel_embed:{widget}",
                "command": _py_cmd(
                    [
                        "scripts/plan_channel_embed.py",
                        "--host",
                        str(host),
                        "--tenant-id",
                        str(tenant_id),
                        "--widget",
                        widget,
                        "--registry",
                        active_paths["registry"],
                        "--channels",
                        active_paths["channels"],
                        "--env-file",
                        active_paths["env_file"],
                    ]
                ),
            }
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run partner onboarding flow: scaffold -> validate -> activate -> embed plan")
    parser.add_argument("--offering-id", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--brand-name", required=True)
    parser.add_argument("--brand-label", default="")
    parser.add_argument("--contact-email", default="")
    parser.add_argument("--contact-phone", default="010-0000-0000")
    parser.add_argument("--site-url", default="")
    parser.add_argument("--notice-url", default="")
    parser.add_argument("--registry", default=str(ROOT / "tenant_config" / "tenant_registry.json"))
    parser.add_argument("--channels", default=str(ROOT / "tenant_config" / "channel_profiles.json"))
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument("--proof-url", default="")
    parser.add_argument("--source-id", default="")
    parser.add_argument("--approve-source", action="store_true", default=False)
    parser.add_argument("--api-key-env", default="")
    parser.add_argument("--api-key-value", default="")
    parser.add_argument("--smoke-base-url", default="")
    parser.add_argument("--smoke-service", choices=["", "yangdo", "permit", "both"], default="")
    parser.add_argument("--smoke-origin", default="")
    parser.add_argument("--smoke-host", default="")
    parser.add_argument("--smoke-channel-id", default="")
    parser.add_argument("--smoke-timeout", type=int, default=15)
    parser.add_argument("--apply", action="store_true", default=False)
    parser.add_argument("--run-smoke-in-dry-run", action="store_true", default=False)
    parser.add_argument("--report", default=str(ROOT / "logs" / "partner_onboarding_flow_latest.json"))
    args = parser.parse_args()

    plan, active_paths = build_onboarding_plan(
        offering_id=args.offering_id,
        tenant_id=args.tenant_id,
        channel_id=args.channel_id,
        host=args.host,
        brand_name=args.brand_name,
        brand_label=args.brand_label,
        contact_email=args.contact_email,
        contact_phone=args.contact_phone,
        site_url=args.site_url,
        notice_url=args.notice_url,
        registry_path=args.registry,
        channels_path=args.channels,
        env_path=args.env_file,
        proof_url=args.proof_url,
        source_id=args.source_id,
        approve_source=bool(args.approve_source),
        api_key_env=args.api_key_env,
        api_key_value=args.api_key_value,
        smoke_base_url=args.smoke_base_url,
        smoke_service=args.smoke_service,
        smoke_origin=args.smoke_origin,
        smoke_host=args.smoke_host,
        smoke_channel_id=args.smoke_channel_id,
        smoke_timeout=int(args.smoke_timeout or 15),
        apply=bool(args.apply),
        run_smoke_in_dry_run=bool(args.run_smoke_in_dry_run),
    )

    report: Dict[str, Any] = {
        "ok": False,
        "mode": "apply" if args.apply else "dry_run",
        "offering_id": str(args.offering_id or "").strip().lower(),
        "tenant_id": str(args.tenant_id or "").strip().lower(),
        "channel_id": str(args.channel_id or "").strip().lower(),
        "host": str(args.host or "").strip().lower(),
        "paths": active_paths,
        "steps": [],
        "activation_blockers": [],
        "embed_plans": {},
    }

    exit_code = 0
    systems: List[str] = []
    step_index = 0
    while step_index < len(plan):
        step = plan[step_index]
        result = _run(step["command"])
        payload = result.get("json") if isinstance(result.get("json"), dict) else {}
        if step["name"] == "scaffold_partner_offering":
            systems = _systems_from_offering_json(payload)
            if (not result["ok"]) and _is_reusable_scaffold_conflict(
                payload=payload,
                registry_path=active_paths["registry"],
                channels_path=active_paths["channels"],
                tenant_id=args.tenant_id,
                channel_id=args.channel_id,
                host=args.host,
                offering_id=args.offering_id,
            ):
                result = dict(result)
                result["ok"] = True
                result["handled_as_noop"] = True
                result["noop_reason"] = str(payload.get("error") or "existing_scope_reused")
                systems = _load_offering_systems(active_paths["registry"], args.offering_id)
        report["steps"].append({"name": step["name"], **result})
        if step["name"] == "scaffold_partner_offering":
            if systems:
                _append_embed_steps(plan, systems, host=args.host, tenant_id=args.tenant_id, active_paths=active_paths)
        if not result["ok"]:
            exit_code = result["returncode"] or 1
            report["activation_blockers"] = _derive_failure_blockers(step["name"], payload)
            break
        if step["name"].startswith("plan_channel_embed:"):
            widget = step["name"].split(":", 1)[1]
            report["embed_plans"][widget] = result.get("json") if isinstance(result.get("json"), dict) else None
        step_index += 1

    activation_step = next((step for step in report["steps"] if step["name"] == "activate_partner_tenant"), None)
    if isinstance(activation_step, dict):
        activation_json = activation_step.get("json") if isinstance(activation_step.get("json"), dict) else {}
        blockers = activation_json.get("activation_blockers") if isinstance(activation_json, dict) else []
        report["activation_blockers"] = sorted({str(x) for x in (blockers or []) if str(x).strip()})
        report["smoke_requested"] = bool(activation_json.get("smoke_requested")) if isinstance(activation_json, dict) else False
        report["smoke_ok"] = activation_json.get("smoke_ok") if isinstance(activation_json, dict) else None
    report["handoff"] = _build_handoff_summary(
        report.get("activation_blockers") or [],
        proof_url=args.proof_url,
        api_key_value=args.api_key_value,
        approve_source=bool(args.approve_source),
        smoke_requested=bool(report.get("smoke_requested")),
        smoke_ok=report.get("smoke_ok"),
    )

    report["ok"] = exit_code == 0
    report_path = Path(str(args.report)).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
