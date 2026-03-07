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


DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_master_catalog_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_master_catalog_latest.md"


def build_master_artifact(bootstrap_payload: Dict[str, Any]) -> Dict[str, Any]:
    permit_catalog = bootstrap_payload.get("permitCatalog") or {}
    master_catalog = permit_catalog.get("master_catalog") or {}
    return {
        "summary": dict(master_catalog.get("summary") or {}),
        "feed_contract": dict(master_catalog.get("feed_contract") or {}),
        "major_categories": list(master_catalog.get("major_categories") or []),
        "industries": list(master_catalog.get("industries") or []),
    }


def render_markdown(artifact: Dict[str, Any]) -> str:
    summary = dict(artifact.get("summary") or {})
    feed_contract = dict(artifact.get("feed_contract") or {})
    lines = [
        "# Permit Master Catalog",
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
        f"- master_selector_alias_total: `{summary.get('master_selector_alias_total', 0)}`",
        f"- master_canonicalized_promoted_total: `{summary.get('master_canonicalized_promoted_total', 0)}`",
        "",
        "## Feed Contract",
        f"- primary_feed_name: `{feed_contract.get('primary_feed_name', '')}`",
        f"- overlay_feed_name: `{feed_contract.get('overlay_feed_name', '')}`",
        f"- primary_row_key: `{feed_contract.get('primary_row_key', '')}`",
        f"- canonical_row_key: `{feed_contract.get('canonical_row_key', '')}`",
        f"- focus_registry_row_key_policy: `{feed_contract.get('focus_registry_row_key_policy', '')}`",
        f"- absorbed_row_key_policy: `{feed_contract.get('absorbed_row_key_policy', '')}`",
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
                for bit in [
                    str(row.get("law_title", "") or "").strip(),
                    str(row.get("legal_basis_title", "") or "").strip(),
                ]
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
    parser = argparse.ArgumentParser(description="Generate a durable permit master catalog artifact.")
    parser.add_argument("--catalog", default=str(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH))
    parser.add_argument("--rules", default=str(permit_diagnosis_calculator.DEFAULT_RULES_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    catalog = permit_diagnosis_calculator._load_catalog(Path(args.catalog).expanduser().resolve())
    rules = permit_diagnosis_calculator._load_rule_catalog(Path(args.rules).expanduser().resolve())
    bootstrap_payload = permit_diagnosis_calculator.build_bootstrap_payload(catalog, rules)
    artifact = build_master_artifact(bootstrap_payload)

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(artifact), encoding="utf-8")

    print(f"[saved-json] {json_output}")
    print(f"[saved-md] {md_output}")
    print(f"[master_industry_total] {artifact['summary'].get('master_industry_total', 0)}")
    print(f"[master_focus_registry_row_total] {artifact['summary'].get('master_focus_registry_row_total', 0)}")
    print(f"[master_absorbed_row_total] {artifact['summary'].get('master_absorbed_row_total', 0)}")
    print(f"[master_real_with_alias_total] {artifact['summary'].get('master_real_with_alias_total', 0)}")
    print(f"[master_canonicalized_promoted_total] {artifact['summary'].get('master_canonicalized_promoted_total', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
