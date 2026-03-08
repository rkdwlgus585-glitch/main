#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_SECTOR_AUDIT = LOG_DIR / "yangdo_sector_price_audit_latest.json"
DEFAULT_JSON = LOG_DIR / "yangdo_exact_pool_split_experiment_latest.json"
DEFAULT_MD = LOG_DIR / "yangdo_exact_pool_split_experiment_latest.md"
DEFAULT_FOCUS = ["토목", "석면"]

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


def _median(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return float(statistics.median(values))


def _token_set(record: Dict[str, Any]) -> Set[str]:
    return {str(token or "").strip() for token in list(record.get("license_tokens") or []) if str(token or "").strip()}


def _price(record: Dict[str, Any]) -> float:
    return _safe_float(record.get("current_price_eok"))


def _has_signal(record: Dict[str, Any]) -> bool:
    return _safe_float(record.get("sales3_eok")) > 0 or _safe_float(record.get("specialty")) > 0


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


def _collect_pool(records: List[Dict[str, Any]], aliases: Set[str], *, exact: bool) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for record in records:
        tokens = _token_set(record)
        if not tokens or not (tokens & aliases):
            continue
        if exact and len(tokens) == 1:
            out.append(record)
        if (not exact) and len(tokens) > 1:
            out.append(record)
    return out


def _pool_stats(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    prices = [_price(record) for record in records if _price(record) > 0]
    signal_count = sum(1 for record in records if _has_signal(record))
    combo_counts: Dict[str, int] = {}
    for record in records:
        combo_key = " + ".join(sorted(_token_set(record)))
        combo_counts[combo_key] = combo_counts.get(combo_key, 0) + 1
    top_combos = [
        {"key": key, "count": count}
        for key, count in sorted(combo_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]
    return {
        "count": len(records),
        "priced_count": len(prices),
        "signal_coverage_share": _round4(signal_count / len(records)) if records else 0.0,
        "median_price_eok": _round4(_median(prices)),
        "q25_price_eok": _round4(_quantile(prices, 0.25)),
        "q75_price_eok": _round4(_quantile(prices, 0.75)),
        "top_combos": top_combos,
    }


def _decision(*, exact_stats: Dict[str, Any], partial_stats: Dict[str, Any]) -> str:
    exact_count = _safe_int(exact_stats.get("priced_count"))
    partial_count = _safe_int(partial_stats.get("priced_count"))
    exact_median = _safe_float(exact_stats.get("median_price_eok"))
    partial_median = _safe_float(partial_stats.get("median_price_eok"))
    divergence = (partial_median / exact_median) if exact_median > 0 else 0.0
    if exact_count >= 8 and partial_count >= 8 and divergence >= 1.25:
        return "run_split_simulation_now"
    if exact_count >= 8 and partial_count < 8:
        return "exact_pool_stable_low_partial_noise"
    if exact_count == 0 and partial_count > 0:
        return "alias_or_catalog_first"
    if 1 <= exact_count < 8:
        return "insufficient_exact_pool"
    return "unobserved_or_empty"


def _proposed_experiment(decision: str) -> str:
    mapping = {
        "run_split_simulation_now": "exact single-license pool만으로 center/range를 다시 계산하고, partial pool은 publication 참고치로만 두는 split simulation을 추가한다.",
        "exact_pool_stable_low_partial_noise": "exact pool만으로 cohort를 재평가하고 partial pool은 보조 evidence로만 남기는 경량 실험을 추가한다.",
        "alias_or_catalog_first": "exact token alias를 정리하고 석면해체/제거 같은 catalog 토큰을 sector canonical로 묶는 매핑 실험을 먼저 한다.",
        "insufficient_exact_pool": "exact pool이 부족하므로 split보다 데이터 유입 또는 canonical merge가 먼저다.",
        "unobserved_or_empty": "해당 sector는 현재 experiment 대상이 아니라 데이터 상태를 먼저 점검한다.",
    }
    return mapping.get(decision, "monitor")


def _falsification_test(decision: str, *, exact_stats: Dict[str, Any], partial_stats: Dict[str, Any]) -> str:
    exact_count = _safe_int(exact_stats.get("priced_count"))
    partial_count = _safe_int(partial_stats.get("priced_count"))
    if decision == "run_split_simulation_now":
        return f"split 후 exact pool cluster proxy가 8건 미만으로 붕괴하거나 partial 제거 뒤 가격 안정성이 떨어지면 split 가설을 폐기한다. exact={exact_count}, partial={partial_count}."
    if decision == "alias_or_catalog_first":
        return "canonical alias를 병합해도 exact single-license pool이 0이면 split이 아니라 catalog/시장 구조 문제로 본다."
    if decision == "insufficient_exact_pool":
        return f"exact pool이 8건 미만이면 split 실험은 보류한다. 현재 exact priced={exact_count}."
    return "추가 반증 없이 drift만 감시한다."


def build_report(*, sector_audit: Dict[str, Any], focus: List[str]) -> Dict[str, Any]:
    estimator = yangdo_blackbox_api.YangdoBlackboxEstimator()
    estimator.refresh()
    records, _token_index, _meta = estimator._snapshot()
    sector_rows = [row for row in sector_audit.get("sectors") or [] if isinstance(row, dict)]

    out_rows: List[Dict[str, Any]] = []
    for sector in focus:
        sector_row = _find_sector_row(sector_rows, sector)
        aliases = _alias_set(sector_row, sector)
        exact_pool = _collect_pool(records, aliases, exact=True)
        partial_pool = _collect_pool(records, aliases, exact=False)
        exact_stats = _pool_stats(exact_pool)
        partial_stats = _pool_stats(partial_pool)
        exact_median = _safe_float(exact_stats.get("median_price_eok"))
        partial_median = _safe_float(partial_stats.get("median_price_eok"))
        price_gap_ratio = (partial_median / exact_median) if exact_median > 0 else 0.0
        decision = _decision(exact_stats=exact_stats, partial_stats=partial_stats)
        out_rows.append(
            {
                "sector": sector,
                "aliases": sorted(aliases),
                "decision": decision,
                "price_gap_ratio_partial_vs_exact": _round4(price_gap_ratio),
                "exact_pool": exact_stats,
                "partial_pool": partial_stats,
                "proposed_experiment": _proposed_experiment(decision),
                "falsification_test": _falsification_test(decision, exact_stats=exact_stats, partial_stats=partial_stats),
            }
        )

    out_rows.sort(
        key=lambda row: (
            {"run_split_simulation_now": 0, "exact_pool_stable_low_partial_noise": 1, "alias_or_catalog_first": 2, "insufficient_exact_pool": 3}.get(str(row.get("decision") or ""), 9),
            -_safe_float(row.get("price_gap_ratio_partial_vs_exact")),
            str(row.get("sector") or ""),
        )
    )
    decision_counts: Dict[str, int] = {}
    for row in out_rows:
        key = str(row.get("decision") or "")
        decision_counts[key] = decision_counts.get(key, 0) + 1

    return {
        "generated_at": _now_str(),
        "packet_id": "yangdo_exact_pool_split_experiment_latest",
        "summary": {
            "focus_sector_count": len(focus),
            "evaluated_sector_count": len(out_rows),
            "decision_counts": decision_counts,
            "top_candidates": [str(row.get("sector") or "") for row in out_rows[:5]],
        },
        "focus_sectors": focus,
        "sector_candidates": out_rows,
        "next_actions": [
            "run_split_simulation_now sector는 exact-only price band 실험을 먼저 추가한다.",
            "alias_or_catalog_first sector는 canonical alias/카탈로그 정리 없이는 split을 시도하지 않는다.",
            "exact_pool_stable_low_partial_noise sector는 partial noise 제거가 publication에 주는 효과만 경량 측정한다.",
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# Yangdo Exact Pool Split Experiment",
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
        exact_pool = row.get("exact_pool") or {}
        partial_pool = row.get("partial_pool") or {}
        lines.append(
            "- {sector}: decision={decision}, exact={exact_count}, partial={partial_count}, exact_median={exact_median}, partial_median={partial_median}, ratio={ratio}".format(
                sector=row.get("sector"),
                decision=row.get("decision"),
                exact_count=exact_pool.get("priced_count"),
                partial_count=partial_pool.get("priced_count"),
                exact_median=exact_pool.get("median_price_eok"),
                partial_median=partial_pool.get("median_price_eok"),
                ratio=row.get("price_gap_ratio_partial_vs_exact"),
            )
        )
    lines.extend(["", "## Next Actions"])
    for item in payload.get("next_actions") or []:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate exact-pool vs partial-pool split experiment plan for yangdo pricing.")
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
