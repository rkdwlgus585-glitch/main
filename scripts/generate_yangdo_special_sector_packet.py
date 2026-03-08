#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_PRECISION = LOG_DIR / "yangdo_recommendation_precision_matrix_latest.json"
DEFAULT_DIVERSITY = LOG_DIR / "yangdo_recommendation_diversity_audit_latest.json"
DEFAULT_CONTRACT = LOG_DIR / "yangdo_recommendation_contract_audit_latest.json"
DEFAULT_SETTLEMENT = LOG_DIR / "special_sector_settlement_matrix_latest.json"
DEFAULT_JSON = LOG_DIR / "yangdo_special_sector_packet_latest.json"
DEFAULT_MD = LOG_DIR / "yangdo_special_sector_packet_latest.md"

SECTOR_SPECS: Dict[str, Dict[str, Any]] = {
    "전기": {
        "aliases": ["전기"],
        "required_scenarios": {
            "포괄": "special_sector_comprehensive_uses_sales_and_scale_without_balance",
            "분할/합병": "special_sector_split_uses_sales_and_capital_without_balance",
        },
        "optional_scenarios": [],
    },
    "정보통신": {
        "aliases": ["정보통신", "통신"],
        "required_scenarios": {
            "포괄": "telecom_comprehensive_keeps_scale_focus_without_balance",
            "분할/합병": "telecom_split_moves_focus_to_sales_and_capital",
        },
        "optional_scenarios": [],
    },
    "소방": {
        "aliases": ["소방"],
        "required_scenarios": {
            "분할/합병": "fire_split_moves_focus_to_sales_and_capital",
        },
        "optional_scenarios": [
            {
                "reorg_mode": "포괄",
                "reason": "소방 포괄 lane은 현재 settlement 규칙은 존재하지만 추천 정밀도 시나리오는 아직 분할/합병 중심으로만 고정돼 있어 확장 backlog로 유지한다.",
            }
        ],
    },
}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _round4(value: Any) -> float:
    return round(_safe_float(value), 4)


def _scenario_index(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    rows = payload.get("scenarios") if isinstance(payload.get("scenarios"), list) else []
    return {
        str(row.get("scenario_id") or ""): row
        for row in rows
        if isinstance(row, dict) and str(row.get("scenario_id") or "").strip()
    }


def _merge_publication_counts(by_reorg: Dict[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for reorg_payload in by_reorg.values():
        if not isinstance(reorg_payload, dict):
            continue
        auto_payload = reorg_payload.get("auto") if isinstance(reorg_payload.get("auto"), dict) else {}
        publications = auto_payload.get("publication_counts") if isinstance(auto_payload.get("publication_counts"), dict) else {}
        for key, value in publications.items():
            label = str(key or "").strip()
            if not label:
                continue
            counts[label] = counts.get(label, 0) + _safe_int(value)
    return counts


def _merge_total_cases(by_reorg: Dict[str, Any]) -> int:
    total = 0
    for reorg_payload in by_reorg.values():
        if not isinstance(reorg_payload, dict):
            continue
        auto_payload = reorg_payload.get("auto") if isinstance(reorg_payload.get("auto"), dict) else {}
        total += _safe_int(auto_payload.get("count"))
    return total


def _publication_safety(publications: Dict[str, int]) -> Dict[str, Any]:
    total = sum(_safe_int(value) for value in publications.values())
    full_count = _safe_int(publications.get("full"))
    full_share = _round4(full_count / total) if total > 0 else 0.0
    consult_count = _safe_int(publications.get("consult_only"))
    range_count = _safe_int(publications.get("range_only"))
    safe = total > 0 and (full_count <= 2 or full_share <= 0.05) and (consult_count + range_count) >= max(1, total - full_count)
    return {
        "total_publication_cases": total,
        "full_count": full_count,
        "full_share": full_share,
        "consult_only_count": consult_count,
        "range_only_count": range_count,
        "publication_safety_ok": safe,
    }


def build_yangdo_special_sector_packet(
    *,
    precision_payload: Dict[str, Any],
    diversity_payload: Dict[str, Any],
    contract_payload: Dict[str, Any],
    settlement_payload: Dict[str, Any],
) -> Dict[str, Any]:
    precision_summary = precision_payload.get("summary") if isinstance(precision_payload.get("summary"), dict) else {}
    diversity_summary = diversity_payload.get("summary") if isinstance(diversity_payload.get("summary"), dict) else {}
    contract_summary = contract_payload.get("summary") if isinstance(contract_payload.get("summary"), dict) else {}
    settlement_by_sector = settlement_payload.get("by_sector") if isinstance(settlement_payload.get("by_sector"), dict) else {}
    scenario_map = _scenario_index(precision_payload)

    sectors: List[Dict[str, Any]] = []
    expansion_candidates: List[Dict[str, str]] = []
    ready_count = 0
    publication_safe_count = 0

    for sector_name, spec in SECTOR_SPECS.items():
        settlement_sector = settlement_by_sector.get(sector_name) if isinstance(settlement_by_sector.get(sector_name), dict) else {}
        publications = _merge_publication_counts(settlement_sector)
        publication_metrics = _publication_safety(publications)

        required_rows: List[Dict[str, Any]] = []
        required_ok = True
        for reorg_mode, scenario_id in (spec.get("required_scenarios") or {}).items():
            scenario_row = scenario_map.get(str(scenario_id)) if isinstance(scenario_map.get(str(scenario_id)), dict) else {}
            ok = bool(scenario_row.get("ok"))
            observed = scenario_row.get("observed") if isinstance(scenario_row.get("observed"), dict) else {}
            required_rows.append(
                {
                    "reorg_mode": reorg_mode,
                    "scenario_id": scenario_id,
                    "ok": ok,
                    "recommendation_focus": str(observed.get("recommendation_focus") or ""),
                    "precision_tier": str(observed.get("precision_tier") or ""),
                }
            )
            required_ok = required_ok and ok

        optional_rows: List[Dict[str, Any]] = []
        for row in spec.get("optional_scenarios") or []:
            optional_rows.append(
                {
                    "reorg_mode": str(row.get("reorg_mode") or ""),
                    "status": "backlog",
                    "reason": str(row.get("reason") or ""),
                }
            )
            expansion_candidates.append(
                {
                    "sector": sector_name,
                    "reorg_mode": str(row.get("reorg_mode") or ""),
                    "reason": str(row.get("reason") or ""),
                }
            )

        settlement_modes_present = sorted(
            [str(mode) for mode, payload in settlement_sector.items() if isinstance(payload, dict)]
        )
        sector_ready = bool(settlement_sector) and required_ok
        if sector_ready:
            ready_count += 1
        if publication_metrics["publication_safety_ok"]:
            publication_safe_count += 1

        sectors.append(
            {
                "sector": sector_name,
                "aliases": list(spec.get("aliases") or []),
                "settlement_modes_present": settlement_modes_present,
                "required_scenarios": required_rows,
                "optional_expansion": optional_rows,
                "settlement_case_total": _merge_total_cases(settlement_sector),
                "publication_metrics": publication_metrics,
                "sector_ready": sector_ready,
            }
        )

    summary = {
        "packet_ready": ready_count == len(SECTOR_SPECS)
        and publication_safe_count == len(SECTOR_SPECS)
        and bool(precision_summary.get("special_sector_comprehensive_ok"))
        and bool(precision_summary.get("special_sector_split_ok"))
        and bool(diversity_summary.get("diversity_ok"))
        and bool(contract_summary.get("contract_ok")),
        "special_sector_count": len(SECTOR_SPECS),
        "sector_ready_count": ready_count,
        "publication_safety_ok": publication_safe_count == len(SECTOR_SPECS),
        "pricing_watch_required": publication_safe_count != len(SECTOR_SPECS),
        "precision_green": bool(precision_summary.get("special_sector_comprehensive_ok")) and bool(precision_summary.get("special_sector_split_ok")),
        "diversity_green": bool(diversity_summary.get("diversity_ok")),
        "contract_green": bool(contract_summary.get("contract_ok")),
        "expansion_candidate_count": len(expansion_candidates),
        "expansion_candidates": list(expansion_candidates),
    }

    next_actions: List[str] = []
    if not summary["packet_ready"]:
        next_actions.append("특수 업종 packet이 아직 완전 녹색이 아니면 settlement·precision·contract 중 실패 축을 먼저 복구한다.")
    else:
        next_actions.append("전기·정보통신·소방 특수 업종 packet을 기준으로 산정 분리, 추천 정밀도, 공개 계약을 계속 감시한다.")
    if expansion_candidates:
        next_actions.append("소방 포괄 lane처럼 아직 backlog인 시나리오는 runtime blocker로 승격하지 말고 sector expansion backlog로만 관리한다.")

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "yangdo_special_sector_packet_latest",
        "data_sources": {
            "precision_matrix": str(DEFAULT_PRECISION),
            "diversity_audit": str(DEFAULT_DIVERSITY),
            "contract_audit": str(DEFAULT_CONTRACT),
            "settlement_matrix": str(DEFAULT_SETTLEMENT),
        },
        "summary": summary,
        "sectors": sectors,
        "next_actions": next_actions,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# Yangdo Special Sector Packet",
        "",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- special_sector_count: {summary.get('special_sector_count')}",
        f"- sector_ready_count: {summary.get('sector_ready_count')}",
        f"- publication_safety_ok: {summary.get('publication_safety_ok')}",
        f"- pricing_watch_required: {summary.get('pricing_watch_required')}",
        f"- precision_green: {summary.get('precision_green')}",
        f"- diversity_green: {summary.get('diversity_green')}",
        f"- contract_green: {summary.get('contract_green')}",
        f"- expansion_candidate_count: {summary.get('expansion_candidate_count')}",
        "",
        "## Sectors",
    ]
    for row in payload.get("sectors") or []:
        if not isinstance(row, dict):
            continue
        metrics = row.get("publication_metrics") if isinstance(row.get("publication_metrics"), dict) else {}
        lines.append(f"- {row.get('sector')}: ready={row.get('sector_ready')} settlement_modes={', '.join(row.get('settlement_modes_present') or []) or '(none)'}")
        lines.append(f"  - settlement_case_total: {row.get('settlement_case_total')}")
        lines.append(f"  - publication_safety_ok: {metrics.get('publication_safety_ok')}")
        lines.append(f"  - full_count: {metrics.get('full_count')} full_share: {metrics.get('full_share')}")
        for scenario in row.get("required_scenarios") or []:
            if not isinstance(scenario, dict):
                continue
            lines.append(
                f"  - required {scenario.get('reorg_mode')}: ok={scenario.get('ok')} scenario_id={scenario.get('scenario_id')} focus={scenario.get('recommendation_focus') or '(none)'} precision_tier={scenario.get('precision_tier') or '(none)'}"
            )
        for optional in row.get("optional_expansion") or []:
            if not isinstance(optional, dict):
                continue
            lines.append(f"  - optional {optional.get('reorg_mode')}: {optional.get('reason')}")
    if payload.get("next_actions"):
        lines.extend(["", "## Next Actions"])
        for action in payload.get("next_actions") or []:
            lines.append(f"- {action}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build canonical packet for 전기/정보통신/소방 special-sector yangdo precision.")
    parser.add_argument("--precision", type=Path, default=DEFAULT_PRECISION)
    parser.add_argument("--diversity", type=Path, default=DEFAULT_DIVERSITY)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--settlement", type=Path, default=DEFAULT_SETTLEMENT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_yangdo_special_sector_packet(
        precision_payload=_load_json(args.precision),
        diversity_payload=_load_json(args.diversity),
        contract_payload=_load_json(args.contract),
        settlement_payload=_load_json(args.settlement),
    )

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
