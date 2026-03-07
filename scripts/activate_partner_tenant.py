#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_tenant_onboarding import _load_env_file, _load_json, validate_registry
from scripts.run_partner_api_smoke import run_smoke


DEFAULT_REGISTRY = ROOT / "tenant_config" / "tenant_registry.json"
DEFAULT_CHANNELS = ROOT / "tenant_config" / "channel_profiles.json"


def _find_row(rows, key: str, value: str) -> Dict[str, object]:
    wanted = str(value or "").strip().lower()
    for row in rows or []:
        if str((row or {}).get(key) or "").strip().lower() == wanted:
            return dict(row)
    return {}


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


def _restore_text(path: Path, original_text: str | None, existed: bool) -> None:
    if existed:
        path.write_text(str(original_text or ""), encoding="utf-8")
        return
    if path.exists():
        path.unlink()


def _find_channel_row(channel_registry: Dict[str, object], channel_id: str) -> Dict[str, object]:
    channels = channel_registry.get("channels") if isinstance(channel_registry, dict) else []
    if not isinstance(channels, list):
        return {}
    wanted = str(channel_id or "").strip().lower()
    for row in channels:
        if isinstance(row, dict) and str(row.get("channel_id") or "").strip().lower() == wanted:
            return dict(row)
    return {}


def _find_offering_template(registry: Dict[str, object], offering_id: str) -> Dict[str, object]:
    rows = registry.get("offering_templates") if isinstance(registry, dict) else []
    if not isinstance(rows, list):
        return {}
    wanted = str(offering_id or "").strip().lower()
    for row in rows:
        if isinstance(row, dict) and str(row.get("offering_id") or "").strip().lower() == wanted:
            return dict(row)
    return {}


def _derive_smoke_context(channel_row: Dict[str, object]) -> Dict[str, str]:
    hosts = channel_row.get("channel_hosts") if isinstance(channel_row.get("channel_hosts"), list) else []
    host = str(hosts[0] or "").strip() if hosts else ""
    branding = channel_row.get("branding") if isinstance(channel_row.get("branding"), dict) else {}
    site_url = str(branding.get("site_url") or "").strip()
    engine_origin = str(channel_row.get("engine_origin") or "").strip()
    origin = site_url
    if not origin and host:
        origin = f"https://{host}"
    if origin and not host:
        host = str(urlparse(origin).netloc or "").strip()
    return {"origin": origin, "host": host, "base_url": engine_origin}


def _mutate_registry_for_activation(
    registry: Dict[str, object],
    *,
    tenant_id: str,
    proof_url: str,
    source_id: str,
    approve_source: bool,
    offering: Dict[str, object] | None = None,
) -> Dict[str, object]:
    data = json.loads(json.dumps(registry, ensure_ascii=False))
    tenants = data.get("tenants") if isinstance(data, dict) else []
    if not isinstance(tenants, list):
        return data
    for row in tenants:
        if not isinstance(row, dict):
            continue
        if str(row.get("tenant_id") or "").strip().lower() != tenant_id:
            continue
        row["enabled"] = True
        if isinstance(offering, dict) and offering:
            plan = str(offering.get("plan") or "").strip().lower()
            if plan:
                row["plan"] = plan
            allowed_features = [str(x or "").strip().lower() for x in (offering.get("allowed_features") or []) if str(x or "").strip()]
            allowed_systems = [str(x or "").strip().lower() for x in (offering.get("allowed_systems") or []) if str(x or "").strip()]
            if allowed_features:
                row["allowed_features"] = allowed_features
            if allowed_systems:
                row["allowed_systems"] = allowed_systems
        if proof_url:
            sources = row.get("data_sources") if isinstance(row.get("data_sources"), list) else []
            target = None
            for src in sources:
                if not isinstance(src, dict):
                    continue
                current_id = str(src.get("source_id") or "").strip().lower()
                access_mode = str(src.get("access_mode") or "").strip().lower()
                if source_id and current_id == source_id:
                    target = src
                    break
                if (not source_id) and access_mode in {"partner_contract", "official_api"}:
                    target = src
                    break
            if isinstance(target, dict):
                target["proof_url"] = proof_url
                if approve_source:
                    target["status"] = "approved"
                    target["allows_commercial_use"] = True
        break
    return data


def _mutate_channels_for_activation(
    channel_registry: Dict[str, object],
    *,
    channel_id: str,
    offering: Dict[str, object] | None = None,
) -> Dict[str, object]:
    data = json.loads(json.dumps(channel_registry, ensure_ascii=False))
    channels = data.get("channels") if isinstance(data, dict) else []
    if not isinstance(channels, list):
        return data
    for row in channels:
        if isinstance(row, dict) and str(row.get("channel_id") or "").strip().lower() == channel_id:
            row["enabled"] = True
            if isinstance(offering, dict) and offering:
                allowed_systems = [str(x or "").strip().lower() for x in (offering.get("allowed_systems") or []) if str(x or "").strip()]
                if allowed_systems:
                    row["exposed_systems"] = allowed_systems
            break
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Activate tenant/channel only when onboarding validation stays clean after enabling")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--channel-id", default="")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--channels", default=str(DEFAULT_CHANNELS))
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument("--offering-id", default="")
    parser.add_argument("--proof-url", default="")
    parser.add_argument("--source-id", default="")
    parser.add_argument("--approve-source", action="store_true", default=False)
    parser.add_argument("--api-key-env", default="")
    parser.add_argument("--api-key-value", default="")
    parser.add_argument("--smoke-base-url", default="")
    parser.add_argument("--smoke-service", choices=["yangdo", "permit", "both"], default="")
    parser.add_argument("--smoke-origin", default="")
    parser.add_argument("--smoke-host", default="")
    parser.add_argument("--smoke-channel-id", default="")
    parser.add_argument("--smoke-timeout", type=int, default=15)
    parser.add_argument("--skip-smoke", action="store_true", default=False)
    parser.add_argument("--apply", action="store_true", default=False)
    args = parser.parse_args()

    tenant_id = str(args.tenant_id or "").strip().lower()
    channel_id = str(args.channel_id or "").strip().lower()
    offering_id = str(args.offering_id or "").strip().lower()
    proof_url = str(args.proof_url or "").strip()
    source_id = str(args.source_id or "").strip().lower()
    api_key_env = str(args.api_key_env or "").strip()
    api_key_value = str(args.api_key_value or "").strip()
    smoke_base_url = str(args.smoke_base_url or "").strip()
    smoke_service = str(args.smoke_service or "").strip().lower()
    smoke_origin = str(args.smoke_origin or "").strip()
    smoke_host = str(args.smoke_host or "").strip()
    smoke_channel_id = str(args.smoke_channel_id or "").strip().lower()
    smoke_timeout = int(args.smoke_timeout or 15)
    skip_smoke = bool(args.skip_smoke)

    registry_path = Path(str(args.registry)).resolve()
    channels_path = Path(str(args.channels)).resolve()
    env_path = Path(str(args.env_file)).resolve()

    registry = _load_json(registry_path)
    channel_registry = _load_json(channels_path) if channels_path.exists() else {}
    env_values = _load_env_file(env_path)
    env_values.update({k: v for k, v in os.environ.items() if isinstance(v, str)})

    current_report = validate_registry(registry, env_values=env_values, channel_registry=channel_registry)
    current_tenant = _find_row(current_report.get("tenants"), "tenant_id", tenant_id)
    if not current_tenant:
        print(json.dumps({"ok": False, "error": "tenant_not_found", "tenant_id": tenant_id}, ensure_ascii=False))
        return 1

    if not channel_id:
        for row in current_report.get("channels", []):
            if str((row or {}).get("default_tenant_id") or "").strip().lower() == tenant_id:
                channel_id = str((row or {}).get("channel_id") or "").strip().lower()
                break

    offering = _find_offering_template(registry, offering_id) if offering_id else {}
    if offering_id and not offering:
        print(json.dumps({"ok": False, "error": "offering_not_found", "offering_id": offering_id}, ensure_ascii=False))
        return 1

    prospective_registry = _mutate_registry_for_activation(
        registry,
        tenant_id=tenant_id,
        proof_url=proof_url,
        source_id=source_id,
        approve_source=bool(args.approve_source),
        offering=offering,
    )
    prospective_channels = _mutate_channels_for_activation(channel_registry, channel_id=channel_id, offering=offering) if channel_id else channel_registry

    resolved_api_key_env = api_key_env
    if api_key_value:
        env_name = resolved_api_key_env
        if not env_name:
            for row in prospective_registry.get("tenants", []):
                if isinstance(row, dict) and str(row.get("tenant_id") or "").strip().lower() == tenant_id:
                    envs = row.get("api_key_envs") if isinstance(row.get("api_key_envs"), list) else []
                    if envs:
                        env_name = str(envs[0] or "").strip()
                    break
        resolved_api_key_env = env_name
        if env_name:
            env_values[env_name] = api_key_value

    report = validate_registry(prospective_registry, env_values=env_values, channel_registry=prospective_channels)
    tenant_row = _find_row(report.get("tenants"), "tenant_id", tenant_id)
    channel_row = _find_row(report.get("channels"), "channel_id", channel_id) if channel_id else {}
    channel_config = _find_channel_row(prospective_channels, channel_id) if channel_id else {}
    derived_smoke = _derive_smoke_context(channel_config)
    resolved_smoke_origin = smoke_origin or str(derived_smoke.get("origin") or "")
    resolved_smoke_host = smoke_host or str(derived_smoke.get("host") or "")
    resolved_smoke_channel_id = smoke_channel_id or channel_id
    offering_systems = [str(x or "").strip().lower() for x in (offering.get("allowed_systems") or []) if str(x or "").strip()]
    resolved_smoke_service = smoke_service
    if not resolved_smoke_service:
        if offering_systems == ["permit"]:
            resolved_smoke_service = "permit"
        elif offering_systems == ["yangdo"]:
            resolved_smoke_service = "yangdo"
        else:
            resolved_smoke_service = "both"
    resolved_smoke_base_url = smoke_base_url or str(derived_smoke.get("base_url") or "")
    should_run_smoke = bool(resolved_smoke_base_url) and not skip_smoke

    blockers = list(tenant_row.get("activation_blockers") or [])
    if channel_row:
        blockers.extend(list(channel_row.get("activation_blockers") or []))
    blockers = sorted({str(x) for x in blockers if str(x).strip()})

    result = {
        "ok": len(blockers) == 0,
        "tenant_id": tenant_id,
        "channel_id": channel_id,
        "tenant_activation_ready": bool(tenant_row.get("activation_ready")),
        "channel_activation_ready": bool(channel_row.get("activation_ready")) if channel_row else None,
        "activation_blockers": blockers,
        "offering_id": offering_id,
        "offering_allowed_systems": offering_systems,
        "offering_allowed_features": [str(x or "").strip().lower() for x in (offering.get("allowed_features") or []) if str(x or "").strip()],
        "would_enable_tenant": True,
        "would_enable_channel": bool(channel_id),
        "proof_url_applied": bool(proof_url),
        "api_key_env": resolved_api_key_env,
        "api_key_value_supplied": bool(api_key_value),
        "smoke_requested": should_run_smoke,
        "smoke_base_url": resolved_smoke_base_url,
        "smoke_service": resolved_smoke_service,
        "smoke_origin": resolved_smoke_origin,
        "smoke_host": resolved_smoke_host,
        "smoke_channel_id": resolved_smoke_channel_id,
        "skip_smoke": skip_smoke,
        "applied": False,
    }

    if blockers or not args.apply:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if (len(blockers) == 0 and not args.apply) else 2 if blockers else 0

    registry_existed = registry_path.exists()
    channels_existed = channels_path.exists()
    env_existed = env_path.exists()
    original_registry_text = registry_path.read_text(encoding="utf-8") if registry_existed else None
    original_channels_text = channels_path.read_text(encoding="utf-8") if channels_existed else None
    original_env_text = env_path.read_text(encoding="utf-8") if env_existed else None

    registry_path.write_text(json.dumps(prospective_registry, ensure_ascii=False, indent=2), encoding="utf-8")
    channels_path.write_text(json.dumps(prospective_channels, ensure_ascii=False, indent=2), encoding="utf-8")
    if api_key_value and resolved_api_key_env:
        _update_env_file(env_path, resolved_api_key_env, api_key_value)
    result["applied"] = True

    if should_run_smoke:
        smoke_api_key = api_key_value
        if not smoke_api_key and resolved_api_key_env:
            smoke_api_key = str(env_values.get(resolved_api_key_env) or "").strip()
        smoke_result = run_smoke(
            base_url=resolved_smoke_base_url,
            service=resolved_smoke_service,
            api_key=smoke_api_key,
            origin=resolved_smoke_origin,
            host=resolved_smoke_host,
            channel_id=resolved_smoke_channel_id or "seoul_web",
            timeout=smoke_timeout,
        )
        result["smoke"] = smoke_result
        result["smoke_ok"] = bool(smoke_result.get("ok"))
        if not result["smoke_ok"]:
            _restore_text(registry_path, original_registry_text, registry_existed)
            _restore_text(channels_path, original_channels_text, channels_existed)
            if api_key_value and resolved_api_key_env:
                _restore_text(env_path, original_env_text, env_existed)
            result["applied"] = False
            result["rolled_back"] = True
            result["ok"] = False
            result["activation_blockers"] = sorted(set(list(result.get("activation_blockers") or []) + ["smoke_failed"]))
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 3

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
