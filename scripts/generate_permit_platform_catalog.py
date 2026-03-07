from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import permit_diagnosis_calculator  # noqa: E402


DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_platform_catalog_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_platform_catalog_latest.md"


def build_platform_artifact(bootstrap_payload: Dict[str, Any]) -> Dict[str, Any]:
    permit_catalog = bootstrap_payload.get("permitCatalog") or {}
    platform_catalog = permit_catalog.get("platform_catalog") or {}
    return {
        "summary": dict(platform_catalog.get("summary") or {}),
        "major_categories": list(platform_catalog.get("major_categories") or []),
        "industries": list(platform_catalog.get("industries") or []),
    }


def render_markdown(artifact: Dict[str, Any]) -> str:
    summary = dict(artifact.get("summary") or {})
    lines = [
        "# Permit Platform Catalog",
        "",
        "## Summary",
        f"- platform_category_total: `{summary.get('platform_category_total', 0)}`",
        f"- platform_industry_total: `{summary.get('platform_industry_total', 0)}`",
        f"- platform_real_row_total: `{summary.get('platform_real_row_total', 0)}`",
        f"- platform_focus_registry_row_total: `{summary.get('platform_focus_registry_row_total', 0)}`",
        f"- platform_promoted_selector_total: `{summary.get('platform_promoted_selector_total', 0)}`",
        f"- platform_absorbed_focus_total: `{summary.get('platform_absorbed_focus_total', 0)}`",
        f"- platform_real_with_selector_alias_total: `{summary.get('platform_real_with_selector_alias_total', 0)}`",
        f"- platform_focus_registry_with_alias_total: `{summary.get('platform_focus_registry_with_alias_total', 0)}`",
        f"- platform_focus_alias_total: `{summary.get('platform_focus_alias_total', 0)}`",
        f"- platform_inferred_alias_total: `{summary.get('platform_inferred_alias_total', 0)}`",
        f"- platform_selector_alias_total: `{summary.get('platform_selector_alias_total', 0)}`",
        "",
        "## Rows",
    ]
    rows = list(artifact.get("industries") or [])
    if not rows:
        lines.append("- none")
    else:
        for row in rows[:40]:
            alias_codes = ", ".join(
                str(alias.get("selector_code", "") or "").strip()
                for alias in list(row.get("platform_selector_aliases") or [])
                if str(alias.get("selector_code", "") or "").strip()
            )
            law_bits = " / ".join(
                bit
                for bit in [str(row.get("law_title", "") or "").strip(), str(row.get("legal_basis_title", "") or "").strip()]
                if bit
            )
            lines.append(
                f"- `{row.get('service_code', '')}` ({row.get('platform_row_origin', '')}) {row.get('service_name', '')}"
                + (f" / canonical `{row.get('canonical_service_code', '')}`" if row.get("canonical_service_code") else "")
                + (f" / aliases {alias_codes}" if alias_codes else "")
                + (f" / 법령 {law_bits}" if law_bits else "")
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a platform-ready permit catalog artifact.")
    parser.add_argument("--catalog", default=str(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH))
    parser.add_argument("--rules", default=str(permit_diagnosis_calculator.DEFAULT_RULES_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    catalog = permit_diagnosis_calculator._load_catalog(Path(args.catalog).expanduser().resolve())
    rules = permit_diagnosis_calculator._load_rule_catalog(Path(args.rules).expanduser().resolve())
    bootstrap_payload = permit_diagnosis_calculator.build_bootstrap_payload(catalog, rules)
    artifact = build_platform_artifact(bootstrap_payload)

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(artifact), encoding="utf-8")

    print(f"[saved-json] {json_output}")
    print(f"[saved-md] {md_output}")
    print(f"[platform_industry_total] {artifact['summary'].get('platform_industry_total', 0)}")
    print(f"[platform_focus_registry_row_total] {artifact['summary'].get('platform_focus_registry_row_total', 0)}")
    print(f"[platform_absorbed_focus_total] {artifact['summary'].get('platform_absorbed_focus_total', 0)}")
    print(f"[platform_real_with_selector_alias_total] {artifact['summary'].get('platform_real_with_selector_alias_total', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
