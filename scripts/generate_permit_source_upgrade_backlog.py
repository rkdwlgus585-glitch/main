from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MASTER_INPUT = ROOT / "logs" / "permit_master_catalog_latest.json"
DEFAULT_AUDIT_INPUT = ROOT / "logs" / "permit_provenance_audit_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_source_upgrade_backlog_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_source_upgrade_backlog_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit source upgrade backlog input must be a JSON object")
    return payload


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "service_code": _safe_str(row.get("service_code")),
        "canonical_service_code": _safe_str(row.get("canonical_service_code")),
        "service_name": _safe_str(row.get("service_name")),
        "major_code": _safe_str(row.get("major_code")),
        "major_name": _safe_str(row.get("major_name")),
        "group_name": _safe_str(row.get("group_name")),
        "law_title": _safe_str(row.get("law_title")),
        "legal_basis_title": _safe_str(row.get("legal_basis_title")),
        "criteria_source_type": _safe_str(row.get("criteria_source_type")),
        "platform_row_origin": _safe_str(row.get("platform_row_origin")),
        "master_row_origin": _safe_str(row.get("master_row_origin")),
        "catalog_source_kind": _safe_str(row.get("catalog_source_kind")),
        "catalog_source_label": _safe_str(row.get("catalog_source_label")),
        "platform_has_focus_alias": bool(row.get("platform_has_focus_alias")),
        "platform_has_inferred_alias": bool(row.get("platform_has_inferred_alias")),
        "is_rules_only": bool(row.get("is_rules_only")),
    }


def _group_rows(rows: List[Dict[str, Any]], group_key_fn, suggested_action: str, limit: int = 15) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        key = group_key_fn(row)
        if not key:
            key = "unknown"
        grouped.setdefault(key, []).append(row)

    buckets: List[Dict[str, Any]] = []
    for key, group_rows in grouped.items():
        sorted_rows = sorted(
            group_rows,
            key=lambda row: (
                str(row.get("major_code", "")),
                str(row.get("service_name", "")),
                str(row.get("canonical_service_code", "")),
            ),
        )
        first = sorted_rows[0]
        buckets.append(
            {
                "group_key": key,
                "law_title": _safe_str(first.get("law_title")),
                "major_name": _safe_str(first.get("major_name")),
                "row_total": len(sorted_rows),
                "sample_service_codes": [
                    _safe_str(row.get("canonical_service_code") or row.get("service_code"))
                    for row in sorted_rows[:5]
                ],
                "sample_service_names": [_safe_str(row.get("service_name")) for row in sorted_rows[:5]],
                "suggested_action": suggested_action,
            }
        )

    buckets.sort(key=lambda row: (-int(row.get("row_total", 0) or 0), _safe_str(row.get("group_key"))))
    return buckets[:limit]


def build_backlog(master_catalog: Dict[str, Any], provenance_audit: Dict[str, Any]) -> Dict[str, Any]:
    master_summary = dict(master_catalog.get("summary") or {})
    audit_summary = dict(provenance_audit.get("summary") or {})
    rows = [
        _normalize_row(row)
        for row in list(master_catalog.get("industries") or [])
        if isinstance(row, dict)
    ]

    focus_seed_rows = [row for row in rows if row.get("catalog_source_kind") == "focus_seed_catalog"]
    absorbed_rows = [
        row
        for row in rows
        if row.get("platform_row_origin") == "focus_source_absorbed"
        or row.get("master_row_origin") == "focus_source_absorbed"
    ]
    candidate_pack_rows = [row for row in rows if row.get("criteria_source_type") == "candidate_pack"]
    inferred_rows = [row for row in rows if row.get("platform_has_inferred_alias")]

    focus_seed_groups = _group_rows(
        focus_seed_rows,
        lambda row: _safe_str(row.get("law_title")) or _safe_str(row.get("group_name")) or _safe_str(row.get("major_name")),
        "Replace this focus-seed family with an official raw/master registry source.",
        limit=20,
    )
    absorbed_groups = _group_rows(
        absorbed_rows,
        lambda row: _safe_str(row.get("law_title")) or _safe_str(row.get("major_name")),
        "Normalize this absorbed family into a raw/master registry source.",
        limit=20,
    )
    candidate_pack_groups = _group_rows(
        candidate_pack_rows,
        lambda row: _safe_str(row.get("law_title")) or _safe_str(row.get("major_name")),
        "Convert this candidate-pack family into structured rule/article mappings.",
        limit=20,
    )
    inferred_review_rows = sorted(
        inferred_rows,
        key=lambda row: (
            _safe_str(row.get("major_code")),
            _safe_str(row.get("service_name")),
        ),
    )[:15]

    next_actions: List[str] = []
    if focus_seed_rows:
        top_seed = focus_seed_groups[0]["group_key"] if focus_seed_groups else "top focus-seed family"
        next_actions.append(
            f"Start with focus-seed family `{top_seed}` and replace the {len(focus_seed_rows)} focus-seed rows with official raw/master source snapshots."
        )
    if absorbed_rows:
        top_promoted = absorbed_groups[0]["group_key"] if absorbed_groups else "top absorbed family"
        next_actions.append(
            f"Start with absorbed family `{top_promoted}` and materialize the {len(absorbed_rows)} absorbed rows into raw/master registry sources."
        )
    if candidate_pack_rows:
        top_candidate = candidate_pack_groups[0]["group_key"] if candidate_pack_groups else "top candidate-pack family"
        next_actions.append(
            f"Reduce candidate-pack dependence for {len(candidate_pack_rows)} rows, starting from `{top_candidate}`."
        )
    if inferred_rows:
        next_actions.append(
            f"Manually re-verify the {len(inferred_rows)} inferred-alias rows before exposing them as partner defaults."
        )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "master_industry_total": int(master_summary.get("master_industry_total", len(rows)) or len(rows)),
            "master_absorbed_row_total": int(
                master_summary.get("master_absorbed_row_total", audit_summary.get("master_absorbed_row_total", len(absorbed_rows)))
                or len(absorbed_rows)
            ),
            "focus_family_registry_row_total": int(
                audit_summary.get("focus_family_registry_row_total", 0) or 0
            ),
            "focus_seed_row_total": int(audit_summary.get("focus_seed_row_total", len(focus_seed_rows)) or len(focus_seed_rows)),
            "candidate_pack_total": int(audit_summary.get("candidate_pack_total", len(candidate_pack_rows)) or len(candidate_pack_rows)),
            "inferred_reverification_total": len(inferred_rows),
            "focus_seed_group_total": len(focus_seed_groups),
            "absorbed_group_total": len(absorbed_groups),
            "candidate_pack_group_total": len(candidate_pack_groups),
        },
        "next_actions": next_actions,
        "upgrade_tracks": {
            "focus_seed_source_groups": focus_seed_groups,
            "absorbed_source_groups": absorbed_groups,
            "candidate_pack_stabilization_groups": candidate_pack_groups,
            "inferred_reverification_rows": inferred_review_rows,
        },
    }


def render_markdown(backlog: Dict[str, Any]) -> str:
    summary = dict(backlog.get("summary") or {})
    lines = [
        "# Permit Source Upgrade Backlog",
        "",
        "## Summary",
        f"- master_industry_total: `{summary.get('master_industry_total', 0)}`",
        f"- master_absorbed_row_total: `{summary.get('master_absorbed_row_total', 0)}`",
        f"- focus_family_registry_row_total: `{summary.get('focus_family_registry_row_total', 0)}`",
        f"- focus_seed_row_total: `{summary.get('focus_seed_row_total', 0)}`",
        f"- candidate_pack_total: `{summary.get('candidate_pack_total', 0)}`",
        f"- inferred_reverification_total: `{summary.get('inferred_reverification_total', 0)}`",
        f"- focus_seed_group_total: `{summary.get('focus_seed_group_total', 0)}`",
        f"- absorbed_group_total: `{summary.get('absorbed_group_total', 0)}`",
        f"- candidate_pack_group_total: `{summary.get('candidate_pack_group_total', 0)}`",
        "",
        "## Next Actions",
    ]
    actions = list(backlog.get("next_actions") or [])
    if actions:
        lines.extend(f"- {item}" for item in actions)
    else:
        lines.append("- none")

    tracks = dict(backlog.get("upgrade_tracks") or {})
    for title, key in (
        ("Focus Seed Source Groups", "focus_seed_source_groups"),
        ("Absorbed Source Groups", "absorbed_source_groups"),
        ("Candidate-Pack Stabilization Groups", "candidate_pack_stabilization_groups"),
        ("Inferred Reverification Rows", "inferred_reverification_rows"),
    ):
        lines.extend(["", f"## {title}"])
        rows = list(tracks.get(key) or [])
        if not rows:
            lines.append("- none")
            continue
        for row in rows:
            if key == "inferred_reverification_rows":
                lines.append(
                    f"- `{row.get('service_code', '')}` {row.get('service_name', '')} / basis `{row.get('law_title', '')} / {row.get('legal_basis_title', '')}`"
                )
                continue
            lines.append(
                f"- `{row.get('group_key', '')}` rows={row.get('row_total', 0)}"
                + (f" / law `{row.get('law_title', '')}`" if row.get("law_title") else "")
                + (f" / sample {', '.join(row.get('sample_service_codes') or [])}" if row.get("sample_service_codes") else "")
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a prioritized source-upgrade backlog for permit data.")
    parser.add_argument("--master-input", default=str(DEFAULT_MASTER_INPUT))
    parser.add_argument("--audit-input", default=str(DEFAULT_AUDIT_INPUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    master_catalog = _load_json(Path(args.master_input).expanduser().resolve())
    provenance_audit = _load_json(Path(args.audit_input).expanduser().resolve())
    backlog = build_backlog(master_catalog, provenance_audit)

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(backlog, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(backlog), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
