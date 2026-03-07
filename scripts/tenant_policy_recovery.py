#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "tenant_config" / "tenant_registry.json"
DEFAULT_REPORT = ROOT / "logs" / "tenant_policy_recovery_latest.json"


def _load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _index_tenants(registry: Dict[str, object]) -> Tuple[Dict[str, Dict[str, object]], List[Dict[str, object]]]:
    tenants_raw = registry.get("tenants")
    if not isinstance(tenants_raw, list):
        return {}, []
    by_id: Dict[str, Dict[str, object]] = {}
    for row in tenants_raw:
        if not isinstance(row, dict):
            continue
        tenant_id = str(row.get("tenant_id") or "").strip().lower()
        if not tenant_id:
            continue
        by_id[tenant_id] = row
    return by_id, tenants_raw


def _has_blocked_tokens(tenant: Dict[str, object]) -> bool:
    raw = tenant.get("blocked_api_tokens")
    return isinstance(raw, list) and len(raw) > 0


def _is_disabled(tenant: Dict[str, object]) -> bool:
    value = tenant.get("enabled")
    if value is None:
        return False
    if isinstance(value, bool):
        return not value
    text = str(value).strip().lower()
    if text in {"0", "false", "no", "off", "n"}:
        return True
    return False


def _select_target_ids(
    tenants_by_id: Dict[str, Dict[str, object]],
    *,
    tenant_ids: Set[str],
    all_disabled: bool,
    with_blocked_keys: bool,
) -> List[str]:
    selected: List[str] = []
    seen: Set[str] = set()

    for tid in sorted(tenant_ids):
        if tid in tenants_by_id and tid not in seen:
            selected.append(tid)
            seen.add(tid)

    if all_disabled or with_blocked_keys:
        for tid in sorted(tenants_by_id.keys()):
            tenant = tenants_by_id[tid]
            if tid in seen:
                continue
            if all_disabled and _is_disabled(tenant):
                selected.append(tid)
                seen.add(tid)
                continue
            if with_blocked_keys and _has_blocked_tokens(tenant):
                selected.append(tid)
                seen.add(tid)

    return selected


def run_recovery(
    *,
    registry_path: Path,
    report_path: Path,
    tenant_ids: Set[str],
    all_disabled: bool,
    with_blocked_keys: bool,
    enable_tenant: bool,
    clear_blocked_keys: bool,
    clear_block_metadata: bool,
    apply_changes: bool,
    strict: bool,
) -> int:
    if not registry_path.exists():
        raise FileNotFoundError(f"registry not found: {registry_path}")

    registry = _load_json(registry_path)
    tenants_by_id, _ = _index_tenants(registry)
    target_ids = _select_target_ids(
        tenants_by_id,
        tenant_ids=tenant_ids,
        all_disabled=bool(all_disabled),
        with_blocked_keys=bool(with_blocked_keys),
    )

    rows: List[Dict[str, object]] = []
    changed_count = 0
    would_change_count = 0

    for tid in target_ids:
        tenant = tenants_by_id[tid]
        before_enabled = bool(tenant.get("enabled", True))
        before_blocked = list(tenant.get("blocked_api_tokens", [])) if isinstance(tenant.get("blocked_api_tokens"), list) else []
        before_reason = str(tenant.get("blocked_reason", "") or "")
        before_at = str(tenant.get("blocked_at", "") or "")

        row = {
            "tenant_id": tid,
            "before": {
                "enabled": before_enabled,
                "blocked_token_count": len(before_blocked),
                "blocked_reason": before_reason,
                "blocked_at": before_at,
            },
            "after": {
                "enabled": before_enabled,
                "blocked_token_count": len(before_blocked),
                "blocked_reason": before_reason,
                "blocked_at": before_at,
            },
            "changed_fields": [],
            "applied": False,
        }

        pending_changed = False

        if enable_tenant and not before_enabled:
            row["after"]["enabled"] = True
            row["changed_fields"].append("enabled")
            pending_changed = True

        if clear_blocked_keys and len(before_blocked) > 0:
            row["after"]["blocked_token_count"] = 0
            row["changed_fields"].append("blocked_api_tokens")
            pending_changed = True

        if clear_block_metadata and (before_reason or before_at):
            row["after"]["blocked_reason"] = ""
            row["after"]["blocked_at"] = ""
            if before_reason:
                row["changed_fields"].append("blocked_reason")
            if before_at:
                row["changed_fields"].append("blocked_at")
            pending_changed = True

        if pending_changed:
            would_change_count += 1
            if apply_changes:
                if "enabled" in row["changed_fields"]:
                    tenant["enabled"] = True
                if "blocked_api_tokens" in row["changed_fields"]:
                    tenant["blocked_api_tokens"] = []
                if "blocked_reason" in row["changed_fields"]:
                    tenant.pop("blocked_reason", None)
                if "blocked_at" in row["changed_fields"]:
                    tenant.pop("blocked_at", None)
                row["applied"] = True
                changed_count += 1

        rows.append(row)

    if apply_changes and changed_count > 0:
        _save_json(registry_path, registry)

    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "registry": str(registry_path),
        "options": {
            "tenant_ids": sorted(tenant_ids),
            "all_disabled": bool(all_disabled),
            "with_blocked_keys": bool(with_blocked_keys),
            "enable_tenant": bool(enable_tenant),
            "clear_blocked_keys": bool(clear_blocked_keys),
            "clear_block_metadata": bool(clear_block_metadata),
            "apply_changes": bool(apply_changes),
        },
        "summary": {
            "target_count": len(target_ids),
            "would_change_count": int(would_change_count),
            "changed_count": int(changed_count),
        },
        "targets": rows,
    }
    _save_json(report_path, payload)
    print(json.dumps({"ok": True, "report": str(report_path), "summary": payload["summary"]}, ensure_ascii=False))

    if strict and (len(target_ids) == 0 or (bool(apply_changes) and changed_count == 0)):
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover tenant policy restrictions (enable/clear blocked keys)")
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--tenant-id", action="append", default=[])
    parser.add_argument("--all-disabled", action="store_true", default=False)
    parser.add_argument("--with-blocked-keys", action="store_true", default=False)
    parser.add_argument("--enable-tenant", action="store_true", default=False)
    parser.add_argument("--clear-blocked-keys", action="store_true", default=False)
    parser.add_argument("--clear-block-metadata", action="store_true", default=False)
    parser.add_argument("--apply", action="store_true", default=False)
    parser.add_argument("--strict", action="store_true", default=False)
    args = parser.parse_args()

    tenant_ids: Set[str] = {
        str(item or "").strip().lower()
        for item in list(args.tenant_id or [])
        if str(item or "").strip()
    }
    if not tenant_ids and not bool(args.all_disabled) and not bool(args.with_blocked_keys):
        # Safe default: preview disabled tenants.
        args.all_disabled = True
        args.with_blocked_keys = True

    if not (bool(args.enable_tenant) or bool(args.clear_blocked_keys) or bool(args.clear_block_metadata)):
        # Safe default for operator: full recovery package.
        args.enable_tenant = True
        args.clear_blocked_keys = True
        args.clear_block_metadata = True

    return run_recovery(
        registry_path=Path(str(args.registry)).resolve(),
        report_path=Path(str(args.report)).resolve(),
        tenant_ids=tenant_ids,
        all_disabled=bool(args.all_disabled),
        with_blocked_keys=bool(args.with_blocked_keys),
        enable_tenant=bool(args.enable_tenant),
        clear_blocked_keys=bool(args.clear_blocked_keys),
        clear_block_metadata=bool(args.clear_block_metadata),
        apply_changes=bool(args.apply),
        strict=bool(args.strict),
    )


if __name__ == "__main__":
    raise SystemExit(main())
