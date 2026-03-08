#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GOLDSET_INPUT = ROOT / "logs" / "permit_family_case_goldset_latest.json"
DEFAULT_RUNTIME_ASSERTIONS_INPUT = ROOT / "logs" / "permit_runtime_case_assertions_latest.json"
DEFAULT_WIDGET_INPUT = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_API_CONTRACT_INPUT = ROOT / "logs" / "api_contract_spec_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_case_release_guard_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_case_release_guard_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit case release guard input must be a JSON object")
    return payload


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except Exception:
        return 0


def _collect_goldset_cases(payload: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
    families: Set[str] = set()
    cases: Set[str] = set()
    for family in [row for row in list(payload.get("families") or []) if isinstance(row, dict)]:
        family_key = _safe_str(family.get("family_key"))
        if family_key:
            families.add(family_key)
        for case in [item for item in list(family.get("cases") or []) if isinstance(item, dict)]:
            case_id = _safe_str(case.get("case_id"))
            if case_id:
                cases.add(case_id)
    return families, cases


def _collect_runtime_cases(payload: Dict[str, Any]) -> Tuple[Set[str], Set[str], Set[str]]:
    families: Set[str] = set()
    asserted_cases: Set[str] = set()
    failed_cases: Set[str] = set()
    for family in [row for row in list(payload.get("families") or []) if isinstance(row, dict)]:
        family_key = _safe_str(family.get("family_key"))
        if family_key:
            families.add(family_key)
        for case in [item for item in list(family.get("cases") or []) if isinstance(item, dict)]:
            case_id = _safe_str(case.get("case_id"))
            if not case_id:
                continue
            if bool(case.get("ok")):
                asserted_cases.add(case_id)
            else:
                failed_cases.add(case_id)
    return families, asserted_cases, failed_cases


def _collect_widget_cases(payload: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
    packaging = payload.get("packaging") if isinstance(payload.get("packaging"), dict) else {}
    partner_rental = packaging.get("partner_rental") if isinstance(packaging.get("partner_rental"), dict) else {}
    permit_widget_feeds = (
        partner_rental.get("permit_widget_feeds")
        if isinstance(partner_rental.get("permit_widget_feeds"), dict)
        else {}
    )
    families: Set[str] = set()
    cases: Set[str] = set()
    for sample in [row for row in list(permit_widget_feeds.get("family_case_samples") or []) if isinstance(row, dict)]:
        family_key = _safe_str(sample.get("family_key"))
        case_id = _safe_str(sample.get("case_id"))
        if family_key:
            families.add(family_key)
        if case_id:
            cases.add(case_id)
    return families, cases


def _collect_api_cases(payload: Dict[str, Any]) -> Tuple[Set[str], Set[str]]:
    services = payload.get("services") if isinstance(payload.get("services"), dict) else {}
    permit_service = services.get("permit") if isinstance(services.get("permit"), dict) else {}
    response_contract = (
        permit_service.get("response_contract") if isinstance(permit_service.get("response_contract"), dict) else {}
    )
    catalog_contracts = (
        response_contract.get("catalog_contracts") if isinstance(response_contract.get("catalog_contracts"), dict) else {}
    )
    master_catalog = (
        catalog_contracts.get("master_catalog")
        if isinstance(catalog_contracts.get("master_catalog"), dict)
        else {}
    )
    proof_surface_examples = (
        master_catalog.get("proof_surface_examples")
        if isinstance(master_catalog.get("proof_surface_examples"), dict)
        else {}
    )
    families: Set[str] = set()
    cases: Set[str] = set()
    for sample in [row for row in list(proof_surface_examples.get("family_case_samples") or []) if isinstance(row, dict)]:
        family_key = _safe_str(sample.get("family_key"))
        case_id = _safe_str(sample.get("case_id"))
        if family_key:
            families.add(family_key)
        if case_id:
            cases.add(case_id)
    return families, cases


def _sorted_sample(values: Set[str], limit: int = 12) -> List[str]:
    return sorted(values)[:limit]


def build_release_guard(
    *,
    permit_family_case_goldset: Dict[str, Any],
    permit_runtime_case_assertions: Dict[str, Any],
    widget_rental_catalog: Dict[str, Any],
    api_contract_spec: Dict[str, Any],
) -> Dict[str, Any]:
    goldset_family_keys, goldset_case_ids = _collect_goldset_cases(permit_family_case_goldset)
    runtime_family_keys, runtime_case_ids, runtime_failed_case_ids = _collect_runtime_cases(permit_runtime_case_assertions)
    widget_family_keys, widget_case_ids = _collect_widget_cases(widget_rental_catalog)
    api_family_keys, api_case_ids = _collect_api_cases(api_contract_spec)

    runtime_missing_families = goldset_family_keys - runtime_family_keys
    widget_missing_families = goldset_family_keys - widget_family_keys
    api_missing_families = goldset_family_keys - api_family_keys

    runtime_missing_cases = goldset_case_ids - runtime_case_ids
    widget_missing_cases = goldset_case_ids - widget_case_ids
    api_missing_cases = goldset_case_ids - api_case_ids

    runtime_extra_cases = runtime_case_ids - goldset_case_ids
    widget_extra_cases = widget_case_ids - goldset_case_ids
    api_extra_cases = api_case_ids - goldset_case_ids

    runtime_summary = (
        permit_runtime_case_assertions.get("summary")
        if isinstance(permit_runtime_case_assertions.get("summary"), dict)
        else {}
    )
    runtime_ready = bool(runtime_summary.get("runtime_assertions_ready"))
    release_guard_ready = (
        bool(goldset_family_keys)
        and runtime_ready
        and not runtime_missing_families
        and not widget_missing_families
        and not api_missing_families
        and not runtime_missing_cases
        and not widget_missing_cases
        and not api_missing_cases
        and not runtime_failed_case_ids
        and not runtime_extra_cases
        and not widget_extra_cases
        and not api_extra_cases
    )

    summary = {
        "family_total": len(goldset_family_keys),
        "case_total": len(goldset_case_ids),
        "runtime_family_total": len(runtime_family_keys),
        "runtime_case_total": len(runtime_case_ids),
        "runtime_failed_case_total": len(runtime_failed_case_ids),
        "widget_family_total": len(widget_family_keys),
        "widget_case_total": len(widget_case_ids),
        "api_family_total": len(api_family_keys),
        "api_case_total": len(api_case_ids),
        "runtime_missing_family_total": len(runtime_missing_families),
        "widget_missing_family_total": len(widget_missing_families),
        "api_missing_family_total": len(api_missing_families),
        "runtime_missing_case_total": len(runtime_missing_cases),
        "widget_missing_case_total": len(widget_missing_cases),
        "api_missing_case_total": len(api_missing_cases),
        "runtime_extra_case_total": len(runtime_extra_cases),
        "widget_extra_case_total": len(widget_extra_cases),
        "api_extra_case_total": len(api_extra_cases),
        "execution_lane_id": "case_release_guard",
        "parallel_lane_id": "family_case_edge_expansion",
        "release_guard_ready": release_guard_ready,
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": summary,
        "source_paths": {
            "family_case_goldset": str(DEFAULT_GOLDSET_INPUT.resolve()),
            "runtime_case_assertions": str(DEFAULT_RUNTIME_ASSERTIONS_INPUT.resolve()),
            "widget_rental_catalog": str(DEFAULT_WIDGET_INPUT.resolve()),
            "api_contract_spec": str(DEFAULT_API_CONTRACT_INPUT.resolve()),
        },
        "missing": {
            "runtime_families": _sorted_sample(runtime_missing_families),
            "widget_families": _sorted_sample(widget_missing_families),
            "api_families": _sorted_sample(api_missing_families),
            "runtime_cases": _sorted_sample(runtime_missing_cases),
            "widget_cases": _sorted_sample(widget_missing_cases),
            "api_cases": _sorted_sample(api_missing_cases),
        },
        "extras": {
            "runtime_cases": _sorted_sample(runtime_extra_cases),
            "widget_cases": _sorted_sample(widget_extra_cases),
            "api_cases": _sorted_sample(api_extra_cases),
        },
        "runtime_failed_case_ids": _sorted_sample(runtime_failed_case_ids),
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    missing = dict(report.get("missing") or {})
    extras = dict(report.get("extras") or {})
    lines = [
        "# Permit Case Release Guard",
        "",
        "## Summary",
        f"- family_total: `{summary.get('family_total', 0)}`",
        f"- case_total: `{summary.get('case_total', 0)}`",
        f"- runtime_family_total: `{summary.get('runtime_family_total', 0)}`",
        f"- widget_family_total: `{summary.get('widget_family_total', 0)}`",
        f"- api_family_total: `{summary.get('api_family_total', 0)}`",
        f"- runtime_failed_case_total: `{summary.get('runtime_failed_case_total', 0)}`",
        f"- runtime_missing_case_total: `{summary.get('runtime_missing_case_total', 0)}`",
        f"- widget_missing_case_total: `{summary.get('widget_missing_case_total', 0)}`",
        f"- api_missing_case_total: `{summary.get('api_missing_case_total', 0)}`",
        f"- release_guard_ready: `{summary.get('release_guard_ready', False)}`",
        f"- execution_lane_id: `{summary.get('execution_lane_id', '')}`",
        f"- parallel_lane_id: `{summary.get('parallel_lane_id', '')}`",
        "",
        "## Missing Samples",
        f"- runtime_families: `{', '.join(missing.get('runtime_families', []))}`",
        f"- widget_families: `{', '.join(missing.get('widget_families', []))}`",
        f"- api_families: `{', '.join(missing.get('api_families', []))}`",
        f"- runtime_cases: `{', '.join(missing.get('runtime_cases', []))}`",
        f"- widget_cases: `{', '.join(missing.get('widget_cases', []))}`",
        f"- api_cases: `{', '.join(missing.get('api_cases', []))}`",
        "",
        "## Extra Samples",
        f"- runtime_cases: `{', '.join(extras.get('runtime_cases', []))}`",
        f"- widget_cases: `{', '.join(extras.get('widget_cases', []))}`",
        f"- api_cases: `{', '.join(extras.get('api_cases', []))}`",
    ]
    failed = list(report.get("runtime_failed_case_ids") or [])
    if failed:
        lines.extend(["", "## Runtime Failed Cases"])
        for case_id in failed:
            lines.append(f"- `{case_id}`")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a release guard over runtime/widget/api family case parity.")
    parser.add_argument("--goldset", type=Path, default=DEFAULT_GOLDSET_INPUT)
    parser.add_argument("--runtime-assertions", type=Path, default=DEFAULT_RUNTIME_ASSERTIONS_INPUT)
    parser.add_argument("--widget", type=Path, default=DEFAULT_WIDGET_INPUT)
    parser.add_argument("--api-contract", type=Path, default=DEFAULT_API_CONTRACT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()

    report = build_release_guard(
        permit_family_case_goldset=_load_json(args.goldset.resolve()),
        permit_runtime_case_assertions=_load_json(args.runtime_assertions.resolve()),
        widget_rental_catalog=_load_json(args.widget.resolve()),
        api_contract_spec=_load_json(args.api_contract.resolve()),
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.md_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        json.dumps(
            {"ok": True, "json": str(args.json_output.resolve()), "md": str(args.md_output.resolve())},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if bool((report.get("summary") or {}).get("release_guard_ready")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
