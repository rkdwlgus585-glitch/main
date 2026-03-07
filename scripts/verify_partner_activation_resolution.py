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
    payload: Dict[str, Any] = {}
    try:
        parsed = json.loads(stdout_text) if stdout_text.strip() else {}
        payload = parsed if isinstance(parsed, dict) else {}
    except Exception:
        payload = {}
    return {
        "ok": proc.returncode == 0,
        "returncode": int(proc.returncode),
        "stdout": stdout_text,
        "stderr": proc.stderr or "",
        "json": payload,
    }


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


def _has_step(payload: Dict[str, Any], name: str) -> bool:
    steps = payload.get("steps") if isinstance(payload.get("steps"), list) else []
    for row in steps:
        if isinstance(row, dict) and str(row.get("name") or "").strip() == name:
            return True
    return False


def _build_preview_for_scope(*, offering_id: str, tenant_id: str, channel_id: str, host: str, brand_name: str, proof_url: str, api_key_value: str, smoke_base_url: str = "", registry_path: str = "", channels_path: str = "", env_path: str = "") -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="partner_resolution_preview_") as td:
        json_path = Path(td) / "preview.json"
        cmd = _py_cmd(
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
                "--proof-url",
                proof_url,
                "--api-key-value",
                api_key_value,
                "--json",
                str(json_path),
                "--md",
                str(Path(td) / "preview.md"),
            ]
        )
        if smoke_base_url:
            cmd.extend(["--smoke-base-url", smoke_base_url])
        if registry_path:
            cmd.extend(["--registry", registry_path])
        if channels_path:
            cmd.extend(["--channels", channels_path])
        if env_path:
            cmd.extend(["--env-file", env_path])
        result = _run(cmd)
        if not result["ok"]:
            return {}
        return _load_json(json_path)


def _build_flow_for_inputs(*, offering_id: str, tenant_id: str, channel_id: str, host: str, brand_name: str, proof_url: str, api_key_value: str, approve_source: bool, smoke_base_url: str = "", registry_path: str = "", channels_path: str = "", env_path: str = "") -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="partner_resolution_flow_") as td:
        json_path = Path(td) / "flow.json"
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
                "--proof-url",
                proof_url,
                "--api-key-value",
                api_key_value,
                "--report",
                str(json_path),
            ]
        )
        if approve_source:
            cmd.append("--approve-source")
        if smoke_base_url:
            cmd.extend(["--smoke-base-url", smoke_base_url, "--run-smoke-in-dry-run"])
        if registry_path:
            cmd.extend(["--registry", registry_path])
        if channels_path:
            cmd.extend(["--channels", channels_path])
        if env_path:
            cmd.extend(["--env-file", env_path])
        result = _run(cmd)
        # Non-zero is valid here because unresolved blockers are part of the comparison.
        payload = _load_json(json_path)
        if payload:
            payload["_command_ok"] = bool(result["ok"])
        return payload


def build_resolution_report(
    *,
    offering_id: str,
    tenant_id: str,
    channel_id: str,
    host: str,
    brand_name: str,
    scenario: str,
    proof_url: str,
    api_key_value: str,
    smoke_base_url: str = "",
    registry_path: str = "",
    channels_path: str = "",
    env_path: str = "",
) -> Dict[str, Any]:
    preview = _build_preview_for_scope(
        offering_id=offering_id,
        tenant_id=tenant_id,
        channel_id=channel_id,
        host=host,
        brand_name=brand_name,
        proof_url=proof_url,
        api_key_value=api_key_value,
        smoke_base_url=smoke_base_url,
        registry_path=registry_path,
        channels_path=channels_path,
        env_path=env_path,
    )
    scenarios = preview.get("scenarios") if isinstance(preview.get("scenarios"), list) else []
    scenario_map = {
        str(row.get("scenario") or "").strip(): row
        for row in scenarios
        if isinstance(row, dict) and str(row.get("scenario") or "").strip()
    }
    selected_name = scenario or str((preview.get("recommended_path") or {}).get("scenario") or "").strip()
    selected = scenario_map.get(selected_name, {})
    selected_remaining = _as_list((selected or {}).get("remaining_required_inputs"))

    scenario_proof = proof_url if selected_name in {"proof_only", "proof_and_key", "proof_key_and_approval", "proof_key_approval_and_smoke"} else ""
    scenario_key = api_key_value if selected_name in {"proof_and_key", "proof_key_and_approval", "proof_key_approval_and_smoke"} else ""
    scenario_approval = selected_name in {"proof_key_and_approval", "proof_key_approval_and_smoke"}
    flow = _build_flow_for_inputs(
        offering_id=offering_id,
        tenant_id=tenant_id,
        channel_id=channel_id,
        host=host,
        brand_name=brand_name,
        proof_url=scenario_proof,
        api_key_value=scenario_key,
        approve_source=scenario_approval,
        smoke_base_url=smoke_base_url if selected_name == "proof_key_approval_and_smoke" else "",
        registry_path=registry_path,
        channels_path=channels_path,
        env_path=env_path,
    )
    handoff = flow.get("handoff") if isinstance(flow.get("handoff"), dict) else {}
    actual_remaining = _as_list(handoff.get("remaining_required_inputs"))
    actual_resolved = _as_list(handoff.get("resolved_inputs"))
    expected_set = set(selected_remaining)
    actual_set = set(actual_remaining)
    preview_ok = len(scenarios) > 0
    selected_found = selected_name != "" and bool(selected)
    activation_step_found = _has_step(flow, "activate_partner_tenant")
    ok = preview_ok and selected_found and activation_step_found and actual_set == expected_set

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scope": {
            "offering_id": offering_id,
            "tenant_id": tenant_id,
            "channel_id": channel_id,
            "host": host,
            "brand_name": brand_name,
        },
        "scenario": {
            "selected": selected_name,
            "preview_expected_remaining_required_inputs": selected_remaining,
            "preview_expected_resolved_inputs": _as_list((selected or {}).get("resolved_inputs")),
        },
        "actual": {
            "remaining_required_inputs": actual_remaining,
            "resolved_inputs": actual_resolved,
            "command_ok": bool(flow.get("_command_ok")),
        },
        "summary": {
            "ok": ok,
            "preview_ok": preview_ok,
            "selected_found": selected_found,
            "activation_step_found": activation_step_found,
            "matches_preview_expected_remaining": actual_set == expected_set,
            "missing_vs_preview": sorted(expected_set - actual_set),
            "extra_vs_preview": sorted(actual_set - expected_set),
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    scope = payload.get("scope") if isinstance(payload.get("scope"), dict) else {}
    scenario = payload.get("scenario") if isinstance(payload.get("scenario"), dict) else {}
    actual = payload.get("actual") if isinstance(payload.get("actual"), dict) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Partner Activation Resolution Verification",
        "",
        f"- offering_id: {scope.get('offering_id')}",
        f"- tenant_id: {scope.get('tenant_id')}",
        f"- channel_id: {scope.get('channel_id')}",
        f"- host: {scope.get('host')}",
        f"- scenario: {scenario.get('selected')}",
        "",
        "## Preview Expectation",
        f"- remaining_required_inputs: {', '.join(scenario.get('preview_expected_remaining_required_inputs') or []) or '(none)'}",
        f"- resolved_inputs: {', '.join(scenario.get('preview_expected_resolved_inputs') or []) or '(none)'}",
        "",
        "## Actual Flow Result",
        f"- remaining_required_inputs: {', '.join(actual.get('remaining_required_inputs') or []) or '(none)'}",
        f"- resolved_inputs: {', '.join(actual.get('resolved_inputs') or []) or '(none)'}",
        f"- command_ok: {actual.get('command_ok')}",
        "",
        "## Summary",
        f"- ok: {summary.get('ok')}",
        f"- preview_ok: {summary.get('preview_ok')}",
        f"- selected_found: {summary.get('selected_found')}",
        f"- activation_step_found: {summary.get('activation_step_found')}",
        f"- matches_preview_expected_remaining: {summary.get('matches_preview_expected_remaining')}",
        f"- missing_vs_preview: {', '.join(summary.get('missing_vs_preview') or []) or '(none)'}",
        f"- extra_vs_preview: {', '.join(summary.get('extra_vs_preview') or []) or '(none)'}",
    ]
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify that a partner input scenario produces the same remaining inputs as preview predicted")
    parser.add_argument("--offering-id", required=True)
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--channel-id", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--brand-name", required=True)
    parser.add_argument("--scenario", default="")
    parser.add_argument("--proof-url", default="https://example.com/partner-contract")
    parser.add_argument("--api-key-value", default="preview-test-key")
    parser.add_argument("--smoke-base-url", default="")
    parser.add_argument("--registry", default="")
    parser.add_argument("--channels", default="")
    parser.add_argument("--env-file", default="")
    parser.add_argument("--json", default="logs/partner_activation_resolution_latest.json")
    parser.add_argument("--md", default="logs/partner_activation_resolution_latest.md")
    args = parser.parse_args()

    payload = build_resolution_report(
        offering_id=str(args.offering_id),
        tenant_id=str(args.tenant_id),
        channel_id=str(args.channel_id),
        host=str(args.host),
        brand_name=str(args.brand_name),
        scenario=str(args.scenario),
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
    print(json.dumps({"ok": True, "json": str(json_path), "md": str(md_path), "summary": payload.get("summary")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
