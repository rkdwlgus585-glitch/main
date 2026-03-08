#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_SECTOR_AUDIT = LOG_DIR / "yangdo_sector_price_audit_latest.json"
DEFAULT_JSON = LOG_DIR / "yangdo_exact_combo_recovery_audit_latest.json"
DEFAULT_MD = LOG_DIR / "yangdo_exact_combo_recovery_audit_latest.md"

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


def _priority_score(row: Dict[str, Any]) -> float:
    support = dict(row.get("comparable_support") or {})
    metrics = dict(row.get("price_metrics") or {})
    same_combo = _safe_float(support.get("avg_same_combo_ratio"))
    display = _safe_float(support.get("avg_display_neighbor_count"))
    clusters = _safe_float(support.get("avg_effective_cluster_count"))
    under = _safe_float(metrics.get("under_67_share"))
    visible = _safe_int(row.get("visible_estimate_count"))
    observed = _safe_int(row.get("observed_record_count"))
    status = str(row.get("status") or "")
    reject_keys = {str(item.get("key") or "") for item in support.get("top_reject_reasons") or [] if isinstance(item, dict)}
    score = 0.0
    score += max(0.0, 1.0 - same_combo) * 0.35
    score += max(0.0, 2.5 - display) / 2.5 * 0.20
    score += max(0.0, 2.5 - clusters) / 2.5 * 0.15
    score += under * 0.20
    score += min(1.0, observed / 20.0) * 0.10
    if visible == 0:
        score += 0.10
    if status in {"sparse_support_hotspot", "publication_locked"}:
        score += 0.10
    if same_combo >= 0.90 and display <= 1.0 and "strict_same_core_miss" in reject_keys:
        score += 0.15
    return _round4(score)


def _decision(row: Dict[str, Any]) -> str:
    support = dict(row.get("comparable_support") or {})
    metrics = dict(row.get("price_metrics") or {})
    same_combo = _safe_float(support.get("avg_same_combo_ratio"))
    display = _safe_float(support.get("avg_display_neighbor_count"))
    under = _safe_float(metrics.get("under_67_share"))
    observed = _safe_int(row.get("observed_record_count"))
    visible = _safe_int(row.get("visible_estimate_count"))
    reject_keys = {str(item.get("key") or "") for item in support.get("top_reject_reasons") or [] if isinstance(item, dict)}
    if observed < 3:
        return "data_intake_first"
    if same_combo < 0.70 and display <= 2.0:
        return "exact_combo_recovery_now"
    if same_combo >= 0.90 and display <= 1.0 and visible == 0 and (
        "strict_same_core_miss" in reject_keys or "single_core_profile_outlier" in reject_keys
    ):
        return "same_combo_locked_support"
    if same_combo < 0.85 and (display <= 3.0 or visible == 0):
        return "cohort_lock_then_retry"
    if under >= 0.45 and same_combo >= 0.85:
        return "pricing_not_cohort"
    return "monitor"


def _reject_excerpt(row: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    support = dict(row.get("comparable_support") or {})
    out: List[Dict[str, Any]] = []
    for item in support.get("top_reject_reasons") or []:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "key": str(item.get("key") or ""),
                "count": _safe_int(item.get("count")),
            }
        )
        if len(out) >= limit:
            break
    return out


def build_report(*, sector_audit: Dict[str, Any], focus: List[str]) -> Dict[str, Any]:
    sectors = [row for row in sector_audit.get("sectors") or [] if isinstance(row, dict)]
    selected: List[Dict[str, Any]] = []
    for row in sectors:
        sector_name = str(row.get("sector") or "")
        if sector_name not in focus:
            continue
        support = dict(row.get("comparable_support") or {})
        metrics = dict(row.get("price_metrics") or {})
        selected.append(
            {
                "sector": sector_name,
                "status": str(row.get("status") or ""),
                "observed_record_count": _safe_int(row.get("observed_record_count")),
                "visible_estimate_count": _safe_int(row.get("visible_estimate_count")),
                "avg_same_combo_ratio": _round4(support.get("avg_same_combo_ratio")),
                "avg_same_core_ratio": _round4(support.get("avg_same_core_ratio")),
                "avg_display_neighbor_count": _round4(support.get("avg_display_neighbor_count")),
                "avg_effective_cluster_count": _round4(support.get("avg_effective_cluster_count")),
                "under_67_share": _round4(metrics.get("under_67_share")),
                "over_150_share": _round4(metrics.get("over_150_share")),
                "decision": _decision(row),
                "priority_score": _priority_score(row),
                "top_reject_reasons": _reject_excerpt(row),
                "recommended_action": str(row.get("recommended_action") or ""),
            }
        )
    selected.sort(key=lambda row: (-_safe_float(row.get("priority_score")), str(row.get("sector") or "")))

    decision_counts: Dict[str, int] = {}
    for row in selected:
        decision = str(row.get("decision") or "")
        decision_counts[decision] = decision_counts.get(decision, 0) + 1

    return {
        "generated_at": _now_str(),
        "packet_id": "yangdo_exact_combo_recovery_audit_latest",
        "summary": {
            "focus_sector_count": len(focus),
            "evaluated_sector_count": len(selected),
            "decision_counts": decision_counts,
            "top_candidates": [str(row.get("sector") or "") for row in selected[:5]],
        },
        "focus_sectors": focus,
        "sector_candidates": selected,
        "next_actions": [
            "exact_combo_recovery_now 섹터는 partial overlap을 후보 풀에서 분리하는 감사/실험을 먼저 추가한다.",
            "same_combo_locked_support 섹터는 strict_same_core_miss와 profile outlier를 분리해 same-combo support를 다시 살린다.",
            "cohort_lock_then_retry 섹터는 same-combo 우선 cohort를 회복한 뒤 price prior를 다시 검증한다.",
            "pricing_not_cohort 섹터는 cohort가 아니라 none-mode 또는 price prior 보정 대상으로 본다.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Yangdo Exact Combo Recovery Audit",
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
            "- {sector}: decision={decision}, score={score}, same_combo={same_combo}, display={display}, under_67={under_67}, visible={visible}".format(
                sector=row.get("sector"),
                decision=row.get("decision"),
                score=row.get("priority_score"),
                same_combo=row.get("avg_same_combo_ratio"),
                display=row.get("avg_display_neighbor_count"),
                under_67=row.get("under_67_share"),
                visible=row.get("visible_estimate_count"),
            )
        )
    lines.extend(["", "## Next Actions"])
    for item in payload.get("next_actions") or []:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate exact-combo recovery audit for yangdo pricing sectors.")
    parser.add_argument("--sector-audit", type=Path, default=DEFAULT_SECTOR_AUDIT)
    parser.add_argument("--focus", nargs="*", default=DEFAULT_FOCUS)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_report(sector_audit=_load_json(args.sector_audit), focus=[str(item) for item in args.focus])
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
