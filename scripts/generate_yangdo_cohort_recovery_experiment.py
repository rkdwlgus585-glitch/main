#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_SECTOR_AUDIT = LOG_DIR / "yangdo_sector_price_audit_latest.json"
DEFAULT_COMPARABLE_AUDIT = LOG_DIR / "yangdo_comparable_selection_audit_latest.json"
DEFAULT_JSON = LOG_DIR / "yangdo_cohort_recovery_experiment_latest.json"
DEFAULT_MD = LOG_DIR / "yangdo_cohort_recovery_experiment_latest.md"

DEFAULT_FOCUS = ["토목", "포장", "상하수도", "조경", "토건", "석공", "석면", "시설물"]


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


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


def _round4(value: Any) -> float:
    return round(_safe_float(value), 4)


def _top_dict_rows(value: Any, limit: int = 5) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not isinstance(value, list):
        return rows
    for item in value:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "key": str(item.get("key") or ""),
                "count": _safe_int(item.get("count")),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _find_sector_row(rows: Iterable[Dict[str, Any]], sector: str) -> Dict[str, Any]:
    for row in rows:
        if str(row.get("sector") or "") == sector:
            return row
    return {}


def _find_combo_row(rows: Iterable[Dict[str, Any]], sector: str) -> Dict[str, Any]:
    for row in rows:
        combo = list(row.get("combo") or [])
        combo_label = str(row.get("combo_label") or "")
        if sector in combo or sector in combo_label:
            return row
    return {}


def _decision(sector_row: Dict[str, Any], comparable_row: Dict[str, Any]) -> str:
    support = dict(sector_row.get("comparable_support") or {})
    same_combo = _safe_float(support.get("avg_same_combo_ratio"))
    display = _safe_float(support.get("avg_display_neighbor_count"))
    visible = _safe_int(sector_row.get("visible_estimate_count"))
    reject_keys = {str(item.get("key") or "") for item in support.get("top_reject_reasons") or [] if isinstance(item, dict)}
    top_neighbor_keys = {str(item.get("key") or "") for item in comparable_row.get("top_neighbor_combos") or [] if isinstance(item, dict)}
    if same_combo < 0.70 and display <= 2.0:
        return "split_exact_vs_partial_now"
    if same_combo >= 0.90 and display <= 1.0 and visible == 0 and (
        "strict_same_core_miss" in reject_keys or "single_core_profile_outlier" in reject_keys
    ):
        return "unlock_same_combo_support_now"
    if same_combo < 0.90 and top_neighbor_keys:
        return "inspect_neighbor_mix"
    return "monitor"


def _falsification_test(decision: str, sector_row: Dict[str, Any]) -> str:
    observed = _safe_int(sector_row.get("observed_record_count"))
    if decision == "split_exact_vs_partial_now":
        return f"exact-pool 분리 후 effective cluster가 2 미만이면 split만으로는 해결되지 않는 것으로 본다. 현재 observed={observed}."
    if decision == "unlock_same_combo_support_now":
        return "same-combo 잠금 해제 후 over-1.5x가 늘거나 display가 그대로 1이면 relaxation을 폐기한다."
    if decision == "inspect_neighbor_mix":
        return "top neighbor combo가 sector core와 다른 조합으로 유지되면 exact recovery보다 매핑/분류 문제로 본다."
    return "추가 실험 없이 drift만 감시한다."


def _proposed_experiment(decision: str) -> str:
    mapping = {
        "split_exact_vs_partial_now": "exact combo pool과 partial overlap pool을 분리하고, exact pool이 2 cluster 미만이면 partial을 publication 참고치로만 남긴다.",
        "unlock_same_combo_support_now": "same-combo 안에서 strict_same_core_miss와 profile outlier를 분리 측정하고, display 1 잠금을 푸는 최소 relaxation 실험을 만든다.",
        "inspect_neighbor_mix": "top neighbor combo를 sector별로 샘플링해 alias/매핑 오류인지 실제 cross-sell cohort인지 확인한다.",
        "monitor": "실험 추가 없이 sector drift만 감시한다.",
    }
    return mapping.get(decision, "monitor")


def _priority_score(sector_row: Dict[str, Any], decision: str) -> float:
    support = dict(sector_row.get("comparable_support") or {})
    metrics = dict(sector_row.get("price_metrics") or {})
    score = 0.0
    score += max(0.0, 1.0 - _safe_float(support.get("avg_same_combo_ratio"))) * 0.35
    score += max(0.0, 2.0 - _safe_float(support.get("avg_display_neighbor_count"))) / 2.0 * 0.20
    score += max(0.0, 2.0 - _safe_float(support.get("avg_effective_cluster_count"))) / 2.0 * 0.15
    score += _safe_float(metrics.get("under_67_share")) * 0.15
    score += min(1.0, _safe_int(sector_row.get("observed_record_count")) / 30.0) * 0.10
    if decision == "split_exact_vs_partial_now":
        score += 0.15
    if decision == "unlock_same_combo_support_now":
        score += 0.10
    return _round4(score)


def build_report(*, sector_audit: Dict[str, Any], comparable_audit: Dict[str, Any], focus: List[str]) -> Dict[str, Any]:
    sector_rows = [row for row in sector_audit.get("sectors") or [] if isinstance(row, dict)]
    combo_rows = [row for row in comparable_audit.get("combo_summaries") or [] if isinstance(row, dict)]

    candidates: List[Dict[str, Any]] = []
    for sector in focus:
        sector_row = _find_sector_row(sector_rows, sector)
        if not sector_row:
            continue
        comparable_row = _find_combo_row(combo_rows, sector)
        decision = _decision(sector_row, comparable_row)
        support = dict(sector_row.get("comparable_support") or {})
        metrics = dict(sector_row.get("price_metrics") or {})
        candidates.append(
            {
                "sector": sector,
                "decision": decision,
                "priority_score": _priority_score(sector_row, decision),
                "status": str(sector_row.get("status") or ""),
                "observed_record_count": _safe_int(sector_row.get("observed_record_count")),
                "visible_estimate_count": _safe_int(sector_row.get("visible_estimate_count")),
                "under_67_share": _round4(metrics.get("under_67_share")),
                "over_150_share": _round4(metrics.get("over_150_share")),
                "avg_same_combo_ratio": _round4(support.get("avg_same_combo_ratio")),
                "avg_display_neighbor_count": _round4(support.get("avg_display_neighbor_count")),
                "avg_effective_cluster_count": _round4(support.get("avg_effective_cluster_count")),
                "top_reject_reasons": _top_dict_rows(support.get("top_reject_reasons"), 3),
                "top_neighbor_combos": _top_dict_rows(comparable_row.get("top_neighbor_combos"), 4),
                "proposed_experiment": _proposed_experiment(decision),
                "falsification_test": _falsification_test(decision, sector_row),
            }
        )

    candidates.sort(key=lambda row: (-_safe_float(row.get("priority_score")), str(row.get("sector") or "")))
    decision_counts: Dict[str, int] = {}
    for row in candidates:
        key = str(row.get("decision") or "")
        decision_counts[key] = decision_counts.get(key, 0) + 1

    return {
        "generated_at": _now_str(),
        "packet_id": "yangdo_cohort_recovery_experiment_latest",
        "summary": {
            "focus_sector_count": len(focus),
            "evaluated_sector_count": len(candidates),
            "decision_counts": decision_counts,
            "top_candidates": [str(row.get("sector") or "") for row in candidates[:5]],
        },
        "focus_sectors": focus,
        "sector_candidates": candidates,
        "next_actions": [
            "split_exact_vs_partial_now 섹터는 exact-pool과 partial-pool을 실제로 분리하는 러너를 추가한다.",
            "unlock_same_combo_support_now 섹터는 strict_same_core_miss/profile outlier 분해 실험을 추가한다.",
            "inspect_neighbor_mix 섹터는 alias/매핑 drift 여부를 먼저 확인한다.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Yangdo Cohort Recovery Experiment",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- focus_sector_count: {summary.get('focus_sector_count')}",
        f"- evaluated_sector_count: {summary.get('evaluated_sector_count')}",
        "",
        "## Decision Counts",
    ]
    for key, value in (summary.get("decision_counts") or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Top Candidates"])
    for item in summary.get("top_candidates") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Sector Candidates"])
    for row in payload.get("sector_candidates") or []:
        lines.append(
            "- {sector}: decision={decision}, score={score}, same_combo={same_combo}, display={display}, clusters={clusters}, under_67={under_67}".format(
                sector=row.get("sector"),
                decision=row.get("decision"),
                score=row.get("priority_score"),
                same_combo=row.get("avg_same_combo_ratio"),
                display=row.get("avg_display_neighbor_count"),
                clusters=row.get("avg_effective_cluster_count"),
                under_67=row.get("under_67_share"),
            )
        )
    lines.extend(["", "## Next Actions"])
    for item in payload.get("next_actions") or []:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a cohort recovery experiment plan for yangdo pricing sectors.")
    parser.add_argument("--sector-audit", type=Path, default=DEFAULT_SECTOR_AUDIT)
    parser.add_argument("--comparable-audit", type=Path, default=DEFAULT_COMPARABLE_AUDIT)
    parser.add_argument("--focus", nargs="*", default=DEFAULT_FOCUS)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_report(
        sector_audit=_load_json(args.sector_audit),
        comparable_audit=_load_json(args.comparable_audit),
        focus=[str(item) for item in args.focus],
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
