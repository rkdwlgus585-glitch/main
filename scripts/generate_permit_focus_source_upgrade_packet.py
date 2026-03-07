from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FOCUS_SEED_INPUT = ROOT / "config" / "permit_focus_seed_catalog.json"
DEFAULT_FOCUS_FAMILY_REGISTRY_INPUT = ROOT / "config" / "permit_focus_family_registry.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_focus_source_upgrade_packet_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_focus_source_upgrade_packet_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit focus source upgrade packet input must be a JSON object")
    return payload


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _normalized_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [row for row in list(payload.get("industries") or []) if isinstance(row, dict)]


def _pending_seed_rows(
    focus_seed_catalog: Dict[str, Any],
    focus_family_registry: Dict[str, Any],
) -> List[Dict[str, Any]]:
    materialized_codes = {
        _safe_str(row.get("service_code"))
        for row in _normalized_rows(focus_family_registry)
        if _safe_str(row.get("service_code"))
    }
    return [
        dict(row)
        for row in _normalized_rows(focus_seed_catalog)
        if _safe_str(row.get("service_code")) not in materialized_codes
    ]


def _group_key(row: Dict[str, Any]) -> str:
    return (
        _safe_str(row.get("law_title"))
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


def _materialize_registry_rows(rows: List[Dict[str, Any]], family_key: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for row in rows:
        item = dict(row)
        item["catalog_source_kind"] = "focus_family_registry"
        item["catalog_source_label"] = "permit_focus_family_registry"
        item["source_upgrade_status"] = "materialized_from_focus_seed"
        item["source_upgrade_family"] = family_key
        item["source_upgrade_generated_at"] = generated_at
        out.append(item)
    return out


def build_packet(
    *,
    focus_seed_catalog: Dict[str, Any],
    focus_family_registry: Dict[str, Any],
) -> Dict[str, Any]:
    seed_rows = _normalized_rows(focus_seed_catalog)
    family_registry_rows = _normalized_rows(focus_family_registry)
    pending_rows = _pending_seed_rows(focus_seed_catalog, focus_family_registry)

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in pending_rows:
        grouped.setdefault(_group_key(row), []).append(row)

    group_rows = []
    for family_key, rows in grouped.items():
        sorted_rows = _sorted_rows(rows)
        first = sorted_rows[0]
        group_rows.append(
            {
                "family_key": family_key,
                "law_title": _safe_str(first.get("law_title")),
                "major_name": _safe_str(first.get("major_name")),
                "group_name": _safe_str(first.get("group_name")),
                "row_total": len(sorted_rows),
                "sample_service_codes": [_safe_str(row.get("service_code")) for row in sorted_rows[:8]],
                "sample_service_names": [_safe_str(row.get("service_name")) for row in sorted_rows[:8]],
            }
        )
    group_rows.sort(key=lambda row: (-int(row.get("row_total", 0) or 0), _safe_str(row.get("family_key"))))

    target_group = dict(group_rows[0]) if group_rows else {}
    target_family = _safe_str(target_group.get("family_key"))
    target_rows = _sorted_rows(grouped.get(target_family, [])) if target_family else []
    registry_rows = _materialize_registry_rows(target_rows, target_family)

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "focus_seed_row_total": len(seed_rows),
            "focus_family_registry_row_total": len(family_registry_rows),
            "pending_focus_seed_row_total": len(pending_rows),
            "materialized_family_total": len(
                {
                    _group_key(row)
                    for row in family_registry_rows
                    if _safe_str(row.get("service_code"))
                }
            ),
            "target_family_row_total": len(target_rows),
            "remaining_pending_after_apply_total": max(0, len(pending_rows) - len(target_rows)),
        },
        "target_family": {
            "family_key": target_family,
            "law_title": _safe_str(target_group.get("law_title")),
            "major_name": _safe_str(target_group.get("major_name")),
            "group_name": _safe_str(target_group.get("group_name")),
            "row_total": int(target_group.get("row_total", len(target_rows)) or len(target_rows)),
            "suggested_action": "Materialize this family into a curated official-source-backed family registry layer.",
            "sample_service_codes": list(target_group.get("sample_service_codes") or []),
            "sample_service_names": list(target_group.get("sample_service_names") or []),
        },
        "execution_packet": {
            "destination_registry_path": str(DEFAULT_FOCUS_FAMILY_REGISTRY_INPUT),
            "packet_policy": "materialize the top pending focus family into a curated official-source-backed family registry layer",
            "source_artifacts": {
                "focus_seed_catalog": str(DEFAULT_FOCUS_SEED_INPUT),
                "focus_family_registry": str(DEFAULT_FOCUS_FAMILY_REGISTRY_INPUT),
            },
            "steps": [
                "Validate law.go.kr basis URLs and legal basis titles for the target family.",
                "Copy the target family rows into the curated family registry layer.",
                "Tag the rows as focus_family_registry so runtime provenance can distinguish them from focus_seed rows.",
                "Rebuild the release bundle and confirm pending focus-seed totals decrease by the target family row count.",
            ],
            "sample_rows": [
                {
                    "service_code": _safe_str(row.get("service_code")),
                    "service_name": _safe_str(row.get("service_name")),
                    "law_title": _safe_str(row.get("law_title")),
                    "legal_basis_title": _safe_str(row.get("legal_basis_title")),
                    "seed_rule_service_code": _safe_str(row.get("seed_rule_service_code")),
                    "seed_rule_id": _safe_str(row.get("seed_rule_id")),
                }
                for row in target_rows[:12]
            ],
            "registry_rows": registry_rows,
        },
    }


def render_markdown(packet: Dict[str, Any]) -> str:
    summary = dict(packet.get("summary") or {})
    target_family = dict(packet.get("target_family") or {})
    execution_packet = dict(packet.get("execution_packet") or {})
    lines = [
        "# Permit Focus Source Upgrade Packet",
        "",
        "## Summary",
        f"- focus_seed_row_total: `{summary.get('focus_seed_row_total', 0)}`",
        f"- focus_family_registry_row_total: `{summary.get('focus_family_registry_row_total', 0)}`",
        f"- pending_focus_seed_row_total: `{summary.get('pending_focus_seed_row_total', 0)}`",
        f"- materialized_family_total: `{summary.get('materialized_family_total', 0)}`",
        f"- target_family_row_total: `{summary.get('target_family_row_total', 0)}`",
        f"- remaining_pending_after_apply_total: `{summary.get('remaining_pending_after_apply_total', 0)}`",
        "",
        "## Target Family",
        f"- family_key: `{target_family.get('family_key', '')}`",
        f"- law_title: `{target_family.get('law_title', '')}`",
        f"- major_name: `{target_family.get('major_name', '')}`",
        f"- group_name: `{target_family.get('group_name', '')}`",
        f"- row_total: `{target_family.get('row_total', 0)}`",
        f"- suggested_action: {target_family.get('suggested_action', '')}",
        "",
        "## Execution Packet",
        f"- destination_registry_path: `{execution_packet.get('destination_registry_path', '')}`",
        f"- packet_policy: {execution_packet.get('packet_policy', '')}",
        "",
        "## Steps",
    ]
    for item in list(execution_packet.get("steps") or []):
        lines.append(f"- {item}")
    lines.extend(["", "## Sample Rows"])
    sample_rows = list(execution_packet.get("sample_rows") or [])
    if not sample_rows:
        lines.append("- none")
    else:
        for row in sample_rows:
            lines.append(
                f"- `{row.get('service_code', '')}` {row.get('service_name', '')}"
                f" / rule `{row.get('seed_rule_service_code', '')}`"
                f" / basis `{row.get('law_title', '')} / {row.get('legal_basis_title', '')}`"
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the next focus source upgrade packet from pending focus-seed rows.")
    parser.add_argument("--focus-seed-input", default=str(DEFAULT_FOCUS_SEED_INPUT))
    parser.add_argument("--focus-family-registry-input", default=str(DEFAULT_FOCUS_FAMILY_REGISTRY_INPUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    packet = build_packet(
        focus_seed_catalog=_load_json(Path(args.focus_seed_input).expanduser().resolve()),
        focus_family_registry=_load_json(Path(args.focus_family_registry_input).expanduser().resolve()),
    )

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(packet), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
