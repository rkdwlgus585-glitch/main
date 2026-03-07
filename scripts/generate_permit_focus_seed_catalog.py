from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import permit_diagnosis_calculator  # noqa: E402


DEFAULT_BASE_CATALOG = permit_diagnosis_calculator.DEFAULT_CATALOG_PATH
DEFAULT_RULES_PATH = permit_diagnosis_calculator.DEFAULT_RULES_PATH
DEFAULT_JSON_OUTPUT = permit_diagnosis_calculator.DEFAULT_FOCUS_SEED_CATALOG_PATH
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_focus_seed_catalog_latest.md"

FOCUS_FAMILY_MAPPINGS: Tuple[Dict[str, str], ...] = (
    {
        "law_keyword": "건설산업기본법",
        "major_code": "31",
        "major_name": "건설",
        "group_code": "31-01",
        "group_name": "건설업 등록기준",
        "group_description": "건설산업기본법상 자본금·기술인력 등록기준 핵심 업종군",
    },
    {
        "law_keyword": "전기공사업법",
        "major_code": "32",
        "major_name": "전기·정보통신",
        "group_code": "32-01",
        "group_name": "전기공사업 등록기준",
        "group_description": "전기공사업법상 등록기준 핵심 업종군",
    },
    {
        "law_keyword": "정보통신공사업법",
        "major_code": "32",
        "major_name": "전기·정보통신",
        "group_code": "32-02",
        "group_name": "정보통신공사업 등록기준",
        "group_description": "정보통신공사업법상 등록기준 핵심 업종군",
    },
    {
        "law_keyword": "소방시설공사업법",
        "major_code": "33",
        "major_name": "소방",
        "group_code": "33-01",
        "group_name": "소방시설공사업 등록기준",
        "group_description": "소방시설공사업법상 등록기준 핵심 업종군",
    },
    {
        "law_keyword": "경비업법",
        "major_code": "34",
        "major_name": "경비",
        "group_code": "34-01",
        "group_name": "경비업 허가기준",
        "group_description": "경비업법상 허가기준 핵심 업종군",
    },
    {
        "law_keyword": "액화석유가스의 안전관리 및 사업법",
        "major_code": "35",
        "major_name": "가스",
        "group_code": "35-01",
        "group_name": "가스시설시공업 등록기준",
        "group_description": "액화석유가스법상 등록기준 핵심 업종군",
    },
)


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _normalize_service_code(rule_service_code: str) -> str:
    raw = _safe_str(rule_service_code)
    if raw.startswith("RULE::"):
        raw = raw.split("RULE::", 1)[1]
    return f"FOCUS::{raw}"


def _classify_family(law_title: str) -> Dict[str, str]:
    normalized = _safe_str(law_title)
    for item in FOCUS_FAMILY_MAPPINGS:
        if item["law_keyword"] in normalized:
            return dict(item)
    return {
        "major_code": "39",
        "major_name": "핵심 인허가",
        "group_code": "39-01",
        "group_name": "핵심 등록기준",
        "group_description": "자본금·기술인력 등록기준 핵심 업종군",
    }


def _primary_legal_basis(rule: Dict[str, Any]) -> Dict[str, str]:
    for basis in list(rule.get("legal_basis") or []):
        if not isinstance(basis, dict):
            continue
        law_title = _safe_str(basis.get("law_title"))
        article = _safe_str(basis.get("article"))
        url = _safe_str(basis.get("url"))
        if law_title or article or url:
            return {
                "law_title": law_title,
                "article": article,
                "url": url,
            }
    return {"law_title": "", "article": "", "url": ""}


def _major_categories(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Dict[Tuple[str, str], int] = {}
    for row in rows:
        key = (_safe_str(row.get("major_code")), _safe_str(row.get("major_name")))
        if not key[0] or not key[1]:
            continue
        counts[key] = int(counts.get(key, 0) or 0) + 1
    output = [
        {"major_code": major_code, "major_name": major_name, "industry_count": total}
        for (major_code, major_name), total in counts.items()
    ]
    output.sort(key=lambda row: (_safe_str(row.get("major_code")), _safe_str(row.get("major_name"))))
    return output


def build_focus_seed_catalog(base_catalog: Dict[str, Any], rule_catalog: Dict[str, Any]) -> Dict[str, Any]:
    bootstrap = permit_diagnosis_calculator.build_bootstrap_payload(base_catalog, rule_catalog)
    permit_catalog = dict(bootstrap.get("permitCatalog") or {})
    focus_rows = [
        dict(row)
        for row in list(permit_catalog.get("focus_entries") or [])
        if isinstance(row, dict) and bool(row.get("is_rules_only"))
    ]
    rule_lookup = dict(bootstrap.get("ruleLookup") or {})

    seed_rows: List[Dict[str, Any]] = []
    for row in focus_rows:
        rule_service_code = _safe_str(row.get("service_code"))
        rule = dict(rule_lookup.get(rule_service_code) or {})
        legal_basis = _primary_legal_basis(rule)
        family = _classify_family(legal_basis.get("law_title", "") or row.get("law_title", ""))
        profile = row.get("registration_requirement_profile") or {}
        seed_rows.append(
            {
                "service_code": _normalize_service_code(rule_service_code),
                "service_name": _safe_str(row.get("service_name")),
                "major_code": family["major_code"],
                "major_name": family["major_name"],
                "group_code": family["group_code"],
                "group_name": family["group_name"],
                "group_description": family["group_description"],
                "group_declared_total": 0,
                "detail_url": legal_basis.get("url", ""),
                "catalog_source_kind": "focus_seed_catalog",
                "catalog_source_label": "permit_focus_seed_catalog",
                "seed_rule_service_code": rule_service_code,
                "seed_rule_id": _safe_str(rule.get("group_rule_id") or rule.get("rule_id")),
                "seed_law_family": family["group_name"],
                "has_rule": True,
                "is_rules_only": False,
                "law_title": _safe_str(row.get("law_title") or legal_basis.get("law_title")),
                "legal_basis_title": _safe_str(row.get("legal_basis_title") or legal_basis.get("article")),
                "legal_basis": [legal_basis] if any(legal_basis.values()) else [],
                "criteria_source_type": _safe_str(row.get("criteria_source_type") or "rule_pack"),
                "quality_flags": list(row.get("quality_flags") or []),
                "registration_requirement_profile": dict(profile) if isinstance(profile, dict) else {},
            }
        )

    seed_rows.sort(key=lambda row: (_safe_str(row.get("major_code")), _safe_str(row.get("service_name"))))
    categories = _major_categories(seed_rows)
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": {
            "base_catalog": str(DEFAULT_BASE_CATALOG),
            "rules_catalog": str(DEFAULT_RULES_PATH),
            "scope_policy": "capital_and_technical_only",
            "selection_origin": "permitCatalog.focus_entries (rule-only rows)",
        },
        "summary": {
            "seed_industry_total": len(seed_rows),
            "seed_major_category_total": len(categories),
            "seed_focus_rules_only_total": len(focus_rows),
        },
        "major_categories": categories,
        "industries": seed_rows,
    }


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    lines = [
        "# Permit Focus Seed Catalog",
        "",
        "## Summary",
        f"- seed_industry_total: `{summary.get('seed_industry_total', 0)}`",
        f"- seed_major_category_total: `{summary.get('seed_major_category_total', 0)}`",
        f"- seed_focus_rules_only_total: `{summary.get('seed_focus_rules_only_total', 0)}`",
        "",
        "## Rows",
    ]
    rows = list(payload.get("industries") or [])
    if not rows:
        lines.append("- none")
    else:
        for row in rows[:60]:
            profile = dict(row.get("registration_requirement_profile") or {})
            lines.append(
                f"- `{row.get('service_code', '')}` {row.get('service_name', '')}"
                f" / family `{row.get('group_name', '')}`"
                f" / rule `{row.get('seed_rule_service_code', '')}`"
                f" / capital `{profile.get('capital_eok', 0)}`억"
                f" / technicians `{profile.get('technicians_required', 0)}`"
                f" / basis `{row.get('law_title', '')} / {row.get('legal_basis_title', '')}`"
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a raw focus seed catalog from rule-only focus rows.")
    parser.add_argument("--base-catalog", default=str(DEFAULT_BASE_CATALOG))
    parser.add_argument("--rules", default=str(DEFAULT_RULES_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    base_catalog = permit_diagnosis_calculator._load_catalog(
        Path(args.base_catalog).expanduser().resolve(),
        merge_focus_seed=False,
    )
    rule_catalog = permit_diagnosis_calculator._load_rule_catalog(Path(args.rules).expanduser().resolve())
    payload = build_focus_seed_catalog(base_catalog, rule_catalog)

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(payload), encoding="utf-8")

    print(f"[saved-json] {json_output}")
    print(f"[saved-md] {md_output}")
    print(f"[seed_industry_total] {payload['summary']['seed_industry_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
