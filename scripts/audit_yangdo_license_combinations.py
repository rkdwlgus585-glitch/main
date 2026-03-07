from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yangdo_blackbox_api


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        num = float(str(value).replace(",", "").strip())
        if num != num:
            return None
        return float(num)
    except Exception:
        return None


def _round4(value: Any) -> Optional[float]:
    num = _to_float(value)
    if num is None:
        return None
    return round(num, 4)


def _combo_key(rec: Dict[str, Any]) -> Tuple[str, ...]:
    tokens = sorted(str(x).strip() for x in (rec.get("license_tokens") or set()) if str(x).strip())
    return tuple(tokens)


def _combo_label(combo: Iterable[str]) -> str:
    return " + ".join(str(x).strip() for x in combo if str(x).strip())


def _payload_from_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "license_text": rec.get("license_text"),
        "specialty": rec.get("specialty"),
        "sales3_eok": rec.get("sales3_eok"),
        "sales5_eok": rec.get("sales5_eok"),
        "balance_eok": rec.get("balance_eok"),
        "capital_eok": rec.get("capital_eok"),
        "surplus_eok": rec.get("surplus_eok"),
        "license_year": rec.get("license_year"),
        "debt_ratio": rec.get("debt_ratio"),
        "liq_ratio": rec.get("liq_ratio"),
        "company_type": rec.get("company_type") or "",
        "admin_history": rec.get("admin_history") or "",
        "credit_level": rec.get("credit_level") or "",
        "reorg_mode": "share",
        "source": "combo_audit",
    }


def _median(values: Iterable[Any]) -> Optional[float]:
    nums = [float(v) for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return float(statistics.median(nums))


def _mode_text(values: Iterable[Any]) -> str:
    counter = Counter(str(v).strip() for v in values if str(v).strip())
    if not counter:
        return ""
    return str(counter.most_common(1)[0][0])


def _build_combo_prototype(combo: Tuple[str, ...], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    payload = {
        "license_text": "\n".join(combo),
        "specialty": _median(rec.get("specialty") for rec in rows),
        "sales3_eok": _median(rec.get("sales3_eok") for rec in rows),
        "sales5_eok": _median(rec.get("sales5_eok") for rec in rows),
        "balance_eok": _median(rec.get("balance_eok") for rec in rows),
        "capital_eok": _median(rec.get("capital_eok") for rec in rows),
        "surplus_eok": _median(rec.get("surplus_eok") for rec in rows),
        "license_year": _median(rec.get("license_year") for rec in rows),
        "debt_ratio": _median(rec.get("debt_ratio") for rec in rows),
        "liq_ratio": _median(rec.get("liq_ratio") for rec in rows),
        "company_type": _mode_text(rec.get("company_type") for rec in rows) or "corp",
        "admin_history": _mode_text(rec.get("admin_history") for rec in rows),
        "credit_level": _mode_text(rec.get("credit_level") for rec in rows),
        "reorg_mode": "share",
        "source": "combo_prototype_audit",
    }
    if isinstance(payload.get("license_year"), float):
        payload["license_year"] = int(round(float(payload["license_year"])))
    return payload


def _estimate(estimator: yangdo_blackbox_api.YangdoBlackboxEstimator, payload: Dict[str, Any]) -> Dict[str, Any]:
    return estimator.estimate(dict(payload))


def _append_failure(
    store: List[Dict[str, Any]],
    kind: str,
    combo: Tuple[str, ...],
    detail: Dict[str, Any],
    *,
    max_failures: int,
) -> None:
    if max_failures > 0 and len(store) >= max_failures:
        return
    item = {
        "kind": kind,
        "combo_size": len(combo),
        "combo": list(combo),
        "combo_label": _combo_label(combo),
    }
    item.update(detail)
    store.append(item)


def _evaluate_monotonic(
    estimator: yangdo_blackbox_api.YangdoBlackboxEstimator,
    combo: Tuple[str, ...],
    payload: Dict[str, Any],
    base: Dict[str, Any],
    failure_store: List[Dict[str, Any]],
    combo_stats: Dict[str, Any],
    *,
    context: Dict[str, Any],
    max_failures: int,
) -> bool:
    specialty = _to_float(payload.get("specialty"))
    sales3 = _to_float(payload.get("sales3_eok"))
    sales5 = _to_float(payload.get("sales5_eok"))
    if specialty is None or sales3 is None or specialty < 1.0 or sales3 < 0.5:
        return False
    center = _to_float(base.get("estimate_center_eok"))
    if center is None:
        return False
    lower = dict(payload)
    lower["specialty"] = round(float(specialty) * 0.7, 4)
    lower["sales3_eok"] = round(float(sales3) * 0.7, 4)
    if sales5 is not None:
        lower["sales5_eok"] = round(float(sales5) * 0.7, 4)
    lowres = _estimate(estimator, lower)
    low_center = _to_float(lowres.get("estimate_center_eok"))
    if low_center is None:
        return False
    combo_stats["monotonic_checked"] += 1
    if low_center <= float(center) * 1.03:
        return False
    combo_stats["monotonic_failures"] += 1
    _append_failure(
        failure_store,
        "scale_down_price_up",
        combo,
        {
            **context,
            "base_center_eok": _round4(center),
            "lower_center_eok": _round4(low_center),
            "delta_pct": _round4((float(low_center) / max(float(center), 0.1) - 1.0) * 100.0),
            "base_neighbor_count": int(base.get("neighbor_count") or 0),
            "lower_neighbor_count": int(lowres.get("neighbor_count") or 0),
        },
        max_failures=max_failures,
    )
    return True


def _evaluate_balance(
    estimator: yangdo_blackbox_api.YangdoBlackboxEstimator,
    combo: Tuple[str, ...],
    payload: Dict[str, Any],
    base: Dict[str, Any],
    failure_store: List[Dict[str, Any]],
    combo_stats: Dict[str, Any],
    *,
    context: Dict[str, Any],
    max_failures: int,
) -> bool:
    if estimator._is_balance_separate_paid_group(payload):
        return False
    balance = _to_float(payload.get("balance_eok"))
    if balance is None or balance < 1.3:
        return False
    center = _to_float(base.get("estimate_center_eok"))
    if center is None:
        return False
    lower = dict(payload)
    lower["balance_eok"] = round(float(balance) - 1.0, 4)
    if lower["balance_eok"] < 0:
        return False
    lowres = _estimate(estimator, lower)
    low_center = _to_float(lowres.get("estimate_center_eok"))
    if low_center is None:
        return False
    combo_stats["balance_checked"] += 1
    delta = float(center) - float(low_center)
    if delta >= 0.8:
        return False
    combo_stats["balance_failures"] += 1
    _append_failure(
        failure_store,
        "balance_minus_1_underreacts",
        combo,
        {
            **context,
            "base_center_eok": _round4(center),
            "lower_center_eok": _round4(low_center),
            "balance_delta_eok": 1.0,
            "center_delta_eok": _round4(delta),
            "base_neighbor_count": int(base.get("neighbor_count") or 0),
            "lower_neighbor_count": int(lowres.get("neighbor_count") or 0),
        },
        max_failures=max_failures,
    )
    return True


def _evaluate_price_gap(
    combo: Tuple[str, ...],
    rec: Dict[str, Any],
    base: Dict[str, Any],
    failure_store: List[Dict[str, Any]],
    combo_stats: Dict[str, Any],
    *,
    max_failures: int,
) -> bool:
    center = _to_float(base.get("estimate_center_eok"))
    current_price = _to_float(rec.get("current_price_eok"))
    if center is None or current_price is None or current_price <= 0:
        return False
    ratio = float(center) / max(float(current_price), 0.1)
    combo_stats["price_gap_checked"] += 1
    if 0.55 <= ratio <= 1.80:
        return False
    combo_stats["price_gap_failures"] += 1
    _append_failure(
        failure_store,
        "estimate_vs_known_price_gap",
        combo,
        {
            "number": int(rec.get("number") or 0),
            "uid": str(rec.get("uid") or ""),
            "known_price_eok": _round4(current_price),
            "estimate_center_eok": _round4(center),
            "estimate_to_known_ratio": _round4(ratio),
            "neighbor_count": int(base.get("neighbor_count") or 0),
        },
        max_failures=max_failures,
    )
    return True


def _render_markdown(report: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Yangdo Combination Audit")
    lines.append("")
    lines.append(f"- generated_at: {report['generated_at']}")
    lines.append(f"- observed_unique_combos: {report['observed_unique_combos']}")
    lines.append(f"- combo_size_counts: {json.dumps(report['combo_size_counts'], ensure_ascii=False)}")
    lines.append(f"- records_checked: {report['records_checked']}")
    lines.append(f"- prototype_checked: {report['prototype_checked']}")
    lines.append("")
    overall = report["overall"]
    lines.append("## Overall")
    for key in [
        "visible_estimate_count",
        "consult_only_count",
        "range_only_count",
        "monotonic_checked",
        "monotonic_failures",
        "balance_checked",
        "balance_failures",
        "price_gap_checked",
        "price_gap_failures",
        "prototype_monotonic_failures",
        "prototype_balance_failures",
    ]:
        lines.append(f"- {key}: {overall.get(key, 0)}")
    lines.append("")
    lines.append("## Top Combos")
    for item in report["top_combo_summaries"][:20]:
        lines.append(
            f"- {item['combo_label']} | n={item['records']} | mono={item['monotonic_failures']}/{item['monotonic_checked']} | "
            f"balance={item['balance_failures']}/{item['balance_checked']} | price_gap={item['price_gap_failures']}/{item['price_gap_checked']}"
        )
    lines.append("")
    lines.append("## Top Failures")
    for item in report["failures"][:40]:
        lines.append(
            f"- {item['kind']} | {item['combo_label']} | no={item.get('number', 0)} uid={item.get('uid', '')} | "
            f"base={item.get('base_center_eok')} low={item.get('lower_center_eok')} "
            f"delta_pct={item.get('delta_pct')} known_ratio={item.get('estimate_to_known_ratio')}"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Broad audit for all observed yangdo license combinations")
    parser.add_argument("--report-json", default="logs/yangdo_combo_audit_latest.json")
    parser.add_argument("--report-md", default="logs/yangdo_combo_audit_latest.md")
    parser.add_argument("--max-failures", type=int, default=800)
    args = parser.parse_args()

    estimator = yangdo_blackbox_api.YangdoBlackboxEstimator()
    estimator.refresh()
    records = list(estimator._records)

    combo_groups: Dict[Tuple[str, ...], List[Dict[str, Any]]] = defaultdict(list)
    for rec in records:
        combo = _combo_key(rec)
        if not combo or len(combo) > 6:
            continue
        combo_groups[combo].append(rec)

    failures: List[Dict[str, Any]] = []
    overall = Counter()
    combo_summaries: List[Dict[str, Any]] = []
    max_failures = int(args.max_failures)

    for combo in sorted(combo_groups.keys(), key=lambda x: (len(x), x)):
        rows = combo_groups[combo]
        stats = Counter()

        prototype = _build_combo_prototype(combo, rows)
        prototype_base = _estimate(estimator, prototype)
        if _to_float(prototype_base.get("estimate_center_eok")) is not None:
            stats["prototype_checked"] += 1
            proto_mono_before = int(stats["monotonic_failures"])
            _evaluate_monotonic(
                estimator,
                combo,
                prototype,
                prototype_base,
                failures,
                stats,
                context={"number": 0, "uid": "combo_prototype"},
                max_failures=max_failures,
            )
            if int(stats["monotonic_failures"]) > proto_mono_before:
                stats["prototype_monotonic_failures"] += 1
            proto_balance_before = int(stats["balance_failures"])
            _evaluate_balance(
                estimator,
                combo,
                prototype,
                prototype_base,
                failures,
                stats,
                context={"number": 0, "uid": "combo_prototype"},
                max_failures=max_failures,
            )
            if int(stats["balance_failures"]) > proto_balance_before:
                stats["prototype_balance_failures"] += 1

        for rec in rows:
            payload = _payload_from_record(rec)
            base = _estimate(estimator, payload)
            center = _to_float(base.get("estimate_center_eok"))
            stats["records"] += 1
            mode = str(base.get("publication_mode") or "")
            if mode == "consult_only":
                stats["consult_only_count"] += 1
            elif mode == "range_only":
                stats["range_only_count"] += 1
            if center is not None:
                stats["visible_estimate_count"] += 1
            context = {
                "number": int(rec.get("number") or 0),
                "uid": str(rec.get("uid") or ""),
            }
            _evaluate_monotonic(
                estimator,
                combo,
                payload,
                base,
                failures,
                stats,
                context=context,
                max_failures=max_failures,
            )
            _evaluate_balance(
                estimator,
                combo,
                payload,
                base,
                failures,
                stats,
                context=context,
                max_failures=max_failures,
            )
            _evaluate_price_gap(combo, rec, base, failures, stats, max_failures=max_failures)

        combo_summary = {
            "combo": list(combo),
            "combo_label": _combo_label(combo),
            "combo_size": len(combo),
            "records": int(stats["records"]),
            "visible_estimate_count": int(stats["visible_estimate_count"]),
            "consult_only_count": int(stats["consult_only_count"]),
            "range_only_count": int(stats["range_only_count"]),
            "monotonic_checked": int(stats["monotonic_checked"]),
            "monotonic_failures": int(stats["monotonic_failures"]),
            "balance_checked": int(stats["balance_checked"]),
            "balance_failures": int(stats["balance_failures"]),
            "price_gap_checked": int(stats["price_gap_checked"]),
            "price_gap_failures": int(stats["price_gap_failures"]),
            "prototype_checked": int(stats["prototype_checked"]),
            "prototype_monotonic_failures": int(stats["prototype_monotonic_failures"]),
            "prototype_balance_failures": int(stats["prototype_balance_failures"]),
        }
        combo_summaries.append(combo_summary)
        for key in [
            "records",
            "visible_estimate_count",
            "consult_only_count",
            "range_only_count",
            "monotonic_checked",
            "monotonic_failures",
            "balance_checked",
            "balance_failures",
            "price_gap_checked",
            "price_gap_failures",
            "prototype_checked",
            "prototype_monotonic_failures",
            "prototype_balance_failures",
        ]:
            overall[key] += int(stats[key])

    combo_size_counts = Counter(len(combo) for combo in combo_groups)
    combo_summaries.sort(
        key=lambda x: (
            -(x["monotonic_failures"] + x["balance_failures"] + x["price_gap_failures"]),
            -x["records"],
            x["combo_label"],
        )
    )
    report = {
        "generated_at": _now_str(),
        "observed_unique_combos": len(combo_groups),
        "combo_size_counts": {str(k): int(v) for k, v in sorted(combo_size_counts.items())},
        "records_checked": int(overall["records"]),
        "prototype_checked": int(overall["prototype_checked"]),
        "overall": {k: int(v) for k, v in overall.items()},
        "top_combo_summaries": combo_summaries[:50],
        "combo_summaries": combo_summaries,
        "failures": failures,
        "failure_store_capped": max_failures > 0 and len(failures) >= max_failures,
        "failure_store_limit": max_failures,
    }

    report_json = (ROOT / args.report_json).resolve()
    report_md = (ROOT / args.report_md).resolve()
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report_md.write_text(_render_markdown(report), encoding="utf-8")

    print(f"[saved-json] {report_json}")
    print(f"[saved-md] {report_md}")
    print(
        json.dumps(
            {
                "observed_unique_combos": report["observed_unique_combos"],
                "combo_size_counts": report["combo_size_counts"],
                "records_checked": report["records_checked"],
                "prototype_checked": report["prototype_checked"],
                "stored_failures": len(report["failures"]),
                "failure_store_capped": report["failure_store_capped"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
