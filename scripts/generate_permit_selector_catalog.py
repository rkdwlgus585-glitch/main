from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import permit_diagnosis_calculator  # noqa: E402


DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_selector_catalog_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_selector_catalog_latest.md"


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "service_code": str(row.get("service_code", "") or "").strip(),
        "canonical_service_code": str(row.get("canonical_service_code", "") or "").strip(),
        "service_name": str(row.get("service_name", "") or "").strip(),
        "selector_kind": str(row.get("selector_kind", "") or "").strip(),
        "major_code": str(row.get("major_code", "") or "").strip(),
        "major_name": str(row.get("major_name", "") or "").strip(),
        "selector_category_code": str(row.get("selector_category_code", "") or "").strip(),
        "selector_category_name": str(row.get("selector_category_name", "") or "").strip(),
        "is_rules_only": bool(row.get("is_rules_only", False)),
        "law_title": str(row.get("law_title", "") or "").strip(),
        "legal_basis_title": str(row.get("legal_basis_title", "") or "").strip(),
        "quality_flags": list(row.get("quality_flags") or []),
    }


def build_selector_artifact(bootstrap_payload: Dict[str, Any]) -> Dict[str, Any]:
    permit_catalog = bootstrap_payload.get("permitCatalog") or {}
    permit_summary = permit_catalog.get("summary") or {}
    selector_catalog = permit_catalog.get("selector_catalog") or {}
    selector_summary = selector_catalog.get("summary") or {}
    rows = [
        _normalize_row(row)
        for row in list(selector_catalog.get("industries") or [])
        if isinstance(row, dict)
    ]
    focus_rows = [row for row in rows if str(row.get("selector_kind", "") or "") == "focus"]
    inferred_rows = [row for row in rows if str(row.get("selector_kind", "") or "") == "inferred"]
    return {
        "summary": {
            "selector_category_total": int(selector_summary.get("selector_category_total", 0) or 0),
            "selector_entry_total": int(selector_summary.get("selector_entry_total", 0) or 0),
            "selector_focus_total": int(selector_summary.get("selector_focus_total", 0) or 0),
            "selector_inferred_total": int(selector_summary.get("selector_inferred_total", 0) or 0),
            "selector_real_entry_total": int(selector_summary.get("selector_real_entry_total", 0) or 0),
            "selector_rules_only_entry_total": int(selector_summary.get("selector_rules_only_entry_total", 0) or 0),
            "real_focus_target_total": int(permit_summary.get("real_focus_target_total", 0) or 0),
            "rules_only_focus_target_total": int(permit_summary.get("rules_only_focus_target_total", 0) or 0),
            "real_focus_target_with_other_total": int(permit_summary.get("real_focus_target_with_other_total", 0) or 0),
            "rules_only_focus_target_with_other_total": int(
                permit_summary.get("rules_only_focus_target_with_other_total", 0) or 0
            ),
            "real_high_confidence_focus_total": int(permit_summary.get("real_focus_target_total", 0) or 0),
            "rules_only_high_confidence_focus_total": int(permit_summary.get("rules_only_focus_target_total", 0) or 0),
            "focus_selector_entry_total": int(permit_summary.get("focus_selector_entry_total", 0) or 0),
            "inferred_selector_entry_total": int(permit_summary.get("inferred_selector_entry_total", 0) or 0),
        },
        "major_categories": list(selector_catalog.get("major_categories") or []),
        "focus_selector_rows": focus_rows,
        "inferred_selector_rows": inferred_rows,
    }


def render_markdown(artifact: Dict[str, Any]) -> str:
    summary = dict(artifact.get("summary") or {})
    lines = [
        "# Permit Selector Catalog",
        "",
        "## Summary",
        f"- selector_category_total: `{summary.get('selector_category_total', 0)}`",
        f"- selector_entry_total: `{summary.get('selector_entry_total', 0)}`",
        f"- selector_focus_total: `{summary.get('selector_focus_total', 0)}`",
        f"- selector_inferred_total: `{summary.get('selector_inferred_total', 0)}`",
        f"- selector_real_entry_total: `{summary.get('selector_real_entry_total', 0)}`",
        f"- selector_rules_only_entry_total: `{summary.get('selector_rules_only_entry_total', 0)}`",
        f"- real_focus_target_total: `{summary.get('real_focus_target_total', 0)}`",
        f"- rules_only_focus_target_total: `{summary.get('rules_only_focus_target_total', 0)}`",
        f"- real_focus_target_with_other_total: `{summary.get('real_focus_target_with_other_total', 0)}`",
        f"- rules_only_focus_target_with_other_total: `{summary.get('rules_only_focus_target_with_other_total', 0)}`",
        "",
        "## Focus Selector Rows",
    ]
    focus_rows = list(artifact.get("focus_selector_rows") or [])
    if focus_rows:
        for row in focus_rows[:30]:
            law_bits = " / ".join(
                bit
                for bit in [
                    str(row.get("law_title", "") or "").strip(),
                    str(row.get("legal_basis_title", "") or "").strip(),
                ]
                if bit
            )
            lines.append(
                f"- `{row.get('service_code', '')}` -> `{row.get('canonical_service_code', '')}` {row.get('service_name', '')}"
                + (f" / 법령 {law_bits}" if law_bits else "")
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Inferred Selector Rows"])
    inferred_rows = list(artifact.get("inferred_selector_rows") or [])
    if inferred_rows:
        for row in inferred_rows[:20]:
            lines.append(
                f"- `{row.get('service_code', '')}` -> `{row.get('canonical_service_code', '')}` {row.get('service_name', '')}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a selector catalog for permit widget/API integration.")
    parser.add_argument("--catalog", default=str(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH))
    parser.add_argument("--rules", default=str(permit_diagnosis_calculator.DEFAULT_RULES_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    catalog = permit_diagnosis_calculator._load_catalog(Path(args.catalog).expanduser().resolve())
    rules = permit_diagnosis_calculator._load_rule_catalog(Path(args.rules).expanduser().resolve())
    bootstrap_payload = permit_diagnosis_calculator.build_bootstrap_payload(catalog, rules)
    artifact = build_selector_artifact(bootstrap_payload)

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(artifact), encoding="utf-8")

    print(f"[saved-json] {json_output}")
    print(f"[saved-md] {md_output}")
    print(f"[selector_entry_total] {artifact['summary']['selector_entry_total']}")
    print(f"[selector_focus_total] {artifact['summary']['selector_focus_total']}")
    print(f"[selector_inferred_total] {artifact['summary']['selector_inferred_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
