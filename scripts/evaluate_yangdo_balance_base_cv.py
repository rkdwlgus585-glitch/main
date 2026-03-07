from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
for candidate in (ROOT, SCRIPTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import yangdo_blackbox_api
from audit_yangdo_comparable_selection import _group_key, _combo_label, _payload_from_record, _round4


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _to_float(value: Any) -> Optional[float]:
    return yangdo_blackbox_api._to_float(value)


def _safe_actual_price(rec: Dict[str, Any]) -> Optional[float]:
    price = _to_float(rec.get("current_price_eok"))
    if price is None or price <= 0:
        return None
    return float(price)


def _prime_estimator(
    estimator: yangdo_blackbox_api.YangdoBlackboxEstimator,
    train_records: List[Dict[str, Any]],
    meta: Dict[str, Any],
) -> None:
    estimator._records = list(train_records)
    estimator._train_records = list(train_records)
    estimator._token_index = yangdo_blackbox_api.core._build_neighbor_index(train_records)
    estimator._meta = dict(meta)


def _record_key(rec: Dict[str, Any]) -> Tuple[str, int]:
    return (str(rec.get("uid") or "").strip(), int(rec.get("row") or 0))


def _build_filtered_records(records: List[Dict[str, Any]], exclude: Dict[str, Any]) -> List[Dict[str, Any]]:
    marker = _record_key(exclude)
    return [row for row in records if _record_key(row) != marker]


def _metric_bucket(pairs: Iterable[Tuple[float, float]]) -> Dict[str, Any]:
    rows = [(float(actual), float(pred)) for actual, pred in list(pairs or []) if actual > 0 and pred > 0]
    if not rows:
        return {
            "count": 0,
            "mae_eok": None,
            "median_abs_pct": None,
            "mean_abs_pct": None,
            "median_signed_pct": None,
            "mean_signed_pct": None,
            "within_10pct": 0,
            "within_20pct": 0,
            "within_30pct": 0,
            "within_50pct": 0,
            "over_150pct": 0,
            "under_67pct": 0,
            "pred_gt_actual_1_5x": 0,
            "pred_gt_actual_2_5x": 0,
            "pred_lt_actual_0_67x": 0,
            "pred_lt_actual_0_33x": 0,
        }
    abs_errors = [abs(pred - actual) for actual, pred in rows]
    abs_pcts = [abs(pred - actual) / max(actual, 0.1) for actual, pred in rows]
    signed_pcts = [(pred - actual) / max(actual, 0.1) for actual, pred in rows]
    pred_gt_actual_1_5x = sum(1 for actual, pred in rows if pred > actual * 1.50)
    pred_gt_actual_2_5x = sum(1 for actual, pred in rows if pred > actual * 2.50)
    pred_lt_actual_0_67x = sum(1 for actual, pred in rows if pred < actual * 0.67)
    pred_lt_actual_0_33x = sum(1 for actual, pred in rows if pred < actual * 0.33)
    return {
        "count": len(rows),
        "mae_eok": _round4(sum(abs_errors) / len(abs_errors)),
        "median_abs_pct": _round4(statistics.median(abs_pcts) * 100.0),
        "mean_abs_pct": _round4((sum(abs_pcts) / len(abs_pcts)) * 100.0),
        "median_signed_pct": _round4(statistics.median(signed_pcts) * 100.0),
        "mean_signed_pct": _round4((sum(signed_pcts) / len(signed_pcts)) * 100.0),
        "within_10pct": sum(1 for x in abs_pcts if x <= 0.10),
        "within_20pct": sum(1 for x in abs_pcts if x <= 0.20),
        "within_30pct": sum(1 for x in abs_pcts if x <= 0.30),
        "within_50pct": sum(1 for x in abs_pcts if x <= 0.50),
        "over_150pct": pred_gt_actual_1_5x,
        "under_67pct": pred_lt_actual_0_67x,
        "pred_gt_actual_1_5x": pred_gt_actual_1_5x,
        "pred_gt_actual_2_5x": pred_gt_actual_2_5x,
        "pred_lt_actual_0_67x": pred_lt_actual_0_67x,
        "pred_lt_actual_0_33x": pred_lt_actual_0_33x,
    }


def _build_summary(rows: List[Dict[str, Any]], field: str) -> Dict[str, Any]:
    buckets: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    for row in rows:
        key = str(row.get(field) or "")
        actual = _to_float(row.get("actual_price_eok"))
        pred = _to_float(row.get("pure_balance_pred_eok"))
        if actual is None or pred is None:
            continue
        buckets[key].append((actual, pred))
    out: Dict[str, Any] = {}
    for key, pairs in sorted(buckets.items(), key=lambda x: (-len(x[1]), x[0])):
        out[key] = _metric_bucket(pairs)
    return out


def _prediction_risk_summary(rows: List[Dict[str, Any]], pred_field: str, group_field: str) -> Dict[str, Any]:
    buckets: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    for row in rows:
        key = str(row.get(group_field) or "")
        actual = _to_float(row.get("actual_price_eok"))
        pred = _to_float(row.get(pred_field))
        if actual is None or pred is None or actual <= 0 or pred <= 0:
            continue
        buckets[key].append((actual, pred))
    out: Dict[str, Any] = {}
    for key, pairs in sorted(buckets.items(), key=lambda x: (-len(x[1]), x[0])):
        out[key] = _metric_bucket(pairs)
    return out


def _top_failures(rows: List[Dict[str, Any]], pred_field: str, limit: int = 40) -> List[Dict[str, Any]]:
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for row in rows:
        actual = _to_float(row.get("actual_price_eok"))
        pred = _to_float(row.get(pred_field))
        if actual is None or pred is None or actual <= 0:
            continue
        abs_pct = abs(pred - actual) / max(actual, 0.1)
        scored.append((abs_pct, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    out: List[Dict[str, Any]] = []
    for abs_pct, row in scored[:limit]:
        item = {
            "combo_label": row.get("combo_label"),
            "uid": row.get("uid"),
            "number": row.get("number"),
            "actual_price_eok": row.get("actual_price_eok"),
            pred_field: row.get(pred_field),
            "abs_pct": _round4(abs_pct * 100.0),
            "publication_mode": row.get("publication_mode"),
            "base_model_applied": row.get("base_model_applied"),
            "balance_excluded": row.get("balance_excluded"),
        }
        out.append(item)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Leave-one-out audit for balance-base additive pricing")
    parser.add_argument("--report-json", default="logs/yangdo_balance_base_cv_latest.json")
    parser.add_argument("--report-md", default="logs/yangdo_balance_base_cv_latest.md")
    args = parser.parse_args()

    seed_estimator = yangdo_blackbox_api.YangdoBlackboxEstimator()
    seed_estimator.refresh()
    full_records, _token_index, meta = seed_estimator._snapshot()

    evaluator = yangdo_blackbox_api.YangdoBlackboxEstimator()
    rows: List[Dict[str, Any]] = []
    public_pairs: List[Tuple[float, float]] = []
    internal_pairs: List[Tuple[float, float]] = []
    pure_pairs: List[Tuple[float, float]] = []
    pure_non_excluded_pairs: List[Tuple[float, float]] = []
    public_modes: Counter = Counter()
    base_mode_counter: Counter = Counter()

    for rec in full_records:
        actual_price = _safe_actual_price(rec)
        if actual_price is None:
            continue
        filtered_records = _build_filtered_records(full_records, rec)
        _prime_estimator(evaluator, filtered_records, meta)
        payload = _payload_from_record(rec)
        out = evaluator.estimate(dict(payload))
        if not out.get("ok"):
            rows.append(
                {
                    "combo_label": _combo_label(_group_key(rec)),
                    "combo_size": len(_group_key(rec)),
                    "uid": str(rec.get("uid") or ""),
                    "number": int(rec.get("number") or 0),
                    "actual_price_eok": _round4(actual_price),
                    "error": str(out.get("error") or "estimate_failed"),
                }
            )
            continue

        public_center = _to_float(out.get("estimate_center_eok"))
        core_center = _to_float(out.get("core_estimate_eok"))
        internal_center = _to_float(out.get("internal_estimate_eok"))
        balance_rate = _to_float(out.get("balance_pass_through"))
        balance_adj = _to_float(out.get("balance_adjustment_eok"))
        balance_input = _to_float(payload.get("balance_eok"))
        balance_excluded = bool(out.get("balance_excluded"))
        internal_pred = internal_center
        if internal_pred is None and core_center is not None:
            internal_pred = float(core_center) + float(balance_adj or 0.0)
        pure_balance_pred = None
        if core_center is not None:
            if balance_excluded or balance_input is None:
                pure_balance_pred = float(core_center)
            else:
                rate = float(balance_rate or 1.0)
                pure_balance_pred = float(core_center) + (float(balance_input) * rate)

        if public_center is not None:
            public_pairs.append((actual_price, float(public_center)))
        if internal_pred is not None:
            internal_pairs.append((actual_price, float(internal_pred)))
        if pure_balance_pred is not None:
            pure_pairs.append((actual_price, float(pure_balance_pred)))
            if not balance_excluded:
                pure_non_excluded_pairs.append((actual_price, float(pure_balance_pred)))

        combo = _group_key(rec)
        row = {
            "combo": list(combo),
            "combo_label": _combo_label(combo),
            "combo_size": len(combo),
            "uid": str(rec.get("uid") or ""),
            "number": int(rec.get("number") or 0),
            "actual_price_eok": _round4(actual_price),
            "publication_mode": str(out.get("publication_mode") or ""),
            "base_model_applied": bool(out.get("base_model_applied")),
            "balance_excluded": bool(balance_excluded),
            "balance_model_mode": str(out.get("balance_model_mode") or ""),
            "confidence_percent": int(out.get("confidence_percent") or 0),
            "neighbor_count": int(out.get("neighbor_count") or 0),
            "effective_cluster_count": int(out.get("effective_cluster_count") or 0),
            "core_estimate_eok": _round4(core_center),
            "balance_pass_through": _round4(balance_rate),
            "balance_adjustment_eok": _round4(balance_adj),
            "engine_public_pred_eok": _round4(public_center),
            "engine_internal_pred_eok": _round4(internal_pred),
            "pure_balance_pred_eok": _round4(pure_balance_pred),
            "actual_vs_pure_ratio": _round4((float(pure_balance_pred) / actual_price) if (pure_balance_pred is not None and actual_price > 0) else None),
        }
        rows.append(row)
        public_modes[row["publication_mode"]] += 1
        base_mode_counter[str(bool(row["base_model_applied"]))] += 1

    report = {
        "generated_at": _now_str(),
        "records_evaluated": len(rows),
        "overall_publication_modes": {str(k): int(v) for k, v in public_modes.items()},
        "base_model_applied_counts": {str(k): int(v) for k, v in base_mode_counter.items()},
        "engine_public_metrics": _metric_bucket(public_pairs),
        "engine_internal_metrics": _metric_bucket(internal_pairs),
        "pure_balance_metrics": _metric_bucket(pure_pairs),
        "pure_balance_non_excluded_metrics": _metric_bucket(pure_non_excluded_pairs),
        "engine_public_risk_by_publication_mode": _prediction_risk_summary(rows, "engine_public_pred_eok", "publication_mode"),
        "engine_internal_risk_by_publication_mode": _prediction_risk_summary(rows, "engine_internal_pred_eok", "publication_mode"),
        "engine_internal_risk_by_balance_model_mode": _prediction_risk_summary(rows, "engine_internal_pred_eok", "balance_model_mode"),
        "pure_balance_by_combo_size": _build_summary(rows, "combo_size"),
        "pure_balance_by_publication_mode": _build_summary(rows, "publication_mode"),
        "top_pure_balance_failures": _top_failures(rows, "pure_balance_pred_eok", limit=50),
        "top_engine_internal_failures": _top_failures(rows, "engine_internal_pred_eok", limit=50),
        "record_rows": rows,
    }

    report_json = ROOT / args.report_json
    report_md = ROOT / args.report_md
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Yangdo Balance Base CV",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- records_evaluated: {report['records_evaluated']}",
        f"- publication_modes: {json.dumps(report['overall_publication_modes'], ensure_ascii=False)}",
        f"- base_model_applied_counts: {json.dumps(report['base_model_applied_counts'], ensure_ascii=False)}",
        "",
        "## Metrics",
    ]
    for label in ["engine_public_metrics", "engine_internal_metrics", "pure_balance_metrics", "pure_balance_non_excluded_metrics"]:
        md_lines.append(f"- {label}: {json.dumps(report[label], ensure_ascii=False)}")
    md_lines.append("")
    md_lines.append("## Engine Internal Risk By Publication Mode")
    for key, value in report["engine_internal_risk_by_publication_mode"].items():
        md_lines.append(f"- publication_mode={key}: {json.dumps(value, ensure_ascii=False)}")
    md_lines.append("")
    md_lines.append("## Engine Internal Risk By Balance Model Mode")
    for key, value in report["engine_internal_risk_by_balance_model_mode"].items():
        md_lines.append(f"- balance_model_mode={key}: {json.dumps(value, ensure_ascii=False)}")
    md_lines.append("")
    md_lines.append("## By Combo Size")
    for key, value in report["pure_balance_by_combo_size"].items():
        md_lines.append(f"- size={key}: {json.dumps(value, ensure_ascii=False)}")
    md_lines.append("")
    md_lines.append("## Worst Pure Balance Cases")
    for item in report["top_pure_balance_failures"][:20]:
        md_lines.append(
            f"- {item['combo_label']} | uid={item['uid']} no={item['number']} | actual={item['actual_price_eok']} | pure={item['pure_balance_pred_eok']} | abs_pct={item['abs_pct']}"
        )
    report_md.write_text("\n".join(md_lines).strip() + "\n", encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "generated_at": report['generated_at'],
        "records_evaluated": report['records_evaluated'],
        "report_json": str(report_json),
        "report_md": str(report_md),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
