#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]


def _python_exe() -> str:
    return sys.executable or "py -3"


def _run(script: Path) -> Dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [_python_exe(), str(script)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "script": str(script),
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def refresh_wordpress_platform_artifacts() -> Dict[str, Any]:
    scripts = [
        ROOT / "scripts" / "generate_wordpress_platform_strategy.py",
        ROOT / "scripts" / "generate_wordpress_platform_ia.py",
        ROOT / "scripts" / "scaffold_wp_surface_lab_runtime.py",
        ROOT / "scripts" / "prepare_wp_surface_lab_php_runtime.py",
        ROOT / "scripts" / "bootstrap_wp_surface_lab_php_fallback.py",
        ROOT / "scripts" / "validate_wp_surface_lab_runtime.py",
        ROOT / "scripts" / "generate_private_engine_proxy_spec.py",
        ROOT / "scripts" / "generate_listing_platform_bridge_policy.py",
        ROOT / "scripts" / "generate_co_listing_bridge_snippets.py",
        ROOT / "scripts" / "generate_co_listing_bridge_operator_checklist.py",
        ROOT / "scripts" / "generate_co_listing_live_injection_plan.py",
        ROOT / "scripts" / "generate_co_listing_injection_bundle.py",
        ROOT / "scripts" / "generate_co_listing_bridge_apply_packet.py",
        ROOT / "scripts" / "generate_kr_proxy_server_matrix.py",
        ROOT / "scripts" / "generate_kr_proxy_server_bundle.py",
        ROOT / "scripts" / "generate_kr_reverse_proxy_cutover.py",
        ROOT / "scripts" / "generate_yangdo_recommendation_qa_matrix.py",
        ROOT / "scripts" / "generate_yangdo_recommendation_precision_matrix.py",
        ROOT / "scripts" / "generate_yangdo_recommendation_diversity_audit.py",
        ROOT / "scripts" / "generate_yangdo_recommendation_contract_audit.py",
        ROOT / "scripts" / "generate_widget_rental_catalog.py",
        ROOT / "scripts" / "generate_yangdo_recommendation_bridge_packet.py",
        ROOT / "scripts" / "generate_yangdo_service_copy_packet.py",
        ROOT / "scripts" / "generate_permit_service_copy_packet.py",
        ROOT / "scripts" / "generate_permit_service_alignment_audit.py",
        ROOT / "scripts" / "scaffold_wp_platform_blueprints.py",
        ROOT / "scripts" / "apply_wp_surface_lab_blueprints.py",
        ROOT / "scripts" / "generate_wordpress_staging_apply_plan.py",
        ROOT / "scripts" / "run_wp_surface_lab_apply_verify_cycle.py",
        ROOT / "scripts" / "verify_wp_surface_lab_pages.py",
        ROOT / "scripts" / "generate_wordpress_platform_encoding_audit.py",
        ROOT / "scripts" / "generate_wordpress_platform_ux_audit.py",
        ROOT / "scripts" / "generate_yangdo_recommendation_ux_packet.py",
        ROOT / "scripts" / "generate_yangdo_recommendation_alignment_audit.py",
        ROOT / "scripts" / "generate_kr_live_apply_packet.py",
        ROOT / "scripts" / "generate_kr_live_operator_checklist.py",
        ROOT / "scripts" / "generate_program_improvement_loop.py",
        ROOT / "scripts" / "generate_operations_packet.py",
    ]
    steps: List[Dict[str, Any]] = []
    ok = True
    for script in scripts:
        result = _run(script)
        steps.append(result)
        if not result["ok"]:
            ok = False
            break
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": ok,
        "step_count": len(steps),
        "steps": steps,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# WordPress Platform Artifact Refresh",
        "",
        f"- ok: {payload.get('ok')}",
        f"- step_count: {payload.get('step_count')}",
        "",
        "## Steps",
    ]
    for row in payload.get("steps", []):
        lines.append(f"- {row.get('script')}: ok={row.get('ok')} returncode={row.get('returncode')}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh dependent WordPress platform artifacts in a safe sequential order.")
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wordpress_platform_refresh_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wordpress_platform_refresh_latest.md")
    args = parser.parse_args()

    payload = refresh_wordpress_platform_artifacts()
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
