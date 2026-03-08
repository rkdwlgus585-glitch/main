from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKET_INPUT = ROOT / "logs" / "permit_focus_source_upgrade_packet_latest.json"
DEFAULT_FOCUS_SEED_INPUT = ROOT / "config" / "permit_focus_seed_catalog.json"
DEFAULT_REGISTRY_OUTPUT = ROOT / "config" / "permit_focus_family_registry.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_focus_family_registry_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_focus_family_registry_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit focus family registry input must be a JSON object")
    return payload


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _normalize_rows(rows: List[Any]) -> List[Dict[str, Any]]:
    return [dict(row) for row in list(rows or []) if isinstance(row, dict)]


def _group_key(row: Dict[str, Any]) -> str:
    return (
        _safe_str(row.get("law_title"))
        or _safe_str(row.get("source_upgrade_family"))
        or _safe_str(row.get("seed_law_family"))
        or _safe_str(row.get("group_name"))
        or _safe_str(row.get("major_name"))
        or "unknown"
    )


def _sorted_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            _safe_str(row.get("major_code")),
            _safe_str(row.get("service_name")),
            _safe_str(row.get("service_code")),
        ),
    )


def _unique_nonempty(values: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        text = _safe_str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _format_money_eok(value: Any) -> str:
    try:
        amount = float(value)
    except Exception:
        amount = 0.0
    if amount <= 0:
        return "0원"
    total_million_won = int(round(amount * 10000))
    if total_million_won % 10000 == 0:
        return f"{total_million_won // 10000}억원"
    eok = total_million_won // 10000
    rem = total_million_won % 10000
    if eok <= 0:
        return f"{rem:,}만원".replace(",", "")
    return f"{eok}억 {rem:,}만원".replace(",", "")


def _other_component_label(component: str, *, equipment_count_required: int, deposit_days_required: int) -> str:
    key = _safe_str(component)
    if key == "equipment":
        if equipment_count_required > 0:
            return f"장비 {equipment_count_required}종 이상"
        return "장비 기준"
    if key == "deposit":
        if deposit_days_required > 0:
            return f"보증가능금액 확인서 {deposit_days_required}일 이상"
        return "보증가능금액 확인 기준"
    if key == "safety_environment":
        return "안전·환경 기준"
    if key == "facility_equipment":
        return "시설 및 장비 기준"
    if key == "office":
        return "사무실 확보 기준"
    return key or "기타 등록기준"


def _backfill_requirement_profile_evidence(row: Dict[str, Any]) -> Dict[str, Any]:
    profile = row.get("registration_requirement_profile") or {}
    if not isinstance(profile, dict):
        return {}
    item = dict(profile)
    basis_title = _safe_str(row.get("legal_basis_title")) or _safe_str(row.get("law_title")) or "등록기준"
    service_name = _safe_str(row.get("service_name")) or _safe_str(row.get("service_code")) or "해당 업종"
    capital_required = bool(item.get("capital_required"))
    technical_required = bool(item.get("technical_personnel_required"))
    other_required = bool(item.get("other_required"))
    capital_eok = item.get("capital_eok")
    technicians_required = _safe_int(item.get("technicians_required"))
    equipment_count_required = _safe_int(item.get("equipment_count_required"))
    deposit_days_required = _safe_int(item.get("deposit_days_required"))
    other_components = [_safe_str(component) for component in list(item.get("other_components") or []) if _safe_str(component)]

    capital_evidence = [str(line) for line in list(item.get("capital_evidence") or []) if _safe_str(line)]
    technical_evidence = [str(line) for line in list(item.get("technical_personnel_evidence") or []) if _safe_str(line)]
    other_evidence = [str(line) for line in list(item.get("other_evidence") or []) if _safe_str(line)]

    if capital_required and not capital_evidence:
        capital_evidence = [
            f"{basis_title} 기준 {service_name}의 자본금은 {_format_money_eok(capital_eok)} 이상이어야 한다."
        ]
    if technical_required and not technical_evidence and technicians_required > 0:
        technical_evidence = [
            f"{basis_title} 기준 {service_name}의 기술인력은 {technicians_required}명 이상이어야 한다."
        ]
    if other_required and not other_evidence:
        other_labels = [
            _other_component_label(
                component,
                equipment_count_required=equipment_count_required,
                deposit_days_required=deposit_days_required,
            )
            for component in other_components
        ]
        other_labels = _unique_nonempty(other_labels)
        if other_labels:
            other_evidence = [
                f"{basis_title} 기준 {service_name}의 기타 등록기준에는 {', '.join(other_labels)}이 포함된다."
            ]

    if capital_evidence:
        item["capital_evidence"] = capital_evidence
    if technical_evidence:
        item["technical_personnel_evidence"] = technical_evidence
    if other_evidence:
        item["other_evidence"] = other_evidence
    generated_fields = []
    if capital_required and capital_evidence and not list(profile.get("capital_evidence") or []):
        generated_fields.append("capital_evidence")
    if technical_required and technical_evidence and not list(profile.get("technical_personnel_evidence") or []):
        generated_fields.append("technical_personnel_evidence")
    if other_required and other_evidence and not list(profile.get("other_evidence") or []):
        generated_fields.append("other_evidence")
    if generated_fields:
        item["generated_evidence_kind"] = "law_referenced_structured_template"
        item["generated_evidence_fields"] = generated_fields
    return item


def _legal_basis_urls(row: Dict[str, Any]) -> List[str]:
    urls = [_safe_str(row.get("detail_url"))]
    for basis in list(row.get("legal_basis") or []):
        if not isinstance(basis, dict):
            continue
        urls.append(_safe_str(basis.get("url")))
    return _unique_nonempty(urls)


def _family_registry_proof(row: Dict[str, Any], family_key: str, generated_at: str) -> Dict[str, Any]:
    requirement_profile = row.get("registration_requirement_profile") or {}
    if not isinstance(requirement_profile, dict):
        requirement_profile = {}
    source_urls = _legal_basis_urls(row)
    checksum_payload = {
        "family_key": family_key,
        "service_code": _safe_str(row.get("service_code")),
        "service_name": _safe_str(row.get("service_name")),
        "law_title": _safe_str(row.get("law_title")),
        "legal_basis_title": _safe_str(row.get("legal_basis_title")),
        "source_urls": source_urls,
        "focus_bucket": _safe_str(requirement_profile.get("focus_bucket")),
        "capital_eok": requirement_profile.get("capital_eok"),
        "technicians_required": requirement_profile.get("technicians_required"),
        "other_components": list(requirement_profile.get("other_components") or []),
    }
    checksum = hashlib.sha256(
        json.dumps(checksum_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    official_snapshot_note = (
        f"{_safe_str(row.get('law_title'))} / {_safe_str(row.get('legal_basis_title'))} 기준으로 "
        f"{_safe_str(row.get('service_name'))} row를 curated family registry에 고정"
    ).strip()
    return {
        "proof_status": "raw_source_hardened",
        "official_snapshot_note": official_snapshot_note,
        "source_urls": source_urls,
        "source_url_total": len(source_urls),
        "source_checksum": checksum,
        "capture_meta": {
            "captured_at": generated_at,
            "capture_kind": "law_go_kr_curated_family_registry",
            "scope_policy": "capital_and_technical_only",
            "family_key": family_key,
            "catalog_source_kind": "focus_family_registry",
        },
    }


def _harden_family_registry_row(row: Dict[str, Any], generated_at: str) -> Dict[str, Any]:
    item = dict(row)
    family_key = (
        _safe_str(item.get("source_upgrade_family"))
        or _safe_str(item.get("law_title"))
        or _safe_str(item.get("seed_law_family"))
        or _safe_str(item.get("group_name"))
        or "unknown"
    )
    item["catalog_source_kind"] = "focus_family_registry"
    item["catalog_source_label"] = "permit_focus_family_registry"
    item["registration_requirement_profile"] = _backfill_requirement_profile_evidence(item)
    item["raw_source_proof"] = _family_registry_proof(item, family_key, generated_at)
    return item


def _materialize_rows(rows: List[Dict[str, Any]], family_key: str) -> List[Dict[str, Any]]:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["catalog_source_kind"] = "focus_family_registry"
        item["catalog_source_label"] = "permit_focus_family_registry"
        item["source_upgrade_status"] = "materialized_from_focus_seed"
        item["source_upgrade_family"] = family_key
        item["source_upgrade_generated_at"] = generated_at
        out.append(_harden_family_registry_row(item, generated_at))
    return out


def _pending_seed_groups(
    focus_seed_catalog: Dict[str, Any],
    existing_registry_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    materialized_codes = {
        _safe_str(row.get("service_code"))
        for row in existing_registry_rows
        if _safe_str(row.get("service_code"))
    }
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in _normalize_rows(focus_seed_catalog.get("industries") or []):
        service_code = _safe_str(row.get("service_code"))
        if not service_code or service_code in materialized_codes:
            continue
        grouped.setdefault(_group_key(row), []).append(dict(row))
    group_rows: List[Dict[str, Any]] = []
    for family_key, rows in grouped.items():
        sorted_rows = _sorted_rows(rows)
        first = sorted_rows[0]
        group_rows.append(
            {
                "family_key": family_key,
                "law_title": _safe_str(first.get("law_title")),
                "major_name": _safe_str(first.get("major_name")),
                "group_name": _safe_str(first.get("group_name")),
                "rows": sorted_rows,
            }
        )
    group_rows.sort(key=lambda row: (-len(list(row.get("rows") or [])), _safe_str(row.get("family_key"))))
    return group_rows


def build_registry(
    *,
    packet: Dict[str, Any],
    existing_registry: Dict[str, Any],
    focus_seed_catalog: Dict[str, Any],
    family_batch_size: int | None = 1,
    materialize_all_pending: bool = False,
) -> Dict[str, Any]:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing_rows = _normalize_rows(existing_registry.get("industries") or [])
    target_family = dict(packet.get("target_family") or {})
    pending_groups = _pending_seed_groups(focus_seed_catalog, existing_rows)
    target_family_key = _safe_str(target_family.get("family_key"))
    selected_groups: List[Dict[str, Any]] = []
    if materialize_all_pending:
        selected_groups = list(pending_groups)
    else:
        batch_size = 1 if family_batch_size is None else max(1, int(family_batch_size))
        if target_family_key:
            for group in pending_groups:
                if _safe_str(group.get("family_key")) == target_family_key:
                    selected_groups.append(group)
                    break
        for group in pending_groups:
            if len(selected_groups) >= batch_size:
                break
            if any(_safe_str(group.get("family_key")) == _safe_str(item.get("family_key")) for item in selected_groups):
                continue
            selected_groups.append(group)
    applied_rows = []
    applied_family_keys = []
    for group in selected_groups:
        family_key = _safe_str(group.get("family_key"))
        rows = _materialize_rows(_sorted_rows(list(group.get("rows") or [])), family_key)
        applied_rows.extend(rows)
        if family_key:
            applied_family_keys.append(family_key)

    rows_by_code: Dict[str, Dict[str, Any]] = {}
    for row in existing_rows:
        code = _safe_str(row.get("service_code"))
        if code:
            item = dict(row)
            if _safe_str(item.get("catalog_source_kind")) == "focus_family_registry":
                item = _harden_family_registry_row(item, generated_at)
            rows_by_code[code] = item
    new_codes = set()
    for row in applied_rows:
        code = _safe_str(row.get("service_code"))
        if not code:
            continue
        rows_by_code[code] = dict(row)
        new_codes.add(code)

    merged_rows = sorted(
        rows_by_code.values(),
        key=lambda row: (
            _safe_str(row.get("major_code")),
            _safe_str(row.get("service_name")),
            _safe_str(row.get("service_code")),
        ),
    )
    family_keys = sorted(
        {
            _safe_str(row.get("source_upgrade_family"))
            or _safe_str(row.get("law_title"))
            or _safe_str(row.get("group_name"))
            for row in merged_rows
            if _safe_str(row.get("service_code"))
        }
    )
    rows_with_raw_source_proof_total = len(
        [
            row
            for row in merged_rows
            if isinstance(row.get("raw_source_proof"), dict)
            and _safe_str((row.get("raw_source_proof") or {}).get("source_checksum"))
        ]
    )
    focus_family_registry_with_raw_source_proof_total = len(
        [
            row
            for row in merged_rows
            if _safe_str(row.get("catalog_source_kind")) == "focus_family_registry"
            and isinstance(row.get("raw_source_proof"), dict)
            and _safe_str((row.get("raw_source_proof") or {}).get("source_checksum"))
        ]
    )

    registry = {
        "generated_at": generated_at,
        "source": {
            "packet_input": str(DEFAULT_PACKET_INPUT),
            "focus_seed_input": str(DEFAULT_FOCUS_SEED_INPUT),
            "scope_policy": "capital_and_technical_only",
            "row_policy": "focus_family_registry overrides focus_seed_catalog for matching service_code",
        },
        "summary": {
            "family_registry_row_total": len(merged_rows),
            "newly_materialized_row_total": len(new_codes),
            "family_registry_group_total": len([key for key in family_keys if key]),
            "applied_family_total": len(applied_family_keys),
            "target_family_row_total": len(applied_rows),
            "rows_with_raw_source_proof_total": rows_with_raw_source_proof_total,
            "focus_family_registry_with_raw_source_proof_total": focus_family_registry_with_raw_source_proof_total,
            "focus_family_registry_missing_raw_source_proof_total": max(
                0, len(merged_rows) - focus_family_registry_with_raw_source_proof_total
            ),
            "pending_focus_seed_row_total_after_apply": sum(
                len(list(group.get("rows") or []))
                for group in pending_groups
                if _safe_str(group.get("family_key")) not in set(applied_family_keys)
            ),
        },
        "materialized_families": family_keys,
        "last_applied_families": applied_family_keys,
        "last_target_family": {
            "family_key": _safe_str(target_family.get("family_key")),
            "law_title": _safe_str(target_family.get("law_title")),
            "major_name": _safe_str(target_family.get("major_name")),
            "group_name": _safe_str(target_family.get("group_name")),
            "row_total": int(target_family.get("row_total", len(applied_rows)) or len(applied_rows)),
        },
        "industries": merged_rows,
    }
    return registry


def render_markdown(registry: Dict[str, Any]) -> str:
    summary = dict(registry.get("summary") or {})
    target = dict(registry.get("last_target_family") or {})
    lines = [
        "# Permit Focus Family Registry",
        "",
        "## Summary",
        f"- family_registry_row_total: `{summary.get('family_registry_row_total', 0)}`",
        f"- newly_materialized_row_total: `{summary.get('newly_materialized_row_total', 0)}`",
        f"- family_registry_group_total: `{summary.get('family_registry_group_total', 0)}`",
        f"- applied_family_total: `{summary.get('applied_family_total', 0)}`",
        f"- target_family_row_total: `{summary.get('target_family_row_total', 0)}`",
        f"- rows_with_raw_source_proof_total: `{summary.get('rows_with_raw_source_proof_total', 0)}`",
        f"- focus_family_registry_with_raw_source_proof_total: `{summary.get('focus_family_registry_with_raw_source_proof_total', 0)}`",
        f"- focus_family_registry_missing_raw_source_proof_total: `{summary.get('focus_family_registry_missing_raw_source_proof_total', 0)}`",
        f"- pending_focus_seed_row_total_after_apply: `{summary.get('pending_focus_seed_row_total_after_apply', 0)}`",
        "",
        "## Last Target Family",
        f"- family_key: `{target.get('family_key', '')}`",
        f"- law_title: `{target.get('law_title', '')}`",
        f"- major_name: `{target.get('major_name', '')}`",
        f"- group_name: `{target.get('group_name', '')}`",
        f"- row_total: `{target.get('row_total', 0)}`",
        "",
        "## Last Applied Families",
    ]
    applied_families = [item for item in list(registry.get("last_applied_families") or []) if _safe_str(item)]
    if not applied_families:
        lines.append("- none")
    else:
        for item in applied_families:
            lines.append(f"- `{item}`")
    lines.extend([
        "",
        "## Materialized Families",
    ])
    families = [item for item in list(registry.get("materialized_families") or []) if _safe_str(item)]
    if not families:
        lines.append("- none")
    else:
        for item in families:
            lines.append(f"- `{item}`")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize the next focus family into a curated family registry.")
    parser.add_argument("--packet-input", default=str(DEFAULT_PACKET_INPUT))
    parser.add_argument("--focus-seed-input", default=str(DEFAULT_FOCUS_SEED_INPUT))
    parser.add_argument("--registry-output", default=str(DEFAULT_REGISTRY_OUTPUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    parser.add_argument("--family-batch-size", type=int, default=1)
    parser.add_argument("--materialize-all-pending", action="store_true")
    args = parser.parse_args()

    packet = _load_json(Path(args.packet_input).expanduser().resolve())
    focus_seed_catalog = _load_json(Path(args.focus_seed_input).expanduser().resolve())
    registry_output = Path(args.registry_output).expanduser().resolve()
    existing_registry = _load_json(registry_output)
    registry = build_registry(
        packet=packet,
        existing_registry=existing_registry,
        focus_seed_catalog=focus_seed_catalog,
        family_batch_size=args.family_batch_size,
        materialize_all_pending=bool(args.materialize_all_pending),
    )

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    registry_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    registry_output.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    json_output.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(registry), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "registry": str(registry_output),
                "json": str(json_output),
                "md": str(md_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
