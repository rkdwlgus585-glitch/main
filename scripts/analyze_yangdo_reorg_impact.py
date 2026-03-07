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


ALLOWED_LICENSES = {"전기", "정보통신", "소방"}
MODE_DEFAULT = ""
MODE_COMPREHENSIVE = "포괄"
MODE_SPLIT = "분할"
ANALYSIS_MODES = [MODE_COMPREHENSIVE, MODE_SPLIT]


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
    return round(float(num), 4)


def _quantile(values: Iterable[Any], q: float) -> Optional[float]:
    nums = sorted(float(v) for v in values if isinstance(v, (int, float)))
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0]
    qv = max(0.0, min(1.0, float(q)))
    idx = qv * (len(nums) - 1)
    lo = int(idx)
    hi = min(len(nums) - 1, lo + 1)
    frac = idx - lo
    return nums[lo] + (nums[hi] - nums[lo]) * frac


def _median(values: Iterable[Any]) -> Optional[float]:
    nums = [float(v) for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return float(statistics.median(nums))


def _base_payload(
    rec: Dict[str, Any],
    meta: Dict[str, Any],
    *,
    token: str,
    reorg_mode: str,
) -> Dict[str, Any]:
    sales3 = _to_float(rec.get("sales3_eok"))
    sales5 = _to_float(rec.get("sales5_eok"))
    specialty = _to_float(rec.get("specialty"))
    capital = _to_float(rec.get("capital_eok"))
    surplus = _to_float(rec.get("surplus_eok"))
    debt = _to_float(rec.get("debt_ratio"))
    liq = _to_float(rec.get("liq_ratio"))
    return {
        "license_text": rec.get("license_text") or token,
        "license_year": rec.get("license_year"),
        "specialty": specialty if specialty is not None else meta.get("median_specialty"),
        "y23": rec.get("years", {}).get("y23"),
        "y24": rec.get("years", {}).get("y24"),
        "y25": rec.get("years", {}).get("y25"),
        "sales3_eok": sales3 if sales3 is not None else meta.get("median_sales3_eok"),
        "sales5_eok": sales5 if sales5 is not None else max((sales3 or 0) * 1.4, 1.0),
        "balance_eok": rec.get("balance_eok"),
        "capital_eok": capital if capital is not None else meta.get("avg_capital_eok"),
        "surplus_eok": surplus if surplus is not None else meta.get("avg_surplus_eok"),
        "debt_ratio": debt if debt is not None else meta.get("avg_debt_ratio"),
        "liq_ratio": liq if liq is not None else meta.get("avg_liq_ratio"),
        "company_type": rec.get("company_type") or "주식회사",
        "credit_level": rec.get("credit_level") or "high",
        "admin_history": rec.get("admin_history") or "none",
        "ok_capital": True,
        "ok_engineer": True,
        "ok_office": True,
        "reorg_mode": reorg_mode,
        "source": "reorg_impact_analysis",
    }


def _estimate_signature(
    estimator: yangdo_blackbox_api.YangdoBlackboxEstimator,
    payload: Dict[str, Any],
) -> Optional[Dict[str, float]]:
    out = estimator.estimate(dict(payload))
    if not bool(out.get("ok")):
        return None
    center = _to_float(
        out.get("estimate_center_eok")
        if out.get("estimate_center_eok") is not None
        else out.get("core_estimate_eok")
    )
    low = _to_float(out.get("estimate_low_eok"))
    high = _to_float(out.get("estimate_high_eok"))
    conf = _to_float(out.get("confidence_score"))
    if center is None:
        return None
    sig = {
        "center_eok": float(center),
        "confidence_score": float(conf) if conf is not None else 0.0,
    }
    if low is not None and high is not None:
        sig["range_width_eok"] = max(0.0, float(high) - float(low))
    return sig


def _variant_payload(
    base_payload: Dict[str, Any],
    meta: Dict[str, Any],
    variant: str,
) -> Dict[str, Any]:
    payload = dict(base_payload)
    if variant == "specialty_omit":
        payload["specialty"] = None
    elif variant == "specialty_low":
        specialty = _to_float(base_payload.get("specialty")) or _to_float(meta.get("median_specialty")) or 1.0
        payload["specialty"] = round(max(0.1, float(specialty) * 0.45), 4)
    elif variant == "surplus_omit":
        payload["surplus_eok"] = None
    elif variant == "surplus_high":
        baseline = _to_float(base_payload.get("surplus_eok")) or _to_float(meta.get("avg_surplus_eok")) or 0.0
        payload["surplus_eok"] = round(max(float(baseline), (float(meta.get("avg_surplus_eok") or 0.0) * 2.2), 6.0), 4)
    elif variant == "credit_low":
        payload["credit_level"] = "low"
    elif variant == "credit_blank":
        payload["credit_level"] = ""
    elif variant == "debt_high":
        payload["debt_ratio"] = round(max(0.0, float(_to_float(meta.get("avg_debt_ratio")) or 20.0) * 1.35), 4)
    elif variant == "liq_low":
        payload["liq_ratio"] = round(max(0.0, float(_to_float(meta.get("avg_liq_ratio")) or 1000.0) * 0.72), 4)
    else:
        raise ValueError(f"unknown_variant:{variant}")
    return payload


def _summarize_metric(values: List[float]) -> Dict[str, Optional[float]]:
    return {
        "count": len(values),
        "median": _round4(_quantile(values, 0.5)),
        "p90": _round4(_quantile(values, 0.9)),
        "max": _round4(max(values) if values else None),
    }


def _format_pct(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{float(value):.2f}%"


def _format_num(value: Optional[float]) -> str:
    if value is None:
        return "-"
    return f"{float(value):.4f}"


def build_report() -> Dict[str, Any]:
    estimator = yangdo_blackbox_api.YangdoBlackboxEstimator()
    meta = estimator.refresh()
    train_records, _token_index, _meta = estimator._snapshot()

    license_counter: Counter[str] = Counter()
    rows: List[Tuple[str, Dict[str, Any]]] = []
    for rec in train_records:
        core_tokens = estimator._core_tokens(estimator._canonical_tokens(rec.get("license_tokens") or set()))
        if len(core_tokens) != 1:
            continue
        token = next(iter(core_tokens))
        if token not in ALLOWED_LICENSES:
            continue
        license_counter[token] += 1
        rows.append((token, rec))

    variants = [
        "specialty_omit",
        "specialty_low",
        "surplus_omit",
        "surplus_high",
        "credit_low",
        "credit_blank",
        "debt_high",
        "liq_low",
    ]
    mode_metrics: Dict[str, Dict[str, List[float]]] = {
        mode: defaultdict(list) for mode in ANALYSIS_MODES
    }
    mode_license_metrics: Dict[str, Dict[str, Dict[str, List[float]]]] = {
        mode: defaultdict(lambda: defaultdict(list)) for mode in ANALYSIS_MODES
    }
    mode_sample_counts: Dict[str, int] = {mode: 0 for mode in ANALYSIS_MODES}
    skipped_by_mode: Dict[str, int] = {mode: 0 for mode in ANALYSIS_MODES}

    for token, rec in rows:
        default_payload = _base_payload(rec, meta, token=token, reorg_mode=MODE_DEFAULT)
        default_sig = _estimate_signature(estimator, default_payload)
        if default_sig is None:
            continue

        for mode in ANALYSIS_MODES:
            payload = _base_payload(rec, meta, token=token, reorg_mode=mode)
            base_sig = _estimate_signature(estimator, payload)
            if base_sig is None:
                skipped_by_mode[mode] += 1
                continue
            mode_sample_counts[mode] += 1
            mode_metrics[mode]["base_center_eok"].append(base_sig["center_eok"])
            mode_metrics[mode]["base_confidence_score"].append(base_sig["confidence_score"])
            if isinstance(base_sig.get("range_width_eok"), (int, float)):
                mode_metrics[mode]["base_range_width_eok"].append(float(base_sig["range_width_eok"]))
            mode_metrics[mode]["delta_vs_default_center_pct"].append(
                abs(base_sig["center_eok"] - default_sig["center_eok"]) / max(default_sig["center_eok"], 0.1) * 100.0
            )
            mode_license_metrics[mode][token]["base_center_eok"].append(base_sig["center_eok"])
            mode_license_metrics[mode][token]["base_confidence_score"].append(base_sig["confidence_score"])
            if isinstance(base_sig.get("range_width_eok"), (int, float)):
                mode_license_metrics[mode][token]["base_range_width_eok"].append(float(base_sig["range_width_eok"]))
            for variant in variants:
                variant_sig = _estimate_signature(estimator, _variant_payload(payload, meta, variant))
                if variant_sig is None:
                    continue
                mode_metrics[mode][f"{variant}_center_abs_pct"].append(
                    abs(variant_sig["center_eok"] - base_sig["center_eok"]) / max(base_sig["center_eok"], 0.1) * 100.0
                )
                mode_metrics[mode][f"{variant}_conf_abs"].append(
                    abs(variant_sig["confidence_score"] - base_sig["confidence_score"])
                )
                if isinstance(base_sig.get("range_width_eok"), (int, float)) and isinstance(variant_sig.get("range_width_eok"), (int, float)):
                    mode_metrics[mode][f"{variant}_range_abs_pct"].append(
                        abs(float(variant_sig["range_width_eok"]) - float(base_sig["range_width_eok"])) / max(base_sig["center_eok"], 0.1) * 100.0
                    )

    summary: Dict[str, Any] = {
        "generated_at": _now_str(),
        "dataset_train_count": len(train_records),
        "separate_group_single_core_count": len(rows),
        "license_counter": dict(license_counter),
        "modes": {},
    }
    for mode in ANALYSIS_MODES:
        mode_summary: Dict[str, Any] = {
            "samples": mode_sample_counts[mode],
            "skipped": skipped_by_mode[mode],
            "base_center_eok": _summarize_metric(mode_metrics[mode]["base_center_eok"]),
            "base_confidence_score": _summarize_metric(mode_metrics[mode]["base_confidence_score"]),
            "base_range_width_eok": _summarize_metric(mode_metrics[mode]["base_range_width_eok"]),
            "delta_vs_default_center_pct": _summarize_metric(mode_metrics[mode]["delta_vs_default_center_pct"]),
            "variants": {},
            "licenses": {},
        }
        for variant in variants:
            mode_summary["variants"][variant] = {
                "center_abs_pct": _summarize_metric(mode_metrics[mode][f"{variant}_center_abs_pct"]),
                "confidence_abs": _summarize_metric(mode_metrics[mode][f"{variant}_conf_abs"]),
                "range_abs_pct": _summarize_metric(mode_metrics[mode][f"{variant}_range_abs_pct"]),
            }
        for token in sorted(mode_license_metrics[mode].keys()):
            token_metrics = mode_license_metrics[mode][token]
            mode_summary["licenses"][token] = {
                "samples": len(token_metrics["base_center_eok"]),
                "median_center_eok": _round4(_median(token_metrics["base_center_eok"])),
                "median_confidence_score": _round4(_median(token_metrics["base_confidence_score"])),
                "median_range_width_eok": _round4(_median(token_metrics["base_range_width_eok"])),
            }
        summary["modes"][mode] = mode_summary
    return summary


def _markdown(summary: Dict[str, Any]) -> str:
    lines = [
        "# 양도가 계산기 포괄/분할 영향 분석",
        "",
        f"- 생성시각: `{summary.get('generated_at')}`",
        f"- 전체 학습 건수: `{summary.get('dataset_train_count', 0)}`",
        f"- 분석 대상(전기/정보통신/소방 단일핵심면허): `{summary.get('separate_group_single_core_count', 0)}`",
        f"- 업종별 표본: `{json.dumps(summary.get('license_counter', {}), ensure_ascii=False)}`",
        "",
    ]
    for mode in ANALYSIS_MODES:
        mode_summary = dict(summary.get("modes", {}).get(mode, {}) or {})
        lines.extend(
            [
                f"## {mode}",
                "",
                f"- 유효 표본: `{mode_summary.get('samples', 0)}`",
                f"- 기본 기준가 중앙값(억): `{_format_num(mode_summary.get('base_center_eok', {}).get('median'))}`",
                f"- 기본 신뢰도 중앙값: `{_format_num(mode_summary.get('base_confidence_score', {}).get('median'))}`",
                f"- 기본 범위폭 중앙값(억): `{_format_num(mode_summary.get('base_range_width_eok', {}).get('median'))}`",
                f"- 무구조 대비 기준가 변동 중앙값: `{_format_pct(mode_summary.get('delta_vs_default_center_pct', {}).get('median'))}`",
                "",
                "| 변수 | 기준가 영향 중앙값 | 기준가 영향 P90 | 신뢰도 영향 중앙값 | 범위폭 영향 중앙값 |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for variant, label in [
            ("specialty_omit", "시평 생략"),
            ("specialty_low", "시평 저하"),
            ("surplus_omit", "이익잉여금 생략"),
            ("surplus_high", "이익잉여금 고값"),
            ("credit_low", "신용등급 low"),
            ("credit_blank", "신용등급 미입력"),
            ("debt_high", "부채비율 상향"),
            ("liq_low", "유동비율 하향"),
        ]:
            row = dict(mode_summary.get("variants", {}).get(variant, {}) or {})
            lines.append(
                "| {label} | {center_med} | {center_p90} | {conf_med} | {range_med} |".format(
                    label=label,
                    center_med=_format_pct(row.get("center_abs_pct", {}).get("median")),
                    center_p90=_format_pct(row.get("center_abs_pct", {}).get("p90")),
                    conf_med=_format_num(row.get("confidence_abs", {}).get("median")),
                    range_med=_format_pct(row.get("range_abs_pct", {}).get("median")),
                )
            )
        lines.extend(
            [
                "",
                "| 업종 | 표본 | 기준가 중앙값(억) | 신뢰도 중앙값 | 범위폭 중앙값(억) |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for token in sorted(mode_summary.get("licenses", {}).keys()):
            item = dict(mode_summary["licenses"][token] or {})
            lines.append(
                "| {token} | {samples} | {center} | {conf} | {width} |".format(
                    token=token,
                    samples=int(item.get("samples", 0) or 0),
                    center=_format_num(item.get("median_center_eok")),
                    conf=_format_num(item.get("median_confidence_score")),
                    width=_format_num(item.get("median_range_width_eok")),
                )
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="전기/정보통신/소방 포괄/분할 영향 분석 리포트 생성")
    parser.add_argument("--json", default="logs/yangdo_reorg_impact_latest.json")
    parser.add_argument("--markdown", default="logs/yangdo_reorg_impact_latest.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_report()
    json_path = (ROOT / str(args.json)).resolve()
    md_path = (ROOT / str(args.markdown)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown(summary), encoding="utf-8")
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
