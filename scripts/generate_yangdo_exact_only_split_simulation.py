#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_BALANCE_CV = LOG_DIR / "yangdo_balance_base_cv_latest.json"
DEFAULT_SPLIT_EXPERIMENT = LOG_DIR / "yangdo_exact_pool_split_experiment_latest.json"
DEFAULT_JSON = LOG_DIR / "yangdo_exact_only_split_simulation_latest.json"
DEFAULT_MD = LOG_DIR / "yangdo_exact_only_split_simulation_latest.md"

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


def _find_target_sectors(split_experiment: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for row in split_experiment.get("sector_candidates") or []:
        if str(row.get("decision") or "") == "run_split_simulation_now":
            sector = str(row.get("sector") or "").strip()
            if sector:
                out.append(sector)
    return out


def _collect_exact_records(records: Iterable[Dict[str, Any]], sector: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for record in records:
        tokens = _token_set(record)
        if tokens == {sector} and _safe_float(record.get("current_price_eok")) > 0:
            out.append(record)
    return out


def _peer_models(target: Dict[str, Any], peers: List[Dict[str, Any]]) -> Dict[str, float]:
    prices = [_safe_float(peer.get("current_price_eok")) for peer in peers if _safe_float(peer.get("current_price_eok")) > 0]
    q25 = _quantile(prices, 0.25)
    q75 = _quantile(prices, 0.75)
    median_price = _median(prices)
    signal = _signal_value(target)
    ratio_samples: List[float] = []
    if signal and signal > 0:
        for peer in peers:
            peer_signal = _signal_value(peer)
            peer_price = _safe_float(peer.get("current_price_eok"))
            if peer_signal and peer_signal > 0 and peer_price > 0:
                ratio_samples.append(peer_price / peer_signal)
    signal_est = 0.0
    if ratio_samples and signal and signal > 0:
        signal_est = signal * _median(ratio_samples)
    bounded_signal = signal_est if signal_est > 0 else median_price
    if q25 > 0 or q75 > 0:
        bounded_signal = max(q25 if q25 > 0 else bounded_signal, min(bounded_signal, q75 if q75 > 0 else bounded_signal))
    return {
        "exact_median_pred_eok": median_price,
        "exact_signal_bounded_pred_eok": bounded_signal,
        "q25_eok": q25,
        "q75_eok": q75,
    }


def _metrics(rows: List[Dict[str, Any]], key: str) -> Dict[str, Any]:
    abs_pcts: List[float] = []
    signed_pcts: List[float] = []
    under_67 = 0
    over_150 = 0
    for row in rows:
        actual = _safe_float(row.get("actual_price_eok"))
        predicted = _safe_float(row.get(key))
        if actual <= 0 or predicted <= 0:
            continue
        ratio = predicted / actual
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


def _decision(baseline: Dict[str, Any], bounded: Dict[str, Any], exact_count: int) -> str:
    if exact_count < 12:
        return "hold_insufficient_exact_pool"
    baseline_under = _safe_float(baseline.get("under_67_share"))
    bounded_under = _safe_float(bounded.get("under_67_share"))
    baseline_over = _safe_int(baseline.get("pred_gt_actual_1_5x"))
    bounded_over = _safe_int(bounded.get("pred_gt_actual_1_5x"))
    if bounded_under < baseline_under and bounded_over <= baseline_over:
        return "candidate_for_engine_patch"
    if bounded_under < baseline_under and bounded_over == baseline_over + 1:
        return "candidate_for_guarded_patch"
    return "analysis_only"


def build_report(*, balance_cv: Dict[str, Any], split_experiment: Dict[str, Any]) -> Dict[str, Any]:
    estimator = yangdo_blackbox_api.YangdoBlackboxEstimator()
    estimator.refresh()
    records, _token_index, _meta = estimator._snapshot()
    record_map = {(str(record.get("uid") or ""), int(record.get("number") or 0)): record for record in records}

    target_sectors = _find_target_sectors(split_experiment)
    sector_rows: List[Dict[str, Any]] = []
    for sector in target_sectors:
        exact_records = _collect_exact_records(records, sector)
        exact_lookup = {(str(record.get("uid") or ""), int(record.get("number") or 0)) for record in exact_records}
        sim_rows: List[Dict[str, Any]] = []
        for row in balance_cv.get("record_rows") or []:
            key = (str(row.get("uid") or ""), int(row.get("number") or 0))
            if key not in exact_lookup:
                continue
            target = record_map.get(key)
            if not target:
                continue
            peers = [record for record in exact_records if (str(record.get("uid") or ""), int(record.get("number") or 0)) != key]
            if len(peers) < 8:
                continue
            models = _peer_models(target, peers)
            sim_rows.append(
                {
                    "uid": key[0],
                    "number": key[1],
                    "actual_price_eok": _round4(row.get("actual_price_eok")),
                    "engine_internal_pred_eok": _round4(row.get("engine_internal_pred_eok")),
                    "exact_median_pred_eok": _round4(models.get("exact_median_pred_eok")),
                    "exact_signal_bounded_pred_eok": _round4(models.get("exact_signal_bounded_pred_eok")),
                    "peer_q25_eok": _round4(models.get("q25_eok")),
                    "peer_q75_eok": _round4(models.get("q75_eok")),
                }
            )

        baseline_metrics = _metrics(sim_rows, "engine_internal_pred_eok")
        exact_median_metrics = _metrics(sim_rows, "exact_median_pred_eok")
        bounded_metrics = _metrics(sim_rows, "exact_signal_bounded_pred_eok")
        decision = _decision(baseline_metrics, bounded_metrics, len(sim_rows))
        sector_rows.append(
            {
                "sector": sector,
                "exact_record_count": len(exact_records),
                "simulated_record_count": len(sim_rows),
                "baseline_engine_internal": baseline_metrics,
                "exact_only_median": exact_median_metrics,
                "exact_only_signal_bounded": bounded_metrics,
                "decision": decision,
                "sample_rows": sim_rows[:8],
            }
        )

    return {
        "generated_at": _now_str(),
        "packet_id": "yangdo_exact_only_split_simulation_latest",
        "summary": {
            "target_sector_count": len(target_sectors),
            "evaluated_sector_count": len(sector_rows),
            "sectors": [str(row.get("sector") or "") for row in sector_rows],
            "decisions": {str(row.get("sector") or ""): str(row.get("decision") or "") for row in sector_rows},
        },
        "sector_results": sector_rows,
        "next_actions": [
            "candidate_for_engine_patch는 exact-only bounded prior를 엔진 후보식으로 올린다.",
            "candidate_for_guarded_patch는 publication lock과 함께 guarded patch로만 검토한다.",
            "analysis_only는 split 효과보다 과대평가 리스크가 커서 엔진 반영을 보류한다.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Yangdo Exact Only Split Simulation",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- target_sector_count: {summary.get('target_sector_count')}",
        f"- evaluated_sector_count: {summary.get('evaluated_sector_count')}",
        "",
        "## Sector Results",
    ]
    for row in payload.get("sector_results") or []:
        baseline = row.get("baseline_engine_internal") or {}
        bounded = row.get("exact_only_signal_bounded") or {}
        lines.append(
            "- {sector}: decision={decision}, simulated={count}, baseline_under={b_under}, bounded_under={s_under}, baseline_over={b_over}, bounded_over={s_over}".format(
                sector=row.get("sector"),
                decision=row.get("decision"),
                count=row.get("simulated_record_count"),
                b_under=baseline.get("under_67_share"),
                s_under=bounded.get("under_67_share"),
                b_over=baseline.get("pred_gt_actual_1_5x"),
                s_over=bounded.get("pred_gt_actual_1_5x"),
            )
        )
    lines.extend(["", "## Next Actions"])
    for item in payload.get("next_actions") or []:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate exact-only split simulation for sectors selected by split experiment.")
    parser.add_argument("--balance-cv", type=Path, default=DEFAULT_BALANCE_CV)
    parser.add_argument("--split-experiment", type=Path, default=DEFAULT_SPLIT_EXPERIMENT)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_report(
        balance_cv=_load_json(args.balance_cv),
        split_experiment=_load_json(args.split_experiment),
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
