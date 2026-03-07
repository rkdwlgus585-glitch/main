#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_tenant_onboarding import _load_env_file, _load_json
from scripts.verify_partner_activation_resolution import build_resolution_report
from security_http import parse_key_values


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _find_channel(channels: List[Dict[str, Any]], tenant_id: str) -> Dict[str, Any]:
    wanted = str(tenant_id or "").strip().lower()
    for row in channels:
        if not isinstance(row, dict):
            continue
        if str(row.get("default_tenant_id") or "").strip().lower() == wanted:
            return row
        if str(row.get("channel_id") or "").strip().lower() == wanted:
            return row
    return {}


def _effective_allowed_features(tenant: Dict[str, Any], plan_feature_defaults: Dict[str, Any]) -> List[str]:
    explicit = sorted(_as_list(tenant.get("allowed_features")))
    if explicit:
        return explicit
    plan = str(tenant.get("plan") or "").strip().lower()
    defaults = plan_feature_defaults.get(plan) if isinstance(plan_feature_defaults, dict) else []
    return sorted(_as_list(defaults))


def _infer_offering_id(tenant: Dict[str, Any], offerings: List[Dict[str, Any]], plan_feature_defaults: Dict[str, Any]) -> str:
    allowed_systems = sorted(_as_list(tenant.get("allowed_systems")))
    allowed_features = _effective_allowed_features(tenant, plan_feature_defaults)
    plan = str(tenant.get("plan") or "").strip().lower()
    for row in offerings:
        if not isinstance(row, dict):
            continue
        if sorted(_as_list(row.get("allowed_systems"))) != allowed_systems:
            continue
        if sorted(_as_list(row.get("allowed_features"))) != allowed_features:
            continue
        if str(row.get("plan") or "").strip().lower() != plan:
            continue
        return str(row.get("offering_id") or "").strip().lower()
    return ""


def _extract_partner_inputs(tenant: Dict[str, Any], env_values: Dict[str, str]) -> Dict[str, Any]:
    api_key_envs = _as_list(tenant.get("api_key_envs"))
    api_key_present = False
    api_key_env = ""
    api_key_value = ""
    token_count = 0
    for env_name in api_key_envs:
        raw = str(env_values.get(env_name) or "").strip()
        tokens = parse_key_values(raw) if raw else []
        if tokens:
            api_key_present = True
            api_key_env = env_name
            api_key_value = raw
            token_count = len(tokens)
            break

    sources = tenant.get("data_sources") if isinstance(tenant.get("data_sources"), list) else []
    proof_url = ""
    approval_present = False
    source_id = ""
    approved_source_count = 0
    for row in sources:
        if not isinstance(row, dict):
            continue
        if str(row.get("status") or "").strip().lower() == "approved" and bool(row.get("allows_commercial_use")):
            approved_source_count += 1
            approval_present = True
        candidate_proof = str(row.get("proof_url") or "").strip()
        if candidate_proof and not proof_url:
            proof_url = candidate_proof
            source_id = str(row.get("source_id") or "").strip().lower()

    return {
        "api_key_present": api_key_present,
        "api_key_env": api_key_env,
        "api_key_token_count": token_count,
        "api_key_value": api_key_value,
        "proof_url_present": bool(proof_url),
        "proof_url": proof_url,
        "source_id": source_id,
        "approval_present": approval_present,
        "approved_source_count": approved_source_count,
    }


def _derive_scenario(proof: bool, api_key: bool, approval: bool) -> Tuple[str, List[str]]:
    missing: List[str] = []
    if not proof:
        missing.append("partner_proof_url")
    if not api_key:
        missing.append("partner_api_key")
    if not approval:
        missing.append("partner_data_source_approval")

    if proof and api_key and approval:
        return "proof_key_and_approval", []
    if proof and api_key:
        return "proof_and_key", missing
    if proof:
        return "proof_only", missing
    if (not proof) and (not api_key) and (not approval):
        return "baseline", missing
    return "partial_custom", missing


def build_partner_input_snapshot(
    *,
    registry_path: Path,
    channels_path: Path,
    env_path: Path,
    include_resolution: bool = True,
) -> Dict[str, Any]:
    registry = _load_json(registry_path)
    channel_registry = _load_json(channels_path) if channels_path.exists() else {}
    env_values = _load_env_file(env_path)
    env_values.update({k: v for k, v in os.environ.items() if isinstance(v, str)})

    tenants = registry.get("tenants") if isinstance(registry.get("tenants"), list) else []
    channels = channel_registry.get("channels") if isinstance(channel_registry.get("channels"), list) else []
    offerings = registry.get("offering_templates") if isinstance(registry.get("offering_templates"), list) else []
    plan_feature_defaults = registry.get("plan_feature_defaults") if isinstance(registry.get("plan_feature_defaults"), dict) else {}

    rows: List[Dict[str, Any]] = []
    scenario_counts: Dict[str, int] = {}
    ready_count = 0
    for tenant in tenants:
        if not isinstance(tenant, dict):
            continue
        tenant_id = str(tenant.get("tenant_id") or "").strip().lower()
        if not tenant_id.startswith("partner_"):
            continue
        channel = _find_channel(channels, tenant_id)
        branding = channel.get("branding") if isinstance(channel.get("branding"), dict) else {}
        host = ""
        channel_hosts = channel.get("channel_hosts") if isinstance(channel.get("channel_hosts"), list) else []
        if channel_hosts:
            host = str(channel_hosts[0] or "").strip().lower()

        inputs = _extract_partner_inputs(tenant, env_values)
        scenario, missing = _derive_scenario(
            proof=bool(inputs["proof_url_present"]),
            api_key=bool(inputs["api_key_present"]),
            approval=bool(inputs["approval_present"]),
        )
        offering_id = _infer_offering_id(tenant, offerings, plan_feature_defaults)
        feature_source = "explicit" if _as_list(tenant.get("allowed_features")) else "plan_default"
        row: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "channel_id": str(channel.get("channel_id") or "").strip().lower(),
            "offering_id": offering_id,
            "feature_source": feature_source,
            "host": host,
            "systems": _as_list(tenant.get("allowed_systems")),
            "current_scenario": scenario,
            "missing_required_inputs": missing,
            "proof_url_present": bool(inputs["proof_url_present"]),
            "api_key_present": bool(inputs["api_key_present"]),
            "approval_present": bool(inputs["approval_present"]),
            "approved_source_count": int(inputs["approved_source_count"]),
            "api_key_env": str(inputs["api_key_env"] or ""),
            "api_key_token_count": int(inputs["api_key_token_count"]),
        }
        if include_resolution and offering_id and host:
            brand_name = str(branding.get("brand_name") or tenant.get("display_name") or tenant_id)
            resolution = build_resolution_report(
                offering_id=offering_id,
                tenant_id=tenant_id,
                channel_id=str(channel.get("channel_id") or tenant_id),
                host=host,
                brand_name=brand_name,
                scenario=scenario if scenario != "partial_custom" else "",
                proof_url=str(inputs["proof_url"] or ""),
                api_key_value=str(inputs["api_key_value"] or ""),
            )
            row["resolution_summary"] = resolution.get("summary") if isinstance(resolution.get("summary"), dict) else {}
            row["resolution_remaining_required_inputs"] = _as_list((resolution.get("actual") or {}).get("remaining_required_inputs"))
        scenario_counts[scenario] = int(scenario_counts.get(scenario, 0) or 0) + 1
        if not missing:
            ready_count += 1
        rows.append(row)

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_paths": {
            "registry": str(registry_path.resolve()),
            "channels": str(channels_path.resolve()),
            "env_file": str(env_path.resolve()),
        },
        "summary": {
            "partner_tenant_count": len(rows),
            "ready_tenant_count": ready_count,
            "scenario_counts": scenario_counts,
            "include_resolution": bool(include_resolution),
        },
        "partners": rows,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines: List[str] = []
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines.append("# Partner Input Snapshot")
    lines.append("")
    lines.append(f"- partner_tenant_count: {summary.get('partner_tenant_count')}")
    lines.append(f"- ready_tenant_count: {summary.get('ready_tenant_count')}")
    lines.append(f"- include_resolution: {summary.get('include_resolution')}")
    scenario_counts = summary.get("scenario_counts") if isinstance(summary.get("scenario_counts"), dict) else {}
    for key, value in scenario_counts.items():
        lines.append(f"- scenario_count.{key}: {value}")
    lines.append("")
    lines.append("## Partners")
    for row in payload.get("partners") or []:
        lines.append(
            f"- {row.get('tenant_id')} / {row.get('channel_id')}: "
            f"scenario={row.get('current_scenario')} "
            f"missing={', '.join(row.get('missing_required_inputs') or []) or '(none)'} "
            f"proof={row.get('proof_url_present')} key={row.get('api_key_present')} approval={row.get('approval_present')}"
        )
        resolution_summary = row.get("resolution_summary") if isinstance(row.get("resolution_summary"), dict) else {}
        if resolution_summary:
            lines.append(
                f"  resolution_ok={resolution_summary.get('ok')} "
                f"matches_preview={resolution_summary.get('matches_preview_expected_remaining')}"
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a snapshot of current partner input readiness from registry/env")
    parser.add_argument("--registry", default=str(ROOT / "tenant_config" / "tenant_registry.json"))
    parser.add_argument("--channels", default=str(ROOT / "tenant_config" / "channel_profiles.json"))
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument("--skip-resolution", action="store_true", default=False)
    parser.add_argument("--json", default="logs/partner_input_snapshot_latest.json")
    parser.add_argument("--md", default="logs/partner_input_snapshot_latest.md")
    args = parser.parse_args()

    payload = build_partner_input_snapshot(
        registry_path=Path(str(args.registry)).resolve(),
        channels_path=Path(str(args.channels)).resolve(),
        env_path=Path(str(args.env_file)).resolve(),
        include_resolution=not bool(args.skip_resolution),
    )

    json_path = (ROOT / str(args.json)).resolve()
    md_path = (ROOT / str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_path), "md": str(md_path), "summary": payload.get("summary")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
