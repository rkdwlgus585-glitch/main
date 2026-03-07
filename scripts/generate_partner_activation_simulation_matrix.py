#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_partner_input_snapshot import build_partner_input_snapshot
from scripts.simulate_partner_input_injection import build_simulation_report


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def _proof_url_for_tenant(tenant_id: str, host: str) -> str:
    clean_host = str(host or "").strip().lower() or "example.com"
    clean_id = str(tenant_id or "").strip().lower() or "partner"
    return f"https://{clean_host}/contracts/{clean_id}"


def _api_key_for_tenant(tenant_id: str) -> str:
    clean_id = str(tenant_id or "").strip().lower().replace("_", "-") or "partner"
    return f"sim-{clean_id}-key"


def build_simulation_matrix(*, registry_path: Path, channels_path: Path, env_path: Path) -> Dict[str, Any]:
    snapshot = build_partner_input_snapshot(
        registry_path=registry_path,
        channels_path=channels_path,
        env_path=env_path,
        include_resolution=True,
    )
    partners = snapshot.get("partners") if isinstance(snapshot.get("partners"), list) else []
    rows: List[Dict[str, Any]] = []
    baseline_ready_count = 0
    ready_after_simulation = 0
    for row in partners:
        if not isinstance(row, dict):
            continue
        tenant_id = str(row.get("tenant_id") or "").strip()
        channel_id = str(row.get("channel_id") or "").strip()
        offering_id = str(row.get("offering_id") or "").strip()
        host = str(row.get("host") or "").strip()
        missing = _as_list(row.get("missing_required_inputs"))
        if not missing:
            baseline_ready_count += 1
        proof_url = _proof_url_for_tenant(tenant_id, host) if "partner_proof_url" in missing else ""
        api_key_value = _api_key_for_tenant(tenant_id) if "partner_api_key" in missing else ""
        approve_source = "partner_data_source_approval" in missing
        report = build_simulation_report(
            offering_id=offering_id,
            tenant_id=tenant_id,
            channel_id=channel_id,
            host=host,
            brand_name=str(tenant_id or channel_id),
            proof_url=proof_url,
            api_key_value=api_key_value,
            approve_source=approve_source,
            registry_path=registry_path,
            channels_path=channels_path,
            env_path=env_path,
        )
        simulated = report.get("simulated") if isinstance(report.get("simulated"), dict) else {}
        delta = report.get("delta") if isinstance(report.get("delta"), dict) else {}
        simulated_remaining = _as_list(simulated.get("remaining_required_inputs"))
        removed_required_inputs = [item for item in missing if item not in simulated_remaining]
        row_payload = {
            "tenant_id": tenant_id,
            "channel_id": channel_id,
            "offering_id": offering_id,
            "current_scenario": str(row.get("current_scenario") or ""),
            "current_missing_required_inputs": missing,
            "injected_inputs": {
                "partner_proof_url": bool(proof_url),
                "partner_api_key": bool(api_key_value),
                "partner_data_source_approval": bool(approve_source),
            },
            "simulated_decision": str(simulated.get("partner_activation_decision") or ""),
            "simulated_remaining_required_inputs": simulated_remaining,
            "preview_alignment_ok": bool(simulated.get("preview_alignment_ok")),
            "resolution_ok": bool(simulated.get("resolution_ok")),
            "refresh_summary": report.get("refresh_summary") if isinstance(report.get("refresh_summary"), dict) else {},
            "simulated_required_count_delta": {
                "before": len(missing),
                "after": int(delta.get("simulated_required_count", len(simulated_remaining)) or 0),
            },
            "removed_required_inputs": removed_required_inputs,
        }
        if row_payload["simulated_decision"] == "ready" and not row_payload["simulated_remaining_required_inputs"]:
            ready_after_simulation += 1
        rows.append(row_payload)

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_paths": {
            "registry": str(registry_path.resolve()),
            "channels": str(channels_path.resolve()),
            "env_file": str(env_path.resolve()),
        },
        "summary": {
            "partner_count": len(rows),
            "baseline_ready_count": baseline_ready_count,
            "ready_after_simulation_count": ready_after_simulation,
            "newly_ready_count": max(ready_after_simulation - baseline_ready_count, 0),
            "all_ready_after_simulation": ready_after_simulation == len(rows) if rows else False,
        },
        "partners": rows,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Partner Activation Simulation Matrix",
        "",
        f"- partner_count: {summary.get('partner_count')}",
        f"- ready_after_simulation_count: {summary.get('ready_after_simulation_count')}",
        f"- all_ready_after_simulation: {summary.get('all_ready_after_simulation')}",
        "",
        "## Partners",
    ]
    for row in payload.get("partners") or []:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- {row.get('tenant_id')} / {row.get('offering_id')}: "
            f"current_missing={', '.join(row.get('current_missing_required_inputs') or []) or '(none)'} "
            f"simulated_decision={row.get('simulated_decision')} "
            f"simulated_remaining={', '.join(row.get('simulated_remaining_required_inputs') or []) or '(none)'}"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate minimal missing-input injection for all current partner tenants")
    parser.add_argument("--registry", default=str(ROOT / "tenant_config" / "tenant_registry.json"))
    parser.add_argument("--channels", default=str(ROOT / "tenant_config" / "channel_profiles.json"))
    parser.add_argument("--env-file", default=str(ROOT / ".env"))
    parser.add_argument("--json", default="logs/partner_activation_simulation_matrix_latest.json")
    parser.add_argument("--md", default="logs/partner_activation_simulation_matrix_latest.md")
    args = parser.parse_args()

    payload = build_simulation_matrix(
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
    print(json.dumps({"ok": True, "json": str(json_path), "md": str(md_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
