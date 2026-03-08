#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "tenant_config" / "tenant_registry.json"
DEFAULT_CHANNELS = ROOT / "tenant_config" / "channel_profiles.json"
DEFAULT_SNAPSHOT = ROOT / "logs" / "partner_input_snapshot_latest.json"
DEFAULT_SIMULATION = ROOT / "logs" / "partner_activation_simulation_matrix_latest.json"
DEFAULT_JSON = ROOT / "logs" / "partner_input_handoff_packet_latest.json"
DEFAULT_MD = ROOT / "logs" / "partner_input_handoff_packet_latest.md"


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
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _find_by_key(rows: List[Dict[str, Any]], key: str, value: str) -> Dict[str, Any]:
    wanted = str(value or "").strip().lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get(key) or "").strip().lower() == wanted:
            return row
    return {}


def _first_api_env(tenant: Dict[str, Any]) -> str:
    envs = _as_list(tenant.get("api_key_envs"))
    return envs[0] if envs else ""


def _first_source_id(tenant: Dict[str, Any]) -> str:
    for row in list(tenant.get("data_sources") or []):
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id") or "").strip()
        if source_id:
            return source_id
    return ""


def _proof_example(host: str, tenant_id: str) -> str:
    clean_host = str(host or "").strip().lower() or "partner.example.com"
    clean_tenant = str(tenant_id or "").strip().lower() or "partner"
    return f"https://{clean_host}/contracts/{clean_tenant}"


def build_partner_input_handoff_packet(
    *,
    registry_path: Path,
    channels_path: Path,
    snapshot_path: Path,
    simulation_path: Path,
) -> Dict[str, Any]:
    registry = _load_json(registry_path)
    channels_payload = _load_json(channels_path)
    snapshot = _load_json(snapshot_path)
    simulation = _load_json(simulation_path)

    tenants = registry.get("tenants") if isinstance(registry.get("tenants"), list) else []
    channels = channels_payload.get("channels") if isinstance(channels_payload.get("channels"), list) else []
    snapshot_rows = snapshot.get("partners") if isinstance(snapshot.get("partners"), list) else []
    simulation_rows = simulation.get("partners") if isinstance(simulation.get("partners"), list) else []
    simulation_summary = simulation.get("summary") if isinstance(simulation.get("summary"), dict) else {}

    rows: List[Dict[str, Any]] = []
    common_required: List[str] | None = None
    for snap in snapshot_rows:
        if not isinstance(snap, dict):
            continue
        tenant_id = str(snap.get("tenant_id") or "").strip().lower()
        channel_id = str(snap.get("channel_id") or "").strip().lower()
        tenant = _find_by_key(tenants, "tenant_id", tenant_id)
        channel = _find_by_key(channels, "channel_id", channel_id)
        sim = _find_by_key(simulation_rows, "tenant_id", tenant_id)
        host = str(snap.get("host") or "")
        required_inputs = _as_list(snap.get("missing_required_inputs"))
        common_required = required_inputs if common_required is None else [item for item in common_required if item in required_inputs]
        row = {
            "tenant_id": tenant_id,
            "channel_id": channel_id,
            "offering_id": str(snap.get("offering_id") or ""),
            "systems": _as_list(snap.get("systems")),
            "host": host,
            "brand_name": str(((channel.get("branding") or {}).get("brand_name")) or tenant.get("display_name") or tenant_id),
            "required_inputs": required_inputs,
            "expected_api_key_env": str(snap.get("api_key_env") or _first_api_env(tenant)),
            "example_proof_url": _proof_example(host, tenant_id),
            "recommended_source_id": _first_source_id(tenant),
            "simulated_decision_after_injection": str(sim.get("simulated_decision") or ""),
            "simulated_remaining_required_inputs": _as_list(sim.get("simulated_remaining_required_inputs")),
            "resolved_inputs_after_injection": _as_list(sim.get("removed_required_inputs")),
            "handoff_notes": [
                "proof_url은 계약 또는 제휴 증빙 URL로 채워야 합니다.",
                "API key는 해당 tenant 전용 env에만 주입해야 합니다.",
                "data source approval은 approved=true, commercial_use=true 상태를 모두 만족해야 합니다.",
            ],
            "copy_paste_packet": {
                "proof_url_field": f"proof_url={_proof_example(host, tenant_id)}",
                "api_key_env_line": f"{str(snap.get('api_key_env') or _first_api_env(tenant) or 'TENANT_API_KEY_PARTNER')}" + "=<issued-secret>",
                "approval_flags": [
                    "approved=true",
                    "commercial_use=true",
                ],
                "source_id_line": f"source_id={_first_source_id(tenant) or 'partner_source_placeholder'}",
            },
        }
        rows.append(row)

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_paths": {
            "registry": str(registry_path.resolve()),
            "channels": str(channels_path.resolve()),
            "snapshot": str(snapshot_path.resolve()),
            "simulation": str(simulation_path.resolve()),
        },
        "summary": {
            "partner_count": len(rows),
            "uniform_required_inputs": bool(common_required is not None and len(common_required) > 0 and all(_as_list(row.get("required_inputs")) == common_required for row in rows)),
            "common_required_inputs": common_required or [],
            "ready_after_recommended_injection": bool(simulation_summary.get("all_ready_after_simulation")),
            "ready_after_recommended_injection_count": int(simulation_summary.get("ready_after_simulation_count", 0) or 0),
            "copy_paste_ready": all(bool(((row.get("copy_paste_packet") or {}).get("proof_url_field"))) and bool(((row.get("copy_paste_packet") or {}).get("api_key_env_line"))) for row in rows),
        },
        "partners": rows,
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Partner Input Handoff Packet",
        "",
        f"- partner_count: {summary.get('partner_count')}",
        f"- uniform_required_inputs: {summary.get('uniform_required_inputs')}",
        f"- common_required_inputs: {', '.join(summary.get('common_required_inputs') or []) or '(none)'}",
        f"- ready_after_recommended_injection: {summary.get('ready_after_recommended_injection')}",
        "",
        "## Partners",
    ]
    for row in payload.get("partners") or []:
        if not isinstance(row, dict):
            continue
        copy_paste = row.get("copy_paste_packet") if isinstance(row.get("copy_paste_packet"), dict) else {}
        lines.append(
            f"- {row.get('tenant_id')} / {row.get('offering_id')}: "
            f"required={', '.join(row.get('required_inputs') or []) or '(none)'} "
            f"api_env={row.get('expected_api_key_env') or '(none)'} "
            f"source_id={row.get('recommended_source_id') or '(none)'} "
            f"simulated_decision={row.get('simulated_decision_after_injection') or '(none)'}"
        )
        lines.append(f"  - proof_url_field: {copy_paste.get('proof_url_field') or '(none)'}")
        lines.append(f"  - api_key_env_line: {copy_paste.get('api_key_env_line') or '(none)'}")
        lines.append(f"  - source_id_line: {copy_paste.get('source_id_line') or '(none)'}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a reusable partner input handoff packet.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--channels", type=Path, default=DEFAULT_CHANNELS)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--simulation", type=Path, default=DEFAULT_SIMULATION)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_partner_input_handoff_packet(
        registry_path=args.registry,
        channels_path=args.channels,
        snapshot_path=args.snapshot,
        simulation_path=args.simulation,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
