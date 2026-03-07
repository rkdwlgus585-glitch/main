#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from security_http import parse_key_values


DEFAULT_REPORT = ROOT / "logs" / "tenant_usage_billing_latest.json"
DEFAULT_REGISTRY = ROOT / "tenant_config" / "tenant_registry.json"
DEFAULT_THRESHOLDS = ROOT / "tenant_config" / "plan_thresholds.json"
DEFAULT_OUTPUT = ROOT / "logs" / "tenant_policy_actions_latest.json"
DEFAULT_ENV = ROOT / ".env"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _save_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.exists():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = str(raw or "").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip().lstrip("\ufeff")] = value.strip().strip('"').strip("'")
    return out


def _to_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "y"}:
        return True
    if text in {"0", "false", "no", "off", "n"}:
        return False
    return default


def _to_set_of_str(values: object) -> Set[str]:
    out: Set[str] = set()
    if isinstance(values, list):
        for item in values:
            key = str(item or "").strip().lower()
            if key:
                out.add(key)
    return out


def _index_tenants(registry: Dict[str, object]) -> Tuple[Dict[str, Dict[str, object]], List[Dict[str, object]]]:
    tenants_raw = registry.get("tenants")
    if not isinstance(tenants_raw, list):
        return {}, []
    by_id: Dict[str, Dict[str, object]] = {}
    for tenant in tenants_raw:
        if not isinstance(tenant, dict):
            continue
        tenant_id = str(tenant.get("tenant_id") or "").strip().lower()
        if not tenant_id:
            continue
        by_id[tenant_id] = tenant
    return by_id, tenants_raw


def _collect_tenant_tokens(tenant: Dict[str, object], env_values: Dict[str, str]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    raw_envs = tenant.get("api_key_envs") or []
    if not isinstance(raw_envs, list):
        return out
    for name in raw_envs:
        env_name = str(name or "").strip()
        if not env_name:
            continue
        env_raw = str(env_values.get(env_name, "") or "").strip()
        for token in parse_key_values(env_raw):
            tok = str(token or "").strip()
            if not tok or tok in seen:
                continue
            seen.add(tok)
            out.append(tok)
    return out


def _upsert_blocked_tokens(tenant: Dict[str, object], tokens: List[str]) -> int:
    existing_raw = tenant.get("blocked_api_tokens") or []
    existing: List[str] = []
    seen: Set[str] = set()
    if isinstance(existing_raw, list):
        for item in existing_raw:
            tok = str(item or "").strip()
            if tok and tok not in seen:
                seen.add(tok)
                existing.append(tok)

    added = 0
    for token in tokens:
        tok = str(token or "").strip()
        if not tok or tok in seen:
            continue
        seen.add(tok)
        existing.append(tok)
        added += 1

    if added > 0:
        tenant["blocked_api_tokens"] = existing
    elif "blocked_api_tokens" not in tenant and existing:
        tenant["blocked_api_tokens"] = existing

    return added


def build_policy_actions(
    *,
    report: Dict[str, object],
    registry: Dict[str, object],
    auto_upgrade: bool,
    auto_disable: bool,
    auto_block_keys: bool,
    disable_actions: Set[str],
    disable_min_usage_events: int,
    protected_tenants: Set[str],
    env_values: Dict[str, str],
    apply_registry: bool,
) -> Tuple[Dict[str, object], bool]:
    tenants_by_id, _tenants_list = _index_tenants(registry)

    actions: List[Dict[str, object]] = []
    applied_changes = 0

    report_tenants = report.get("tenants") if isinstance(report, dict) else []
    if not isinstance(report_tenants, list):
        report_tenants = []

    min_events = max(1, int(disable_min_usage_events or 1))

    for row in report_tenants:
        if not isinstance(row, dict):
            continue

        tenant_id = str(row.get("tenant_id") or "").strip().lower()
        rec = str(row.get("recommended_action") or "normal").strip().lower()
        usage_events = int(row.get("usage_events") or 0)

        if rec == "normal":
            continue

        base = {
            "tenant_id": tenant_id,
            "display_name": str(row.get("display_name") or tenant_id),
            "recommended_action": rec,
            "reason": str(row.get("action_reason") or ""),
            "usage_events": usage_events,
            "estimated_tokens": int(row.get("estimated_tokens") or 0),
            "upgrade_target": str(row.get("upgrade_target") or "").strip().lower(),
            "applied": False,
            "severity": "medium",
            "policy_action": "notify",
            "message": "",
            "protected_tenant": tenant_id in protected_tenants,
            "blocked_tokens_added": 0,
        }

        if rec == "usage_warning":
            base["severity"] = "low"
            base["policy_action"] = "notify_warning"
            base["message"] = "사용량 경고 구간 도달"
            actions.append(base)
            continue

        if rec in {"upgrade_or_overage_charge", "review_limit_exceeded"}:
            target = str(base["upgrade_target"] or "").strip().lower()
            tenant = tenants_by_id.get(tenant_id)
            if auto_upgrade and apply_registry and tenant is not None and target:
                old_plan = str(tenant.get("plan") or "").strip().lower()
                if old_plan != target:
                    tenant["plan"] = target
                    base["applied"] = True
                    base["policy_action"] = "upgrade_plan"
                    base["message"] = f"plan 자동 승급: {old_plan} -> {target}"
                    applied_changes += 1
                else:
                    base["policy_action"] = "notify"
                    base["message"] = "이미 목표 plan 상태"
            else:
                base["policy_action"] = "notify_upgrade_needed"
                base["message"] = "승급 또는 초과요금 정책 검토 필요"
            actions.append(base)
            continue

        if rec in disable_actions:
            base["severity"] = "high"
            tenant = tenants_by_id.get(tenant_id)
            if tenant_id in protected_tenants:
                base["policy_action"] = "protected_tenant_skip"
                base["message"] = "보호 테넌트로 자동 제한 제외"
                actions.append(base)
                continue
            if usage_events < min_events:
                base["policy_action"] = "below_disable_threshold"
                base["message"] = f"자동 제한 최소 이벤트 미만({usage_events}<{min_events})"
                actions.append(base)
                continue

            if auto_disable and apply_registry and tenant is not None:
                was_enabled = _to_bool(tenant.get("enabled"), True)
                if was_enabled:
                    tenant["enabled"] = False
                    tenant["blocked_at"] = _now()
                    tenant["blocked_reason"] = rec
                    applied_changes += 1
                added_tokens = 0
                if auto_block_keys:
                    tokens = _collect_tenant_tokens(tenant, env_values)
                    if tokens:
                        added_tokens = _upsert_blocked_tokens(tenant, tokens)
                        if added_tokens > 0:
                            applied_changes += 1
                base["applied"] = True
                base["policy_action"] = "disable_tenant"
                base["blocked_tokens_added"] = int(added_tokens)
                if auto_block_keys:
                    base["message"] = f"tenant 자동 제한 + 키 차단({added_tokens}개 추가)"
                else:
                    base["message"] = "tenant 자동 제한 적용"
            else:
                base["policy_action"] = "notify_disable_needed"
                base["message"] = "자동 제한 조건 충족: 수동 승인 필요"
            actions.append(base)
            continue

        if rec == "investigate_unknown_host":
            base["severity"] = "high"
            base["policy_action"] = "investigate"
            base["message"] = "host/origin 매핑 누락 원인 분석 필요"
            actions.append(base)
            continue

        base["policy_action"] = "notify_unknown_action"
        base["message"] = "정의되지 않은 권고 액션"
        actions.append(base)

    unresolved = [
        a
        for a in actions
        if str(a.get("recommended_action")) not in {"normal", "usage_warning"} and not bool(a.get("applied"))
    ]

    payload = {
        "generated_at": _now(),
        "options": {
            "auto_upgrade": bool(auto_upgrade),
            "auto_disable": bool(auto_disable),
            "auto_block_keys": bool(auto_block_keys),
            "disable_actions": sorted(disable_actions),
            "disable_min_usage_events": int(min_events),
            "protected_tenants": sorted(protected_tenants),
            "apply_registry": bool(apply_registry),
        },
        "summary": {
            "action_count": len(actions),
            "applied_change_count": int(applied_changes),
            "warning_count": sum(1 for a in actions if a.get("policy_action") == "notify_warning"),
            "high_severity_count": sum(1 for a in actions if a.get("severity") == "high"),
            "unresolved_action_count": len(unresolved),
        },
        "actions": actions,
    }

    return payload, applied_changes > 0


def run(
    *,
    report_path: Path,
    registry_path: Path,
    thresholds_path: Path,
    env_path: Path,
    output_path: Path,
    auto_upgrade_override: Optional[bool],
    auto_disable_override: Optional[bool],
    auto_block_keys_override: Optional[bool],
    disable_min_events_override: Optional[int],
    protected_tenants_override: Optional[Set[str]],
    apply_registry: bool,
    strict: bool,
) -> int:
    if not report_path.exists():
        raise FileNotFoundError(f"report not found: {report_path}")
    if not registry_path.exists():
        raise FileNotFoundError(f"registry not found: {registry_path}")

    report = _load_json(report_path)
    registry = _load_json(registry_path)

    auto_upgrade = False
    auto_disable = False
    auto_block_keys = False
    disable_actions: Set[str] = {"disabled_tenant_activity"}
    disable_min_events = 3
    protected_tenants: Set[str] = {"seoul_main"}

    if thresholds_path.exists():
        thresholds = _load_json(thresholds_path)
        policy = thresholds.get("policy") if isinstance(thresholds, dict) else {}
        if isinstance(policy, dict):
            auto_upgrade = _to_bool(policy.get("auto_upgrade"), False)
            auto_disable = _to_bool(policy.get("auto_disable"), False)
            auto_block_keys = _to_bool(policy.get("auto_block_keys_on_disable"), False)
            configured_disable_actions = _to_set_of_str(policy.get("auto_disable_actions"))
            if configured_disable_actions:
                disable_actions = configured_disable_actions
            try:
                disable_min_events = max(1, int(policy.get("auto_disable_min_usage_events") or 3))
            except Exception:
                disable_min_events = 3
            configured_protected = _to_set_of_str(policy.get("protected_tenants"))
            if configured_protected:
                protected_tenants = configured_protected

    if auto_upgrade_override is not None:
        auto_upgrade = bool(auto_upgrade_override)
    if auto_disable_override is not None:
        auto_disable = bool(auto_disable_override)
    if auto_block_keys_override is not None:
        auto_block_keys = bool(auto_block_keys_override)
    if disable_min_events_override is not None:
        disable_min_events = max(1, int(disable_min_events_override))
    if protected_tenants_override is not None:
        protected_tenants = set(protected_tenants_override)

    env_values = _load_env_file(env_path)
    env_values.update({k: v for k, v in os.environ.items() if isinstance(v, str)})

    payload, changed = build_policy_actions(
        report=report,
        registry=registry,
        auto_upgrade=auto_upgrade,
        auto_disable=auto_disable,
        auto_block_keys=auto_block_keys,
        disable_actions=disable_actions,
        disable_min_usage_events=disable_min_events,
        protected_tenants=protected_tenants,
        env_values=env_values,
        apply_registry=bool(apply_registry),
    )

    if apply_registry and changed:
        _save_json(registry_path, registry)

    _save_json(output_path, payload)
    print(json.dumps({"ok": True, "report": str(output_path), "summary": payload.get("summary")}, ensure_ascii=False))

    unresolved = int(payload["summary"]["unresolved_action_count"])
    if strict and unresolved > 0:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply tenant threshold policy actions from usage/billing report")
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    parser.add_argument("--thresholds", default=str(DEFAULT_THRESHOLDS))
    parser.add_argument("--env-file", default=str(DEFAULT_ENV))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))

    parser.add_argument("--auto-upgrade", action="store_true", default=False)
    parser.add_argument("--no-auto-upgrade", action="store_true", default=False)
    parser.add_argument("--auto-disable", action="store_true", default=False)
    parser.add_argument("--no-auto-disable", action="store_true", default=False)
    parser.add_argument("--auto-block-keys", action="store_true", default=False)
    parser.add_argument("--no-auto-block-keys", action="store_true", default=False)

    parser.add_argument("--disable-min-events", type=int, default=0)
    parser.add_argument("--protected-tenant", action="append", default=[])

    parser.add_argument("--apply-registry", action="store_true", default=False)
    parser.add_argument("--strict", action="store_true", default=False)
    args = parser.parse_args()

    if bool(args.auto_upgrade) and bool(args.no_auto_upgrade):
        raise ValueError("--auto-upgrade and --no-auto-upgrade cannot be used together")
    if bool(args.auto_disable) and bool(args.no_auto_disable):
        raise ValueError("--auto-disable and --no-auto-disable cannot be used together")
    if bool(args.auto_block_keys) and bool(args.no_auto_block_keys):
        raise ValueError("--auto-block-keys and --no-auto-block-keys cannot be used together")

    auto_upgrade_override: Optional[bool] = None
    auto_disable_override: Optional[bool] = None
    auto_block_keys_override: Optional[bool] = None

    if bool(args.auto_upgrade):
        auto_upgrade_override = True
    elif bool(args.no_auto_upgrade):
        auto_upgrade_override = False

    if bool(args.auto_disable):
        auto_disable_override = True
    elif bool(args.no_auto_disable):
        auto_disable_override = False

    if bool(args.auto_block_keys):
        auto_block_keys_override = True
    elif bool(args.no_auto_block_keys):
        auto_block_keys_override = False

    protected_override: Optional[Set[str]] = None
    if isinstance(args.protected_tenant, list) and args.protected_tenant:
        protected_override = {
            str(item or "").strip().lower()
            for item in args.protected_tenant
            if str(item or "").strip()
        }

    disable_min_events_override: Optional[int] = None
    if int(args.disable_min_events or 0) > 0:
        disable_min_events_override = int(args.disable_min_events)

    return run(
        report_path=Path(str(args.report)).resolve(),
        registry_path=Path(str(args.registry)).resolve(),
        thresholds_path=Path(str(args.thresholds)).resolve(),
        env_path=Path(str(args.env_file)).resolve(),
        output_path=Path(str(args.output)).resolve(),
        auto_upgrade_override=auto_upgrade_override,
        auto_disable_override=auto_disable_override,
        auto_block_keys_override=auto_block_keys_override,
        disable_min_events_override=disable_min_events_override,
        protected_tenants_override=protected_override,
        apply_registry=bool(args.apply_registry),
        strict=bool(args.strict),
    )


if __name__ == "__main__":
    raise SystemExit(main())
