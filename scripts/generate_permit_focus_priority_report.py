from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import permit_diagnosis_calculator  # noqa: E402


DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_focus_priority_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_focus_priority_latest.md"
FOCUS_SELECTOR_CATEGORY_CODE = "SEL-FOCUS"
INFERRED_SELECTOR_CATEGORY_CODE = "SEL-INFERRED"


def _load_payload(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("focus report input must be a JSON object")
    return data


def _is_rules_only(row: Dict[str, Any]) -> bool:
    return str(row.get("service_code", "") or "").strip().startswith("RULE::")


def _profile(row: Dict[str, Any]) -> Dict[str, Any]:
    profile = row.get("registration_requirement_profile") or {}
    return profile if isinstance(profile, dict) else {}


def _is_capital_technical_scope(row: Dict[str, Any]) -> bool:
    profile = _profile(row)
    return bool(profile.get("capital_required")) and bool(profile.get("technical_personnel_required"))


def _law_basis_title(row: Dict[str, Any]) -> str:
    title = str(row.get("legal_basis_title", "") or "").strip()
    if title:
        return title
    legal_basis = list(row.get("legal_basis") or [])
    if legal_basis:
        return str(legal_basis[0].get("article", "") or "").strip()
    return ""


def _law_title(row: Dict[str, Any]) -> str:
    title = str(row.get("law_title", "") or "").strip()
    if title:
        return title
    legal_basis = list(row.get("legal_basis") or [])
    if legal_basis:
        return str(legal_basis[0].get("law_title", "") or "").strip()
    return ""


def _selector_entry(row: Dict[str, Any], selector_kind: str) -> Dict[str, str]:
    service_code = str(row.get("service_code", "") or "").strip()
    selector_suffix = service_code
    if selector_suffix.startswith("FOCUS::"):
        selector_suffix = selector_suffix.split("FOCUS::", 1)[1]
    kind = str(selector_kind or "").strip().lower()
    if kind == "inferred":
        return {
            "selector_kind": "inferred",
            "selector_code": f"SEL::INFERRED::{selector_suffix}",
            "selector_category_code": INFERRED_SELECTOR_CATEGORY_CODE,
            "selector_category_name": "추론 점검군",
        }
    return {
        "selector_kind": "focus",
        "selector_code": f"SEL::FOCUS::{selector_suffix}",
        "selector_category_code": FOCUS_SELECTOR_CATEGORY_CODE,
        "selector_category_name": "핵심 업종군",
    }


def _normalize_focus_row(row: Dict[str, Any], selector_kind: str) -> Dict[str, Any]:
    profile = _profile(row)
    normalized = {
        "service_code": str(row.get("service_code", "") or "").strip(),
        "service_name": str(row.get("service_name", "") or "").strip(),
        "major_name": str(row.get("major_name", "") or "").strip(),
        "is_rules_only": _is_rules_only(row),
        "focus_bucket": str(profile.get("focus_bucket", "") or "").strip(),
        "profile_source": str(profile.get("profile_source", "") or "").strip(),
        "capital_eok": float(profile.get("capital_eok", 0) or 0),
        "technicians_required": int(profile.get("technicians_required", 0) or 0),
        "other_components": list(profile.get("other_components") or []),
        "law_title": _law_title(row),
        "legal_basis_title": _law_basis_title(row),
        "criteria_source_type": str(row.get("criteria_source_type", "") or "").strip(),
        "quality_flags": list(row.get("quality_flags") or []),
        "status": str(row.get("status", row.get("collection_status", "")) or "").strip(),
    }
    normalized.update(_selector_entry(row, selector_kind))
    return normalized


def _sort_focus_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            1 if row.get("is_rules_only") else 0,
            -float(row.get("capital_eok", 0) or 0),
            -int(row.get("technicians_required", 0) or 0),
            str(row.get("service_name", "") or ""),
        ),
    )


def build_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    industries = [
        row
        for row in list(payload.get("industries") or [])
        if isinstance(row, dict) and _is_capital_technical_scope(row)
    ]
    focus_rows = [
        _normalize_focus_row(row, "focus")
        for row in industries
        if bool(_profile(row).get("focus_target"))
    ]
    focus_with_other_rows = [
        _normalize_focus_row(row, "focus")
        for row in industries
        if bool(_profile(row).get("focus_target_with_other"))
    ]
    core_only_rows = [
        _normalize_focus_row(row, "focus")
        for row in industries
        if bool(_profile(row).get("focus_target")) and not bool(_profile(row).get("focus_target_with_other"))
    ]
    inferred = [
        _normalize_focus_row(row, "inferred")
        for row in industries
        if bool(_profile(row).get("inferred_focus_candidate"))
    ]
    focus_rows = _sort_focus_rows(focus_rows)
    focus_with_other_rows = _sort_focus_rows(focus_with_other_rows)
    core_only_rows = _sort_focus_rows(core_only_rows)
    inferred = _sort_focus_rows(inferred)

    real_focus_rows = [row for row in focus_rows if not row.get("is_rules_only")]
    rules_only_focus_rows = [row for row in focus_rows if row.get("is_rules_only")]
    real_focus_with_other_rows = [row for row in focus_with_other_rows if not row.get("is_rules_only")]
    rules_only_focus_with_other_rows = [row for row in focus_with_other_rows if row.get("is_rules_only")]
    real_core_only_rows = [row for row in core_only_rows if not row.get("is_rules_only")]
    rules_only_core_only_rows = [row for row in core_only_rows if row.get("is_rules_only")]

    summary = {
        "generated_at": str(payload.get("generated_at", "") or datetime.now().isoformat(timespec="seconds")),
        "scope_industry_total": len(industries),
        "scope_real_industry_total": sum(1 for row in industries if not _is_rules_only(row)),
        "scope_rules_only_industry_total": sum(1 for row in industries if _is_rules_only(row)),
        "focus_target_total": len(focus_rows),
        "real_focus_target_total": len(real_focus_rows),
        "rules_only_focus_target_total": len(rules_only_focus_rows),
        "selector_ready_focus_total": len(focus_rows),
        "focus_target_with_other_total": len(focus_with_other_rows),
        "real_focus_target_with_other_total": len(real_focus_with_other_rows),
        "rules_only_focus_target_with_other_total": len(rules_only_focus_with_other_rows),
        "selector_ready_focus_with_other_total": len(focus_with_other_rows),
        "focus_core_only_total": len(core_only_rows),
        "real_focus_core_only_total": len(real_core_only_rows),
        "rules_only_focus_core_only_total": len(rules_only_core_only_rows),
        "inferred_focus_total": len(inferred),
        "selector_ready_inferred_total": len(inferred),
        # Legacy aliases kept for downstream compatibility.
        "high_confidence_focus_total": len(focus_rows),
        "real_high_confidence_focus_total": len(real_focus_rows),
        "rules_only_high_confidence_focus_total": len(rules_only_focus_rows),
        "selector_ready_high_confidence_total": len(focus_rows),
        "partial_core_total": len(core_only_rows),
    }

    priority_actions: List[str] = []
    if not real_focus_rows:
        priority_actions.append(
            "실업종 selector에는 자본금·기술인력 필수 핵심 업종이 없으므로, rule-only 핵심 업종군을 실제 선택 row로 편입해야 한다."
        )
    if inferred:
        priority_actions.append(
            f"추론 후보 {len(inferred)}건은 오탐 가능성이 있으므로 고신뢰 핵심 업종군과 분리된 재검증 큐로 유지해야 한다."
        )
    if rules_only_focus_rows:
        priority_actions.append(
            f"등록기준 업종군 {len(rules_only_focus_rows)}건은 selector_code가 준비됐으므로 seoulmna.kr와 임대형 widget에서 동일 코드로 먼저 노출할 수 있다."
        )
    if core_only_rows:
        priority_actions.append(
            f"기타 요소 없이 자본금·기술인력만으로 성립하는 핵심 업종 {len(core_only_rows)}건은 with_other 지표와 분리해 raw 근거를 우선 보강해야 한다."
        )

    return {
        "summary": summary,
        "priority_actions": priority_actions,
        "focus_target_rows": focus_rows,
        "focus_target_with_other_rows": focus_with_other_rows,
        "focus_core_only_rows": core_only_rows,
        "inferred_focus_candidates": inferred,
        # Legacy aliases kept for downstream compatibility.
        "high_confidence_focus": focus_rows,
        "partial_core_focus": core_only_rows,
    }


def _row_label(row: Dict[str, Any]) -> str:
    prefix = "RULE" if row.get("is_rules_only") else "REAL"
    other_components = ", ".join(str(item) for item in list(row.get("other_components") or []))
    details = [
        f"{prefix}",
        f"자본금 {row.get('capital_eok', 0)}억",
        f"기술인력 {row.get('technicians_required', 0)}명",
    ]
    if other_components:
        details.append(f"기타 {other_components}")
    return " / ".join(details)


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    lines = [
        "# Permit Focus Priority Report",
        "",
        "## Summary",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- scope_industry_total: `{summary.get('scope_industry_total', 0)}`",
        f"- scope_real_industry_total: `{summary.get('scope_real_industry_total', 0)}`",
        f"- scope_rules_only_industry_total: `{summary.get('scope_rules_only_industry_total', 0)}`",
        f"- focus_target_total: `{summary.get('focus_target_total', 0)}`",
        f"- real_focus_target_total: `{summary.get('real_focus_target_total', 0)}`",
        f"- rules_only_focus_target_total: `{summary.get('rules_only_focus_target_total', 0)}`",
        f"- selector_ready_focus_total: `{summary.get('selector_ready_focus_total', 0)}`",
        f"- focus_target_with_other_total: `{summary.get('focus_target_with_other_total', 0)}`",
        f"- real_focus_target_with_other_total: `{summary.get('real_focus_target_with_other_total', 0)}`",
        f"- rules_only_focus_target_with_other_total: `{summary.get('rules_only_focus_target_with_other_total', 0)}`",
        f"- focus_core_only_total: `{summary.get('focus_core_only_total', 0)}`",
        f"- inferred_focus_total: `{summary.get('inferred_focus_total', 0)}`",
        f"- selector_ready_inferred_total: `{summary.get('selector_ready_inferred_total', 0)}`",
        "",
        "## Priority Actions",
    ]
    actions = list(report.get("priority_actions") or [])
    if actions:
        lines.extend(f"- {item}" for item in actions)
    else:
        lines.append("- none")

    sections = (
        ("Capital + Technical Focus", list(report.get("focus_target_rows") or []), 20),
        ("Capital + Technical + Other", list(report.get("focus_target_with_other_rows") or []), 15),
        ("Capital + Technical Core Only", list(report.get("focus_core_only_rows") or []), 10),
        ("Inferred Focus Candidates", list(report.get("inferred_focus_candidates") or []), 10),
    )
    for title, rows, limit in sections:
        lines.extend(["", f"## {title}"])
        if not rows:
            lines.append("- none")
            continue
        for row in rows[:limit]:
            law_bits = " / ".join(
                bit for bit in [str(row.get("law_title", "") or "").strip(), str(row.get("legal_basis_title", "") or "").strip()] if bit
            )
            selector_bits = " / ".join(
                bit
                for bit in [str(row.get("selector_category_name", "") or "").strip(), str(row.get("selector_code", "") or "").strip()]
                if bit
            )
            lines.append(
                f"- `{row.get('service_code', '')}` {row.get('service_name', '')}: {_row_label(row)}"
                + (f" / selector {selector_bits}" if selector_bits else "")
                + (f" / 법령 {law_bits}" if law_bits else "")
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a focus report for permit industries.")
    parser.add_argument("--input", default="")
    parser.add_argument("--catalog", default=str(permit_diagnosis_calculator.DEFAULT_CATALOG_PATH))
    parser.add_argument("--rules", default=str(permit_diagnosis_calculator.DEFAULT_RULES_PATH))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    if str(args.input or "").strip():
        payload = _load_payload(Path(args.input).expanduser().resolve())
    else:
        catalog = permit_diagnosis_calculator._load_catalog(Path(args.catalog).expanduser().resolve())
        rules = permit_diagnosis_calculator._load_rule_catalog(Path(args.rules).expanduser().resolve())
        payload = dict((permit_diagnosis_calculator.build_bootstrap_payload(catalog, rules) or {}).get("permitCatalog") or {})
    report = build_report(payload)

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(report), encoding="utf-8")

    print(f"[saved-json] {json_output}")
    print(f"[saved-md] {md_output}")
    print(f"[focus_target_total] {report['summary']['focus_target_total']}")
    print(f"[real_focus_target_total] {report['summary']['real_focus_target_total']}")
    print(f"[focus_target_with_other_total] {report['summary']['focus_target_with_other_total']}")
    print(f"[inferred_focus_total] {report['summary']['inferred_focus_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
