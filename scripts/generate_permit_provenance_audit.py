from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "logs" / "permit_master_catalog_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_provenance_audit_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_provenance_audit_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit provenance audit input must be a JSON object")
    return payload


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    raw_source_proof = row.get("raw_source_proof") or {}
    if not isinstance(raw_source_proof, dict):
        raw_source_proof = {}
    aliases = [
        {
            "selector_code": _safe_str(alias.get("selector_code")),
            "selector_kind": _safe_str(alias.get("selector_kind")),
        }
        for alias in list(row.get("platform_selector_aliases") or [])
        if isinstance(alias, dict) and _safe_str(alias.get("selector_code"))
    ]
    return {
        "service_code": _safe_str(row.get("service_code")),
        "canonical_service_code": _safe_str(row.get("canonical_service_code")),
        "service_name": _safe_str(row.get("service_name")),
        "major_code": _safe_str(row.get("major_code")),
        "major_name": _safe_str(row.get("major_name")),
        "platform_row_origin": _safe_str(row.get("platform_row_origin")),
        "master_row_origin": _safe_str(row.get("master_row_origin")),
        "catalog_source_kind": _safe_str(row.get("catalog_source_kind")),
        "catalog_source_label": _safe_str(row.get("catalog_source_label")),
        "criteria_source_type": _safe_str(row.get("criteria_source_type")),
        "law_title": _safe_str(row.get("law_title")),
        "legal_basis_title": _safe_str(row.get("legal_basis_title")),
        "is_rules_only": bool(row.get("is_rules_only")),
        "platform_has_focus_alias": bool(row.get("platform_has_focus_alias")),
        "platform_has_inferred_alias": bool(row.get("platform_has_inferred_alias")),
        "quality_flags": [
            _safe_str(flag) for flag in list(row.get("quality_flags") or []) if _safe_str(flag)
        ],
        "platform_selector_aliases": aliases,
        "raw_source_proof_status": _safe_str(raw_source_proof.get("proof_status")),
        "raw_source_checksum": _safe_str(raw_source_proof.get("source_checksum")),
        "raw_source_url_total": len(
            [_safe_str(url) for url in list(raw_source_proof.get("source_urls") or []) if _safe_str(url)]
        ),
    }


def _top_rows(rows: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
    return rows[:limit]


def build_audit(payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(payload.get("summary") or {})
    rows = [
        _normalize_row(row)
        for row in list(payload.get("industries") or [])
        if isinstance(row, dict)
    ]

    focus_registry_rows = [row for row in rows if row.get("platform_row_origin") == "focus_registry_source"]
    absorbed_rows = [row for row in rows if row.get("platform_row_origin") == "focus_source_absorbed"]
    promoted_rows = [row for row in rows if row.get("platform_row_origin") == "selector_promoted"]
    real_rows = [row for row in rows if row.get("platform_row_origin") == "real_catalog"]
    focus_family_registry_rows = [row for row in rows if row.get("catalog_source_kind") == "focus_family_registry"]
    focus_seed_rows = [row for row in rows if row.get("catalog_source_kind") == "focus_seed_catalog"]
    inferred_alias_rows = [row for row in rows if row.get("platform_has_inferred_alias")]
    focus_alias_rows = [row for row in rows if row.get("platform_has_focus_alias")]
    quality_flag_rows = [row for row in rows if list(row.get("quality_flags") or [])]
    missing_basis_rows = [
        row for row in rows if not row.get("law_title") or not row.get("legal_basis_title")
    ]
    raw_source_proof_rows = [row for row in rows if row.get("raw_source_checksum")]
    focus_family_registry_missing_raw_source_proof_rows = [
        row
        for row in focus_family_registry_rows
        if not row.get("raw_source_checksum")
    ]
    candidate_pack_rows = [row for row in rows if row.get("criteria_source_type") == "candidate_pack"]
    article_body_rows = [row for row in rows if row.get("criteria_source_type") == "article_body"]
    rule_pack_rows = [row for row in rows if row.get("criteria_source_type") == "rule_pack"]

    criteria_source_breakdown: Dict[str, int] = {}
    for row in rows:
        key = row.get("criteria_source_type") or "unknown"
        criteria_source_breakdown[key] = int(criteria_source_breakdown.get(key, 0) or 0) + 1

    quality_flag_breakdown: Dict[str, int] = {}
    for row in rows:
        for flag in list(row.get("quality_flags") or []):
            quality_flag_breakdown[flag] = int(quality_flag_breakdown.get(flag, 0) or 0) + 1

    next_actions: List[str] = []
    if focus_seed_rows:
        next_actions.append(
            f"Upgrade {len(focus_seed_rows)} focus-seed rows into durable raw registry sources so the product is not relying on focus-seed overlays as the long-term source of truth."
        )
    if focus_family_registry_missing_raw_source_proof_rows:
        next_actions.append(
            f"Add raw-source proof to {len(focus_family_registry_missing_raw_source_proof_rows)} curated family-registry rows before treating them as patent-grade source evidence."
        )
    if absorbed_rows:
        next_actions.append(
            f"Normalize {len(absorbed_rows)} absorbed focus rows into raw registry snapshots so runtime absorption is no longer the only source of truth."
        )
    if promoted_rows:
        next_actions.append(
            f"Legacy promoted residue still exists on {len(promoted_rows)} rows and should be removed from the runtime contract."
        )
    if inferred_alias_rows:
        next_actions.append(
            f"Re-verify {len(inferred_alias_rows)} inferred alias rows before using them as commercial widget defaults."
        )
    if candidate_pack_rows:
        next_actions.append(
            f"Reduce candidate-pack dependence for {len(candidate_pack_rows)} rows by pushing them toward structured rule packs or stable article mappings."
        )
    if missing_basis_rows:
        next_actions.append(
            f"Repair missing legal basis fields for {len(missing_basis_rows)} rows before externalizing them through partner/API contracts."
        )
    if quality_flag_rows:
        next_actions.append(
            f"Resolve {len(quality_flag_rows)} rows carrying quality flags before marking the master feed as fully trusted."
        )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "master_industry_total": int(summary.get("master_industry_total", len(rows)) or len(rows)),
            "master_real_row_total": int(summary.get("master_real_row_total", len(real_rows)) or len(real_rows)),
            "master_focus_registry_row_total": int(
                summary.get("master_focus_registry_row_total", len(focus_registry_rows)) or len(focus_registry_rows)
            ),
            "master_promoted_row_total": int(summary.get("master_promoted_row_total", len(promoted_rows)) or len(promoted_rows)),
            "master_absorbed_row_total": int(summary.get("master_absorbed_row_total", len(absorbed_rows)) or len(absorbed_rows)),
            "master_real_with_alias_total": int(summary.get("master_real_with_alias_total", 0) or 0),
            "master_focus_row_total": int(summary.get("master_focus_row_total", len(focus_alias_rows)) or len(focus_alias_rows)),
            "master_inferred_overlay_total": int(summary.get("master_inferred_overlay_total", len(inferred_alias_rows)) or len(inferred_alias_rows)),
            "master_canonicalized_promoted_total": int(summary.get("master_canonicalized_promoted_total", len(promoted_rows)) or len(promoted_rows)),
            "focus_registry_row_total": len(focus_registry_rows),
            "focus_registry_rules_only_total": len([row for row in focus_registry_rows if row.get("is_rules_only")]),
            "focus_family_registry_row_total": len(focus_family_registry_rows),
            "focus_seed_row_total": len(focus_seed_rows),
            "focus_seed_real_row_total": len(
                [
                    row
                    for row in focus_seed_rows
                    if row.get("platform_row_origin") == "real_catalog"
                    or row.get("master_row_origin") == "real_catalog"
                ]
            ),
            "absorbed_focus_row_total": len([row for row in absorbed_rows if row.get("platform_has_focus_alias")]),
            "absorbed_rules_only_total": len([row for row in absorbed_rows if row.get("is_rules_only")]),
            "rows_with_raw_source_proof_total": len(raw_source_proof_rows),
            "focus_family_registry_with_raw_source_proof_total": len(
                [row for row in focus_family_registry_rows if row.get("raw_source_checksum")]
            ),
            "focus_family_registry_missing_raw_source_proof_total": len(
                focus_family_registry_missing_raw_source_proof_rows
            ),
            "rows_with_quality_flags_total": len(quality_flag_rows),
            "rows_missing_legal_basis_total": len(missing_basis_rows),
            "candidate_pack_total": len(candidate_pack_rows),
            "article_body_total": len(article_body_rows),
            "rule_pack_total": len(rule_pack_rows),
        },
        "criteria_source_breakdown": criteria_source_breakdown,
        "quality_flag_breakdown": quality_flag_breakdown,
        "next_actions": next_actions,
        "review_queues": {
            "focus_seed_rows": _top_rows(focus_seed_rows, 25),
            "focus_registry_rows": _top_rows(focus_registry_rows, 25),
            "absorbed_rows": _top_rows(absorbed_rows, 25),
            "inferred_alias_rows": _top_rows(inferred_alias_rows, 10),
            "rows_missing_raw_source_proof": _top_rows(focus_family_registry_missing_raw_source_proof_rows, 25),
            "quality_flag_rows": _top_rows(quality_flag_rows, 25),
            "missing_legal_basis_rows": _top_rows(missing_basis_rows, 25),
        },
    }


def render_markdown(audit: Dict[str, Any]) -> str:
    summary = dict(audit.get("summary") or {})
    criteria_source_breakdown = dict(audit.get("criteria_source_breakdown") or {})
    lines = [
        "# Permit Provenance Audit",
        "",
        "## Summary",
        f"- master_industry_total: `{summary.get('master_industry_total', 0)}`",
        f"- master_real_row_total: `{summary.get('master_real_row_total', 0)}`",
        f"- master_focus_registry_row_total: `{summary.get('master_focus_registry_row_total', 0)}`",
        f"- master_promoted_row_total: `{summary.get('master_promoted_row_total', 0)}`",
        f"- master_absorbed_row_total: `{summary.get('master_absorbed_row_total', 0)}`",
        f"- master_real_with_alias_total: `{summary.get('master_real_with_alias_total', 0)}`",
        f"- master_focus_row_total: `{summary.get('master_focus_row_total', 0)}`",
        f"- master_inferred_overlay_total: `{summary.get('master_inferred_overlay_total', 0)}`",
        f"- master_canonicalized_promoted_total: `{summary.get('master_canonicalized_promoted_total', 0)}`",
        f"- focus_registry_row_total: `{summary.get('focus_registry_row_total', 0)}`",
        f"- focus_registry_rules_only_total: `{summary.get('focus_registry_rules_only_total', 0)}`",
        f"- focus_family_registry_row_total: `{summary.get('focus_family_registry_row_total', 0)}`",
        f"- focus_seed_row_total: `{summary.get('focus_seed_row_total', 0)}`",
        f"- focus_seed_real_row_total: `{summary.get('focus_seed_real_row_total', 0)}`",
        f"- absorbed_focus_row_total: `{summary.get('absorbed_focus_row_total', 0)}`",
        f"- absorbed_rules_only_total: `{summary.get('absorbed_rules_only_total', 0)}`",
        f"- rows_with_raw_source_proof_total: `{summary.get('rows_with_raw_source_proof_total', 0)}`",
        f"- focus_family_registry_with_raw_source_proof_total: `{summary.get('focus_family_registry_with_raw_source_proof_total', 0)}`",
        f"- focus_family_registry_missing_raw_source_proof_total: `{summary.get('focus_family_registry_missing_raw_source_proof_total', 0)}`",
        f"- rows_with_quality_flags_total: `{summary.get('rows_with_quality_flags_total', 0)}`",
        f"- rows_missing_legal_basis_total: `{summary.get('rows_missing_legal_basis_total', 0)}`",
        f"- candidate_pack_total: `{summary.get('candidate_pack_total', 0)}`",
        f"- article_body_total: `{summary.get('article_body_total', 0)}`",
        f"- rule_pack_total: `{summary.get('rule_pack_total', 0)}`",
        "",
        "## Criteria Sources",
    ]
    if criteria_source_breakdown:
        for key in sorted(criteria_source_breakdown):
            lines.append(f"- {key}: `{criteria_source_breakdown[key]}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Next Actions"])
    actions = list(audit.get("next_actions") or [])
    if actions:
        lines.extend(f"- {item}" for item in actions)
    else:
        lines.append("- none")

    queues = dict(audit.get("review_queues") or {})
    for title, key in (
        ("Focus Seed Rows", "focus_seed_rows"),
        ("Focus Registry Rows", "focus_registry_rows"),
        ("Absorbed Rows", "absorbed_rows"),
        ("Inferred Alias Rows", "inferred_alias_rows"),
        ("Rows Missing Raw Source Proof", "rows_missing_raw_source_proof"),
        ("Quality Flag Rows", "quality_flag_rows"),
        ("Missing Legal Basis Rows", "missing_legal_basis_rows"),
    ):
        lines.extend(["", f"## {title}"])
        rows = list(queues.get(key) or [])
        if not rows:
            lines.append("- none")
            continue
        for row in rows:
            lines.append(
                f"- `{row.get('service_code', '')}` {row.get('service_name', '')}"
                f" / origin `{row.get('platform_row_origin', '')}`"
                + (f" / canonical `{row.get('canonical_service_code', '')}`" if row.get("canonical_service_code") else "")
                + (f" / catalog_source `{row.get('catalog_source_kind', '')}`" if row.get("catalog_source_kind") else "")
                + (f" / source `{row.get('criteria_source_type', '')}`" if row.get("criteria_source_type") else "")
                + (
                    f" / raw_source_proof `{row.get('raw_source_proof_status', '')}`:{row.get('raw_source_url_total', 0)}"
                    if row.get("raw_source_proof_status") or row.get("raw_source_url_total")
                    else ""
                )
                + (f" / basis `{row.get('law_title', '')} / {row.get('legal_basis_title', '')}`" if row.get("law_title") or row.get("legal_basis_title") else "")
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit permit master catalog provenance and hidden release risk.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    payload = _load_json(Path(args.input).expanduser().resolve())
    audit = build_audit(payload)

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(audit), encoding="utf-8")

    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
