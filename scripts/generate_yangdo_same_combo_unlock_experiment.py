#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_BALANCE_CV = LOG_DIR / "yangdo_balance_base_cv_latest.json"
DEFAULT_COHORT_RECOVERY = LOG_DIR / "yangdo_cohort_recovery_experiment_latest.json"
DEFAULT_SECTOR_AUDIT = LOG_DIR / "yangdo_sector_price_audit_latest.json"
DEFAULT_JSON = LOG_DIR / "yangdo_same_combo_unlock_experiment_latest.json"
DEFAULT_MD = LOG_DIR / "yangdo_same_combo_unlock_experiment_latest.md"

for candidate in (ROOT, Path(__file__).resolve().parent):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import yangdo_blackbox_api


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


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(statistics.median(values))


def _quantile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    seq = sorted(float(value) for value in values)
    if len(seq) == 1:
        return seq[0]
    idx = (len(seq) - 1) * q
    lo = int(idx)
    hi = min(len(seq) - 1, lo + 1)
    frac = idx - lo
    return seq[lo] * (1.0 - frac) + seq[hi] * frac


def _token_set(record: Dict[str, Any]) -> Set[str]:
    return {str(token or "").strip() for token in list(record.get("license_tokens") or []) if str(token or "").strip()}


def _signal_value(record: Dict[str, Any]) -> Optional[float]:
    sales3 = _safe_float(record.get("sales3_eok"))
    specialty = _safe_float(record.get("specialty"))
    if sales3 > 0 and specialty > 0:
        return (0.65 * sales3) + (0.35 * specialty)
    if sales3 > 0:
        return sales3
    if specialty > 0:
        return specialty
    return None


def _target_sectors(cohort_recovery: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for row in cohort_recovery.get("sector_candidates") or []:
        if str(row.get("decision") or "") == "unlock_same_combo_support_now":
            sector = str(row.get("sector") or "").strip()
            if sector:
                out.append(sector)
    return out


def _find_sector_row(rows: Iterable[Dict[str, Any]], sector: str) -> Dict[str, Any]:
    for row in rows:
        if str(row.get("sector") or "") == sector:
            return row
    return {}


def _alias_set(sector_row: Dict[str, Any], sector: str) -> Set[str]:
    aliases = {sector}
    for item in sector_row.get("aliases") or []:
        text = str(item or "").strip()
        if text:
            aliases.add(text)
    return aliases


def _collect_exact_single(records: Iterable[Dict[str, Any]], aliases: Set[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for record in records:
        tokens = _token_set(record)
        if len(tokens) == 1 and tokens <= aliases and _safe_float(record.get("current_price_eok")) > 0:
            out.append(record)
    return out


def _peer_models(target: Dict[str, Any], peers: List[Dict[str, Any]]) -> Dict[str, float]:
    prices = [_safe_float(peer.get("current_price_eok")) for peer in peers if _safe_float(peer.get("current_price_eok")) > 0]
    median_price = _median(prices)
    q25 = _quantile(prices, 0.25)
    q75 = _quantile(prices, 0.75)
    target_signal = _signal_value(target)
    ratio_samples: List[float] = []
    if target_signal and target_signal > 0:
        for peer in peers:
            peer_signal = _signal_value(peer)
            peer_price = _safe_float(peer.get("current_price_eok"))
            if peer_signal and peer_signal > 0 and peer_price > 0:
                ratio_samples.append(peer_price / peer_signal)
    bounded = median_price
    if ratio_samples and target_signal and target_signal > 0:
        bounded = target_signal * _median(ratio_samples)
        if q25 > 0 or q75 > 0:
            bounded = max(q25 if q25 > 0 else bounded, min(bounded, q75 if q75 > 0 else bounded))
    return {
        "exact_median_pred_eok": median_price,
        "exact_bounded_pred_eok": bounded,
    }


def _metrics(rows: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    abs_pcts: List[float] = []
    signed_pcts: List[float] = []
    under_67 = 0
    over_150 = 0
    for row in rows:
        actual = _safe_float(row.get("actual_price_eok"))
        pred = _safe_float(row.get(key))
        if actual <= 0 or pred <= 0:
            continue
        ratio = pred / actual
        abs_pcts.append(abs(ratio - 1.0) * 100.0)
        signed_pcts.append((ratio - 1.0) * 100.0)
        under_67 += int(ratio < 0.67)
        over_150 += int(ratio > 1.5)
    count = len(abs_pcts)
    return {
        "count": count,
        "median_abs_pct": _round4(_median(abs_pcts)),
        "median_signed_pct": _round4(_median(signed_pcts)),
        "pred_lt_actual_0_67x": under_67,
        "pred_gt_actual_1_5x": over_150,
        "under_67_share": _round4(under_67 / count) if count else 0.0,
        "over_150_share": _round4(over_150 / count) if count else 0.0,
    }


def _decision(*, exact_count: int, baseline: Dict[str, Any], median_metrics: Dict[str, Any], bounded_metrics: Dict[str, Any]) -> str:
    if exact_count == 0:
        return "alias_or_catalog_first"
    if exact_count < 8:
        return "micro_pool_guard_only"
    baseline_under = _safe_float(baseline.get("under_67_share"))
    baseline_over = _safe_int(baseline.get("pred_gt_actual_1_5x"))
    median_under = _safe_float(median_metrics.get("under_67_share"))
    median_over = _safe_int(median_metrics.get("pred_gt_actual_1_5x"))
    bounded_under = _safe_float(bounded_metrics.get("under_67_share"))
    bounded_over = _safe_int(bounded_metrics.get("pred_gt_actual_1_5x"))
    if median_under < baseline_under and median_over <= baseline_over:
        return "exact_median_unlock_candidate"
    if bounded_under < baseline_under and bounded_over <= baseline_over + 1:
        return "bounded_unlock_guarded"
    return "analysis_only"


def build_report(*, balance_cv: Dict[str, Any], cohort_recovery: Dict[str, Any], sector_audit: Dict[str, Any]) -> Dict[str, Any]:
    estimator = yangdo_blackbox_api.YangdoBlackboxEstimator()
    estimator.refresh()
    records, _token_index, _meta = estimator._snapshot()
    record_map = {(str(record.get("uid") or ""), int(record.get("number") or 0)): record for record in records}
    sector_rows = [row for row in sector_audit.get("sectors") or [] if isinstance(row, dict)]

    out_rows: List[Dict[str, Any]] = []
    for sector in _target_sectors(cohort_recovery):
        sector_row = _find_sector_row(sector_rows, sector)
        aliases = _alias_set(sector_row, sector)
        exact_records = _collect_exact_single(records, aliases)
        exact_keys = {(str(record.get("uid") or ""), int(record.get("number") or 0)) for record in exact_records}
        sim_rows: List[Dict[str, Any]] = []
        for row in balance_cv.get("record_rows") or []:
            key = (str(row.get("uid") or ""), int(row.get("number") or 0))
            if key not in exact_keys:
                continue
            target = record_map.get(key)
            if not target:
                continue
            peers = [record for record in exact_records if (str(record.get("uid") or ""), int(record.get("number") or 0)) != key]
            if not peers:
                continue
            models = _peer_models(target, peers)
            sim_rows.append(
                {
                    "uid": key[0],
                    "number": key[1],
                    "actual_price_eok": _round4(row.get("actual_price_eok")),
                    "engine_internal_pred_eok": _round4(row.get("engine_internal_pred_eok")),
                    "exact_median_pred_eok": _round4(models.get("exact_median_pred_eok")),
                    "exact_bounded_pred_eok": _round4(models.get("exact_bounded_pred_eok")),
                }
            )
        baseline = _metrics(sim_rows, "engine_internal_pred_eok")
        median_metrics = _metrics(sim_rows, "exact_median_pred_eok")
        bounded_metrics = _metrics(sim_rows, "exact_bounded_pred_eok")
        decision = _decision(
            exact_count=len(exact_records),
            baseline=baseline,
            median_metrics=median_metrics,
            bounded_metrics=bounded_metrics,
        )
        out_rows.append(
            {
                "sector": sector,
                "aliases": sorted(aliases),
                "exact_single_count": len(exact_records),
                "simulated_record_count": len(sim_rows),
                "baseline_engine_internal": baseline,
                "exact_median": median_metrics,
                "exact_bounded": bounded_metrics,
                "decision": decision,
                "sample_rows": sim_rows[:8],
            }
        )

    return {
        "generated_at": _now_str(),
        "packet_id": "yangdo_same_combo_unlock_experiment_latest",
        "summary": {
            "target_sector_count": len(out_rows),
            "sectors": [str(row.get("sector") or "") for row in out_rows],
            "decisions": {str(row.get("sector") or ""): str(row.get("decision") or "") for row in out_rows},
        },
        "sector_results": out_rows,
        "next_actions": [
            "exact_median_unlock_candidate는 strict_same_core relaxation 후 median-only cohort를 우선 검토한다.",
            "bounded_unlock_guarded는 publication lock을 유지한 채 guarded patch 후보로만 취급한다.",
            "micro_pool_guard_only와 alias_or_catalog_first는 엔진 패치보다 데이터/매핑 정리를 먼저 한다.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Yangdo Same Combo Unlock Experiment",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- target_sector_count: {summary.get('target_sector_count')}",
        "",
        "## Sector Results",
    ]
    for row in payload.get("sector_results") or []:
        baseline = row.get("baseline_engine_internal") or {}
        median_metrics = row.get("exact_median") or {}
        bounded = row.get("exact_bounded") or {}
        lines.append(
            "- {sector}: decision={decision}, exact_count={exact_count}, baseline_under={b_under}, median_under={m_under}, bounded_under={bd_under}, baseline_over={b_over}, median_over={m_over}, bounded_over={bd_over}".format(
                sector=row.get("sector"),
                decision=row.get("decision"),
                exact_count=row.get("exact_single_count"),
                b_under=baseline.get("under_67_share"),
                m_under=median_metrics.get("under_67_share"),
                bd_under=bounded.get("under_67_share"),
                b_over=baseline.get("pred_gt_actual_1_5x"),
                m_over=median_metrics.get("pred_gt_actual_1_5x"),
                bd_over=bounded.get("pred_gt_actual_1_5x"),
            )
        )
    lines.extend(["", "## Next Actions"])
    for item in payload.get("next_actions") or []:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate same-combo unlock experiment for locked support sectors.")
    parser.add_argument("--balance-cv", type=Path, default=DEFAULT_BALANCE_CV)
    parser.add_argument("--cohort-recovery", type=Path, default=DEFAULT_COHORT_RECOVERY)
    parser.add_argument("--sector-audit", type=Path, default=DEFAULT_SECTOR_AUDIT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_report(
        balance_cv=_load_json(args.balance_cv),
        cohort_recovery=_load_json(args.cohort_recovery),
        sector_audit=_load_json(args.sector_audit),
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
