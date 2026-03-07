#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_tenant_onboarding import DEFAULT_CHANNELS, DEFAULT_REGISTRY, _load_env_file, _load_json, validate_registry
from scripts.verify_calculator_runtime import _find_chrome_exe

DEFAULT_REPORT = ROOT / "logs" / "live_release_readiness_latest.json"
DEFAULT_ENV = ROOT / ".env"


def _find_row(rows, key: str, value: str) -> Dict[str, Any]:
    wanted = str(value or "").strip().lower()
    for row in rows or []:
        if str((row or {}).get(key) or "").strip().lower() == wanted:
            return dict(row)
    return {}


def _collect_scoped_message_codes(report: Dict[str, Any], *, level: str, scoped_ids: set[str]) -> list[str]:
    rows = report.get(level) if isinstance(report.get(level), list) else []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        tenant_id = str(row.get("tenant_id") or "").strip().lower()
        if tenant_id and tenant_id not in scoped_ids:
            continue
        code = str(row.get("code") or "").strip()
        if code:
            out.append(code)
    return sorted({code for code in out if code})


def _build_handoff_summary(*, blockers: list[str], warnings: list[str], bundle_manifest_exists: bool, has_admin_credentials: bool, chrome_path: str) -> Dict[str, Any]:
    blocker_set = {str(x or "").strip() for x in (blockers or []) if str(x or "").strip()}
    warning_set = {str(x or "").strip() for x in (warnings or []) if str(x or "").strip()}
    next_actions: list[str] = []
    if "missing_admin_credentials" in blocker_set:
        next_actions.append("운영 관리자 계정(ADMIN_ID/ADMIN_PW) 주입")
    if "chrome_not_found" in blocker_set:
        next_actions.append("Chrome 실행 파일 경로 확인 또는 설치")
    if any(item.startswith("channel:") or item.startswith("tenant:") for item in blocker_set):
        next_actions.append("채널/테넌트 activation blocker 해소")
    if "channel_not_found" in blocker_set or "default_tenant_not_found" in blocker_set:
        next_actions.append("release 대상 channel/tenant 설정 재확인")
    if "bundle_manifest_missing_will_be_generated_on_release" in warning_set and not bundle_manifest_exists:
        next_actions.append("bundle publish 단계에서 manifest 생성 여부 확인")
    if not next_actions and blocker_set:
        next_actions.append("preflight blocker 해소 후 재실행")
    if not blocker_set:
        next_actions.append("release orchestration 진행 가능")
    return {
        "release_ready": len(blocker_set) == 0,
        "bundle_ready": bool(bundle_manifest_exists),
        "admin_ready": bool(has_admin_credentials),
        "runtime_ready": bool(chrome_path),
        "next_actions": next_actions,
    }


def build_readiness(*, channel_id: str, registry_path: str = "", channels_path: str = "", env_path: str = "") -> Dict[str, Any]:
    registry_file = Path(str(registry_path or DEFAULT_REGISTRY)).resolve()
    channels_file = Path(str(channels_path or DEFAULT_CHANNELS)).resolve()
    env_file = Path(str(env_path or DEFAULT_ENV)).resolve()
    registry = _load_json(registry_file)
    channels = _load_json(channels_file) if channels_file.exists() else {}
    env_values = _load_env_file(env_file)
    env_values.update({k: v for k, v in os.environ.items() if isinstance(v, str)})
    report = validate_registry(registry, env_values=env_values, channel_registry=channels)

    channel_id = str(channel_id or "").strip().lower()
    channel_row = _find_row(report.get("channels"), "channel_id", channel_id)
    tenant_id = str(channel_row.get("default_tenant_id") or "").strip().lower()
    tenant_row = _find_row(report.get("tenants"), "tenant_id", tenant_id)

    blockers = []
    warnings = []
    if not channel_row:
        blockers.append("channel_not_found")
    if not tenant_row:
        blockers.append("default_tenant_not_found")
    if channel_row and not bool(channel_row.get("activation_ready")):
        blockers.extend([f"channel:{x}" for x in (channel_row.get("activation_blockers") or [])])
    if tenant_row and not bool(tenant_row.get("activation_ready")):
        blockers.extend([f"tenant:{x}" for x in (tenant_row.get("activation_blockers") or [])])
    scoped_ids = {channel_id, tenant_id}
    scoped_warnings = _collect_scoped_message_codes(report, level="warnings", scoped_ids=scoped_ids)
    scoped_errors = _collect_scoped_message_codes(report, level="errors", scoped_ids=scoped_ids)
    warnings.extend(scoped_warnings)
    if scoped_errors:
        blockers.extend([f"registry:{code}" for code in scoped_errors])

    admin_id = str(env_values.get("ADMIN_ID") or "").strip()
    admin_pw = str(env_values.get("ADMIN_PW") or "").strip()
    if not admin_id or not admin_pw:
        blockers.append("missing_admin_credentials")

    chrome_path = _find_chrome_exe()
    if not chrome_path:
        blockers.append("chrome_not_found")
    bundle_manifest = ROOT / "output" / "widget" / "bundles" / channel_id / "manifest.json"
    if not bundle_manifest.exists():
        warnings.append("bundle_manifest_missing_will_be_generated_on_release")

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ok": len(blockers) == 0,
        "channel_id": channel_id,
        "tenant_id": tenant_id,
        "summary": report.get("summary", {}),
        "scoped_summary": {
            "warning_count": len(scoped_warnings),
            "error_count": len(scoped_errors),
        },
        "channel_activation_ready": channel_row.get("activation_ready") if channel_row else None,
        "tenant_activation_ready": tenant_row.get("activation_ready") if tenant_row else None,
        "bundle_manifest": str(bundle_manifest),
        "bundle_manifest_exists": bundle_manifest.exists(),
        "chrome_path": chrome_path,
        "has_admin_credentials": bool(admin_id and admin_pw),
        "blocking_issues": sorted({str(x) for x in blockers if str(x).strip()}),
        "warnings": sorted({str(x) for x in warnings if str(x).strip()}),
        "handoff": _build_handoff_summary(
            blockers=blockers,
            warnings=warnings,
            bundle_manifest_exists=bundle_manifest.exists(),
            has_admin_credentials=bool(admin_id and admin_pw),
            chrome_path=str(chrome_path or ""),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate live release readiness for Seoul widget embed deployment")
    parser.add_argument("--channel-id", default="seoul_web")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--channels", default=str(DEFAULT_CHANNELS))
    parser.add_argument("--env-file", default=str(DEFAULT_ENV))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    result = build_readiness(
        channel_id=args.channel_id,
        registry_path=args.registry,
        channels_path=args.channels,
        env_path=args.env_file,
    )
    out_path = Path(str(args.report)).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
