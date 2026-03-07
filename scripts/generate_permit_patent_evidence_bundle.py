from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FOCUS_SEED_INPUT = ROOT / "config" / "permit_focus_seed_catalog.json"
DEFAULT_FOCUS_FAMILY_REGISTRY_INPUT = ROOT / "config" / "permit_focus_family_registry.json"
DEFAULT_MASTER_INPUT = ROOT / "logs" / "permit_master_catalog_latest.json"
DEFAULT_FOCUS_REPORT_INPUT = ROOT / "logs" / "permit_focus_priority_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_patent_evidence_bundle_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_patent_evidence_bundle_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit patent evidence input must be a JSON object")
    return payload


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _profile(row: Dict[str, Any]) -> Dict[str, Any]:
    profile = row.get("registration_requirement_profile") or {}
    return profile if isinstance(profile, dict) else {}


def _raw_source_proof(row: Dict[str, Any]) -> Dict[str, Any]:
    proof = row.get("raw_source_proof") or {}
    return proof if isinstance(proof, dict) else {}


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


def _claim_id(family_key: str) -> str:
    digest = hashlib.sha1(_safe_str(family_key).encode("utf-8")).hexdigest()[:10]
    return f"permit-family-{digest}"


def _profile_input_domains(rows: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    required_inputs = ["industry_selector", "capital_eok", "technicians_count"]
    optional_domains: List[str] = []
    for item in rows:
        profile = _profile(item)
        other_components = {
            _safe_str(component)
            for component in list(profile.get("other_components") or [])
            if _safe_str(component)
        }
        if profile.get("other_required"):
            optional_domains.append("other_requirement_checklist")
        if profile.get("equipment_count_required") or "equipment" in other_components:
            optional_domains.append("equipment_inventory")
        if profile.get("deposit_days_required") or "deposit" in other_components:
            optional_domains.append("deposit_hold_days")
        if "safety_environment" in other_components:
            optional_domains.append("safety_environment")
        if "facility_equipment" in other_components:
            optional_domains.append("facility_equipment")
    return {
        "required_input_domains": _unique_nonempty(required_inputs),
        "optional_input_domains": _unique_nonempty(optional_domains),
    }


def _claim_packet(
    *,
    family_key: str,
    rows: List[Dict[str, Any]],
    selector_alias_total: int,
    proof_row_total: int,
    proof_urls: List[str],
    proof_checksums: List[str],
    sample_selector_codes: List[str],
) -> Dict[str, Any]:
    capitals = [_safe_float(_profile(item).get("capital_eok")) for item in rows]
    technicians = [_safe_int(_profile(item).get("technicians_required")) for item in rows]
    input_domains = _profile_input_domains(rows)
    checksum_samples = _unique_nonempty(proof_checksums)[:6]
    url_samples = _unique_nonempty(proof_urls)[:6]
    sample_names = [_safe_str(item.get("service_name")) for item in rows[:6]]
    basis_titles = _unique_nonempty([_safe_str(item.get("legal_basis_title")) for item in rows])[:4]
    other_components = _unique_nonempty(
        [
            _safe_str(component)
            for item in rows
            for component in list(_profile(item).get("other_components") or [])
            if _safe_str(component)
        ]
    )
    claim_statement = (
        f"{family_key} 법령군 {len(rows)}건은 자본금 {min(capitals) if capitals else 0.0}~"
        f"{max(capitals) if capitals else 0.0}억, 기술인력 {min(technicians) if technicians else 0}~"
        f"{max(technicians) if technicians else 0}명 범위를 구조화하고 동일 selector/master/widget 계약으로 제공한다."
    )
    calculation_steps = [
        "업종 선택은 canonical service_code와 selector alias를 동시에 해석한다.",
        "자본금은 법령군별 최소 기준과 입력 capital_eok를 비교한다.",
        "기술인력은 법령군별 최소 기준과 입력 technicians_count를 비교한다.",
    ]
    if input_domains["optional_input_domains"]:
        calculation_steps.append(
            "기타 요건은 구조화된 requirement domain을 checklist 형태로 분리 노출한다."
        )
    calculation_steps.append("raw source checksum과 official snapshot note를 근거 패킷에 함께 연결한다.")
    return {
        "claim_id": _claim_id(family_key),
        "claim_title": f"{family_key} 등록기준 패킷",
        "claim_statement": claim_statement,
        "covered_input_domains": input_domains["required_input_domains"] + input_domains["optional_input_domains"],
        "required_input_domains": input_domains["required_input_domains"],
        "optional_input_domains": input_domains["optional_input_domains"],
        "calculation_steps": calculation_steps,
        "ui_surfaces": [
            "ai_permit_precheck.html",
            "permit_master_catalog_latest.json",
            "permit_selector_catalog_latest.json",
            "widget_rental_catalog_latest.json",
            "api_contract_spec_latest.json",
        ],
        "evidence_chain": [
            f"family_key={family_key}",
            f"selector_alias_total={selector_alias_total}",
            f"raw_source_proof_rows={proof_row_total}/{len(rows)}",
            "law.go.kr curated family registry snapshot",
        ],
        "source_proof_summary": {
            "proof_status": "raw_source_hardened" if proof_row_total == len(rows) else "partial_raw_source_proof",
            "row_total": len(rows),
            "proof_coverage_ratio": f"{proof_row_total}/{len(rows)}",
            "source_url_total": len(url_samples),
            "checksum_total": len(_unique_nonempty(proof_checksums)),
            "checksum_sample_total": len(checksum_samples),
            "checksum_samples": checksum_samples,
            "source_url_samples": url_samples,
        },
        "selector_surface_summary": {
            "selector_alias_total": selector_alias_total,
            "sample_selector_codes": _unique_nonempty(sample_selector_codes)[:6],
        },
        "profile_bounds": {
            "capital_min_eok": min(capitals) if capitals else 0.0,
            "capital_max_eok": max(capitals) if capitals else 0.0,
            "technicians_min": min(technicians) if technicians else 0,
            "technicians_max": max(technicians) if technicians else 0,
            "other_components": other_components,
        },
        "sample_services": _unique_nonempty(sample_names),
        "legal_basis_titles": basis_titles,
        "claim_packet_complete": bool(rows) and proof_row_total == len(rows) and bool(url_samples),
    }


def build_bundle(
    *,
    focus_seed_catalog: Dict[str, Any],
    focus_family_registry: Dict[str, Any],
    master_catalog: Dict[str, Any],
    focus_report: Dict[str, Any],
) -> Dict[str, Any]:
    seed_rows = [row for row in list(focus_seed_catalog.get("industries") or []) if isinstance(row, dict)]
    family_registry_rows = [
        row for row in list(focus_family_registry.get("industries") or []) if isinstance(row, dict)
    ]
    master_rows = [row for row in list(master_catalog.get("industries") or []) if isinstance(row, dict)]
    master_by_code = {
        _safe_str(row.get("service_code")): row
        for row in master_rows
        if _safe_str(row.get("service_code"))
    }
    family_registry_codes = {
        _safe_str(row.get("service_code"))
        for row in family_registry_rows
        if _safe_str(row.get("service_code"))
    }
    focus_source_rows = list(family_registry_rows) + [
        row
        for row in seed_rows
        if _safe_str(row.get("service_code")) not in family_registry_codes
    ]

    families: Dict[str, List[Dict[str, Any]]] = {}
    for row in focus_source_rows:
        family_key = _safe_str(row.get("law_title")) or _safe_str(row.get("seed_law_family")) or "unknown"
        families.setdefault(family_key, []).append(row)

    family_rows: List[Dict[str, Any]] = []
    for family_key, grouped_rows in families.items():
        sorted_rows = sorted(
            grouped_rows,
            key=lambda item: (
                -_safe_float(_profile(item).get("capital_eok")),
                -_safe_int(_profile(item).get("technicians_required")),
                _safe_str(item.get("service_name")),
            ),
        )
        capitals = [_safe_float(_profile(item).get("capital_eok")) for item in sorted_rows]
        technicians = [_safe_int(_profile(item).get("technicians_required")) for item in sorted_rows]
        alias_total = 0
        selector_codes: List[str] = []
        proof_rows = 0
        proof_urls: List[str] = []
        proof_checksums: List[str] = []
        for item in sorted_rows:
            master_row = master_by_code.get(_safe_str(item.get("service_code"))) or {}
            aliases = [
                alias
                for alias in list(master_row.get("platform_selector_aliases") or [])
                if isinstance(alias, dict)
            ]
            alias_total += len(aliases)
            selector_codes.extend(
                [
                    _safe_str(alias.get("selector_code"))
                    for alias in aliases
                    if _safe_str(alias.get("selector_code"))
                ]
            )
            proof = _raw_source_proof(item)
            if _safe_str(proof.get("source_checksum")):
                proof_rows += 1
            proof_urls.extend([_safe_str(url) for url in list(proof.get("source_urls") or [])])
            proof_checksums.append(_safe_str(proof.get("source_checksum")))
        claim_packet = _claim_packet(
            family_key=family_key,
            rows=sorted_rows,
            selector_alias_total=alias_total,
            proof_row_total=proof_rows,
            proof_urls=proof_urls,
            proof_checksums=proof_checksums,
            sample_selector_codes=selector_codes,
        )
        family_rows.append(
            {
                "family_key": family_key,
                "group_name": _safe_str(sorted_rows[0].get("group_name")),
                "row_total": len(sorted_rows),
                "capital_min_eok": min(capitals) if capitals else 0.0,
                "capital_max_eok": max(capitals) if capitals else 0.0,
                "technicians_min": min(technicians) if technicians else 0,
                "technicians_max": max(technicians) if technicians else 0,
                "selector_alias_total": alias_total,
                "raw_source_proof_row_total": proof_rows,
                "raw_source_proof_url_total": len(_unique_nonempty(proof_urls)),
                "raw_source_proof_checksums": _unique_nonempty(proof_checksums)[:8],
                "raw_source_proof_urls": _unique_nonempty(proof_urls)[:8],
                "sample_service_codes": [_safe_str(item.get("service_code")) for item in sorted_rows[:8]],
                "sample_service_names": [_safe_str(item.get("service_name")) for item in sorted_rows[:8]],
                "sample_selector_codes": _unique_nonempty(selector_codes)[:8],
                "claim_focus": [
                    "법령군별 등록기준 구조화",
                    "자본금·기술인력 requirement profile 정규화",
                    "selector/master/widget 동일 코드 계약",
                    "raw-source checksum 및 capture meta 결합",
                ],
                "claim_packet": claim_packet,
                "claim_packet_complete": bool(claim_packet.get("claim_packet_complete")),
            }
        )

    family_rows.sort(key=lambda row: (-_safe_int(row.get("row_total")), _safe_str(row.get("family_key"))))
    focus_summary = dict(focus_report.get("summary") or {})
    core_only_total = _safe_int(focus_summary.get("focus_core_only_total"))
    raw_source_proof_row_total = sum(_safe_int(row.get("raw_source_proof_row_total")) for row in family_rows)
    raw_source_proof_family_total = sum(
        1
        for row in family_rows
        if _safe_int(row.get("raw_source_proof_row_total")) == _safe_int(row.get("row_total"))
    )
    claim_packet_family_total = sum(1 for row in family_rows if isinstance(row.get("claim_packet"), dict))
    claim_packet_complete_family_total = sum(1 for row in family_rows if bool(row.get("claim_packet_complete")))
    checksum_sample_family_total = sum(
        1
        for row in family_rows
        if len(list(((row.get("claim_packet") or {}).get("source_proof_summary") or {}).get("checksum_samples") or [])) > 0
    )
    execution_lane_id = (
        "patent_evidence_bundle_lock"
        if claim_packet_complete_family_total < len(family_rows)
        else "platform_contract_proof_surface"
    )
    parallel_lane_id = (
        "platform_contract_proof_surface"
        if execution_lane_id == "patent_evidence_bundle_lock"
        else "runtime_proof_disclosure"
    )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "focus_source_row_total": len(focus_source_rows),
            "focus_source_family_total": len(family_rows),
            "focus_seed_row_total": len(seed_rows),
            "focus_family_registry_row_total": len(family_registry_rows),
            "focus_seed_family_total": len(family_rows),
            "master_row_total": len(master_rows),
            "real_focus_target_total": _safe_int(focus_summary.get("real_focus_target_total")),
            "focus_core_only_total": core_only_total,
            "raw_source_proof_row_total": raw_source_proof_row_total,
            "raw_source_proof_family_total": raw_source_proof_family_total,
            "claim_packet_family_total": claim_packet_family_total,
            "claim_packet_complete_family_total": claim_packet_complete_family_total,
            "checksum_sample_family_total": checksum_sample_family_total,
            "execution_lane_id": execution_lane_id,
            "parallel_lane_id": parallel_lane_id,
        },
        "evidence_artifacts": {
            "focus_seed_catalog": str(DEFAULT_FOCUS_SEED_INPUT),
            "focus_family_registry": str(DEFAULT_FOCUS_FAMILY_REGISTRY_INPUT),
            "master_catalog": str(DEFAULT_MASTER_INPUT),
            "focus_report": str(DEFAULT_FOCUS_REPORT_INPUT),
            "ui_output": str(ROOT / "output" / "ai_permit_precheck.html"),
            "widget_contract": str(ROOT / "logs" / "widget_rental_catalog_latest.json"),
            "api_contract_spec": str(ROOT / "logs" / "api_contract_spec_latest.json"),
        },
        "claim_strategy": [
            "자본금·기술인력 동시 요구 업종만 청구범위에 포함",
            "법령군 단위 family와 selector/master 계약을 함께 증빙",
            "focus-seed와 focus-family-registry를 구분 표시하고 official source upgrade 진행상황을 분리 서술",
        ],
        "families": family_rows,
    }


def render_markdown(bundle: Dict[str, Any]) -> str:
    summary = dict(bundle.get("summary") or {})
    evidence_artifacts = dict(bundle.get("evidence_artifacts") or {})
    lines = [
        "# Permit Patent Evidence Bundle",
        "",
        "## Summary",
        f"- focus_source_row_total: `{summary.get('focus_source_row_total', 0)}`",
        f"- focus_source_family_total: `{summary.get('focus_source_family_total', 0)}`",
        f"- focus_seed_row_total: `{summary.get('focus_seed_row_total', 0)}`",
        f"- focus_family_registry_row_total: `{summary.get('focus_family_registry_row_total', 0)}`",
        f"- focus_seed_family_total: `{summary.get('focus_seed_family_total', 0)}`",
        f"- master_row_total: `{summary.get('master_row_total', 0)}`",
        f"- real_focus_target_total: `{summary.get('real_focus_target_total', 0)}`",
        f"- focus_core_only_total: `{summary.get('focus_core_only_total', 0)}`",
        f"- raw_source_proof_row_total: `{summary.get('raw_source_proof_row_total', 0)}`",
        f"- raw_source_proof_family_total: `{summary.get('raw_source_proof_family_total', 0)}`",
        f"- claim_packet_family_total: `{summary.get('claim_packet_family_total', 0)}`",
        f"- claim_packet_complete_family_total: `{summary.get('claim_packet_complete_family_total', 0)}`",
        f"- checksum_sample_family_total: `{summary.get('checksum_sample_family_total', 0)}`",
        f"- execution_lane_id: `{summary.get('execution_lane_id', '')}`",
        f"- parallel_lane_id: `{summary.get('parallel_lane_id', '')}`",
        "",
        "## Evidence Artifacts",
    ]
    for key, value in evidence_artifacts.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Claim Strategy"])
    for item in list(bundle.get("claim_strategy") or []):
        lines.append(f"- {item}")
    lines.extend(["", "## Families"])
    families = list(bundle.get("families") or [])
    if not families:
        lines.append("- none")
    else:
        for row in families:
            sample_codes = ", ".join(str(item) for item in list(row.get("sample_service_codes") or [])[:5])
            lines.append(
                f"- `{row.get('family_key', '')}` rows={row.get('row_total', 0)}"
                f" / capital {row.get('capital_min_eok', 0)}~{row.get('capital_max_eok', 0)}억"
                f" / technicians {row.get('technicians_min', 0)}~{row.get('technicians_max', 0)}명"
                f" / selector_alias_total {row.get('selector_alias_total', 0)}"
                f" / raw_source_proof {row.get('raw_source_proof_row_total', 0)}/{row.get('row_total', 0)}"
                f" / claim `{((row.get('claim_packet') or {}).get('claim_id', ''))}`"
                + (f" / sample {sample_codes}" if sample_codes else "")
            )
            claim_packet = row.get("claim_packet") or {}
            source_proof_summary = (
                (claim_packet.get("source_proof_summary") or {})
                if isinstance(claim_packet, dict)
                else {}
            )
            claim_statement = (
                _safe_str(claim_packet.get("claim_statement"))
                if isinstance(claim_packet, dict)
                else ""
            )
            if claim_statement:
                lines.append(f"  claim_statement: {claim_statement}")
            if source_proof_summary:
                lines.append(
                    "  proof_surface:"
                    f" coverage={source_proof_summary.get('proof_coverage_ratio', '')}"
                    f" checksum_samples={source_proof_summary.get('checksum_sample_total', 0)}"
                    f" urls={source_proof_summary.get('source_url_total', 0)}"
                )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a permit patent evidence bundle for focus families.")
    parser.add_argument("--focus-seed-input", default=str(DEFAULT_FOCUS_SEED_INPUT))
    parser.add_argument("--focus-family-registry-input", default=str(DEFAULT_FOCUS_FAMILY_REGISTRY_INPUT))
    parser.add_argument("--master-input", default=str(DEFAULT_MASTER_INPUT))
    parser.add_argument("--focus-report-input", default=str(DEFAULT_FOCUS_REPORT_INPUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    bundle = build_bundle(
        focus_seed_catalog=_load_json(Path(args.focus_seed_input).expanduser().resolve()),
        focus_family_registry=_load_json(Path(args.focus_family_registry_input).expanduser().resolve()),
        master_catalog=_load_json(Path(args.master_input).expanduser().resolve()),
        focus_report=_load_json(Path(args.focus_report_input).expanduser().resolve()),
    )

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(bundle), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
