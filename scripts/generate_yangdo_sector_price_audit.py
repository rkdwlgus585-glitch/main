#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_BALANCE_CV_INPUT = LOG_DIR / "yangdo_balance_base_cv_latest.json"
DEFAULT_COMBO_AUDIT_INPUT = LOG_DIR / "yangdo_combo_audit_latest.json"
DEFAULT_COMPARABLE_AUDIT_INPUT = LOG_DIR / "yangdo_comparable_selection_audit_latest.json"
DEFAULT_SETTLEMENT_INPUT = LOG_DIR / "special_sector_settlement_matrix_latest.json"
DEFAULT_JSON_OUTPUT = LOG_DIR / "yangdo_sector_price_audit_latest.json"
DEFAULT_MD_OUTPUT = LOG_DIR / "yangdo_sector_price_audit_latest.md"


@dataclass(frozen=True)
class SectorSpec:
    name: str
    aliases: tuple[str, ...]
    exact_combo: tuple[str, ...] = ()
    inherited_special_tests: bool = False


TARGET_SPECS: List[SectorSpec] = [
    SectorSpec("조경", ("조경",)),
    SectorSpec("토목", ("토목",)),
    SectorSpec("건축", ("건축",)),
    SectorSpec("토건", ("토건",), exact_combo=("건축", "토목")),
    SectorSpec("산업설비", ("산업설비", "기계설비")),
    SectorSpec("토공", ("토공",)),
    SectorSpec("포장", ("포장",)),
    SectorSpec("보링", ("보링",)),
    SectorSpec("실내건축", ("실내건축",)),
    SectorSpec("실내", ("실내",)),
    SectorSpec("금속", ("금속",)),
    SectorSpec("지붕", ("지붕",)),
    SectorSpec("도장", ("도장",)),
    SectorSpec("습식", ("습식",)),
    SectorSpec("석공", ("석공",)),
    SectorSpec("조경식재", ("조경식재",)),
    SectorSpec("조경시설", ("조경시설",)),
    SectorSpec("조경식재시설물", ("조경식재시설물",), exact_combo=("조경식재", "조경시설")),
    SectorSpec("철콘", ("철콘", "철근콘크리트")),
    SectorSpec("비계", ("비계",)),
    SectorSpec("상하수도", ("상하수도", "상하")),
    SectorSpec("철도궤도", ("철도궤도",)),
    SectorSpec("철강구조물", ("철강구조물",)),
    SectorSpec("수중", ("수중",)),
    SectorSpec("준설", ("준설",)),
    SectorSpec("승강기", ("승강기",)),
    SectorSpec("삭도기계설비", ("삭도기계설비",)),
    SectorSpec("가스1종", ("가스1종",)),
    SectorSpec("시설물", ("시설물",)),
    SectorSpec("전기", ("전기",), inherited_special_tests=True),
    SectorSpec("정보통신", ("정보통신", "통신"), inherited_special_tests=True),
    SectorSpec("소방", ("소방",), inherited_special_tests=True),
    SectorSpec("주택", ("주택",)),
    SectorSpec("대지", ("대지",)),
    SectorSpec("공동사업", ("공동사업",)),
    SectorSpec("문화재", ("문화재",)),
    SectorSpec("정비사업", ("정비사업",)),
    SectorSpec("지하수", ("지하수",)),
    SectorSpec("폐수", ("폐수",)),
    SectorSpec("에너지절약", ("에너지절약",)),
    SectorSpec("산림", ("산림",)),
    SectorSpec("산림경영", ("산림경영",)),
    SectorSpec("숲가꾸기", ("숲가꾸기",)),
    SectorSpec("산림토목", ("산림토목",)),
    SectorSpec("자연휴양림", ("자연휴양림",)),
    SectorSpec("도시림", ("도시림",)),
    SectorSpec("숲길조성", ("숲길조성",)),
    SectorSpec("나무병원", ("나무병원",)),
    SectorSpec("부동산개발", ("부동산개발",)),
    SectorSpec("석면", ("석면",)),
    SectorSpec("공법인", ("공법인",)),
]


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


def _ratio(value: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return value / total


def _tokens(raw: Iterable[Any]) -> List[str]:
    out: List[str] = []
    for item in raw or []:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def _matches_spec(spec: SectorSpec, combo: Iterable[Any], combo_label: str = "") -> Dict[str, Any]:
    tokens = _tokens(combo)
    token_set = set(tokens)
    if spec.exact_combo and token_set == set(spec.exact_combo):
        return {"match": True, "basis": "exact_combo"}
    for alias in spec.aliases:
        if alias in token_set:
            return {"match": True, "basis": "token"}
    label = str(combo_label or "")
    for alias in spec.aliases:
        if alias and alias in label:
            return {"match": True, "basis": "label_substring"}
    return {"match": False, "basis": ""}


def _row_metrics(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    abs_pcts: List[float] = []
    signed_pcts: List[float] = []
    confs: List[float] = []
    neighbors: List[float] = []
    clusters: List[float] = []
    under_67 = 0
    over_150 = 0
    count = 0
    for row in rows:
        actual = _safe_float(row.get("actual_price_eok") or row.get("actual_price_eok"))
        pred = _safe_float(row.get("engine_internal_pred_eok"))
        if actual <= 0 or pred <= 0:
            continue
        ratio = pred / actual
        abs_pcts.append(abs(ratio - 1.0) * 100.0)
        signed_pcts.append((ratio - 1.0) * 100.0)
        confs.append(_safe_float(row.get("confidence_percent")))
        neighbors.append(_safe_float(row.get("neighbor_count")))
        clusters.append(_safe_float(row.get("effective_cluster_count")))
        under_67 += int(ratio < 0.67)
        over_150 += int(ratio > 1.5)
        count += 1
    return {
        "count": count,
        "median_abs_pct": _round4(median(abs_pcts)) if abs_pcts else 0.0,
        "median_signed_pct": _round4(median(signed_pcts)) if signed_pcts else 0.0,
        "pred_lt_actual_0_67x": under_67,
        "pred_gt_actual_1_5x": over_150,
        "under_67_share": _round4(_ratio(under_67, count)),
        "over_150_share": _round4(_ratio(over_150, count)),
        "median_confidence_percent": _round4(median(confs)) if confs else 0.0,
        "median_neighbor_count": _round4(median(neighbors)) if neighbors else 0.0,
        "median_cluster_count": _round4(median(clusters)) if clusters else 0.0,
    }

def _find_combo_summary(combo_summaries: List[Dict[str, Any]], spec: SectorSpec) -> Optional[Dict[str, Any]]:
    for row in combo_summaries:
        match = _matches_spec(spec, row.get("combo") or [], row.get("combo_label") or "")
        if match["match"]:
            return row
    return None


def _special_settlement_snapshot(report: Dict[str, Any], sector_name: str) -> Dict[str, Any]:
    by_sector = dict(report.get("by_sector") or {})
    return dict(by_sector.get(sector_name) or {})


def _status_for_sector(*, observed_count: int, under_67_share: float, over_150_share: float, avg_display_neighbors: float, visible_estimate_count: int, special_green: bool) -> str:
    if observed_count <= 0:
        return "unobserved"
    if over_150_share >= 0.2:
        return "overpricing_hotspot"
    if under_67_share >= 0.5 and observed_count >= 5:
        return "underpricing_hotspot"
    if avg_display_neighbors <= 1.0 and observed_count >= 3:
        return "sparse_support_hotspot"
    if visible_estimate_count == 0 and observed_count >= 10:
        return "publication_locked"
    if special_green:
        return "special_contract_green"
    return "monitor"


def _recommended_action(status: str) -> str:
    mapping = {
        "unobserved": "실데이터 미관측 섹터다. 가격 로직 확장보다 카탈로그/데이터 유입 여부부터 점검한다.",
        "overpricing_hotspot": "public 보호를 유지한 채 과대 구간을 만드는 fallback 또는 balance-base 경로를 먼저 차단한다.",
        "underpricing_hotspot": "bounded same-sector prior 또는 residual calibration 대상으로 올린다.",
        "sparse_support_hotspot": "exact combo와 partial overlap cohort를 분리해 effective cluster를 회복한다.",
        "publication_locked": "가격 편향을 먼저 줄인 뒤 publication unlock 후보로 관리한다.",
        "special_contract_green": "기존 전기/정보통신/소방 정산 계약을 유지하고 가격 CV만 모니터링한다.",
        "monitor": "당장 엔진 개편 대상은 아니며 drift 감시만 유지한다.",
    }
    return mapping.get(status, "모니터링 유지")


def build_report(*, balance_cv: Dict[str, Any], combo_audit: Dict[str, Any], comparable_audit: Dict[str, Any], settlement_report: Dict[str, Any]) -> Dict[str, Any]:
    record_rows = list(balance_cv.get("record_rows") or [])
    combo_summaries = list(combo_audit.get("combo_summaries") or [])
    comparable_summaries = list(comparable_audit.get("combo_summaries") or [])
    invariant_failures = dict(settlement_report.get("invariant_failures") or {})
    special_green = all(_safe_int(value) == 0 for value in invariant_failures.values())

    sectors: List[Dict[str, Any]] = []
    status_counter: Counter[str] = Counter()
    for spec in TARGET_SPECS:
        matching_rows = [row for row in record_rows if _matches_spec(spec, row.get("combo") or [], row.get("combo_label") or "")["match"]]
        row_metrics = _row_metrics(matching_rows)
        pub_counter = Counter(str(row.get("publication_mode") or "") for row in matching_rows)
        balance_modes = Counter(str(row.get("balance_model_mode") or "") for row in matching_rows)
        combo_summary = _find_combo_summary(combo_summaries, spec) or {}
        comparable_summary = _find_combo_summary(comparable_summaries, spec) or {}
        exact_combo_observed = bool(combo_summary)
        support_display = _safe_float(comparable_summary.get("avg_display_neighbor_count"))
        if support_display <= 0 and matching_rows:
            support_display = _safe_float(row_metrics.get("median_neighbor_count"))
        visible_estimate_count = _safe_int(combo_summary.get("visible_estimate_count"))
        settlement_snapshot = _special_settlement_snapshot(settlement_report, spec.name) if spec.inherited_special_tests else {}
        status = _status_for_sector(
            observed_count=row_metrics["count"],
            under_67_share=_safe_float(row_metrics.get("under_67_share")),
            over_150_share=_safe_float(row_metrics.get("over_150_share")),
            avg_display_neighbors=support_display,
            visible_estimate_count=visible_estimate_count,
            special_green=bool(settlement_snapshot) and special_green,
        )
        status_counter[status] += 1
        sector_row = {
            "sector": spec.name,
            "aliases": list(spec.aliases),
            "exact_combo": list(spec.exact_combo),
            "inherited_special_tests": spec.inherited_special_tests,
            "observed_record_count": row_metrics["count"],
            "exact_combo_observed": exact_combo_observed,
            "publication_modes": dict(pub_counter),
            "balance_model_modes": dict(balance_modes),
            "visible_estimate_count": visible_estimate_count,
            "range_only_count": _safe_int(combo_summary.get("range_only_count")),
            "consult_only_count": _safe_int(combo_summary.get("consult_only_count")),
            "price_metrics": row_metrics,
            "comparable_support": {
                "avg_same_combo_ratio": _round4(comparable_summary.get("avg_same_combo_ratio")),
                "avg_same_core_ratio": _round4(comparable_summary.get("avg_same_core_ratio")),
                "avg_effective_cluster_count": _round4(comparable_summary.get("avg_effective_cluster_count")),
                "avg_display_neighbor_count": _round4(comparable_summary.get("avg_display_neighbor_count")),
                "top_reject_reasons": list(comparable_summary.get("top_reject_reasons") or [])[:3],
            },
            "settlement_snapshot": settlement_snapshot,
            "status": status,
            "recommended_action": _recommended_action(status),
        }
        sectors.append(sector_row)

    observed = [row for row in sectors if row["observed_record_count"] > 0]
    unobserved = [row for row in sectors if row["observed_record_count"] <= 0]
    underpricing = sorted(
        [row for row in sectors if row["status"] == "underpricing_hotspot"],
        key=lambda row: (-_safe_float((row.get("price_metrics") or {}).get("under_67_share")), -_safe_int(row.get("observed_record_count"))),
    )
    sparse = sorted(
        [row for row in sectors if row["status"] == "sparse_support_hotspot"],
        key=lambda row: (_safe_float((row.get("comparable_support") or {}).get("avg_display_neighbor_count")), -_safe_int(row.get("observed_record_count"))),
    )

    next_actions = [
        {
            "id": "none_mode_sector_calibration",
            "priority": "P0",
            "why": "가격 편향의 중심은 여전히 none-mode 과소평가이며, 업종별로 단일 면허 구간이 크게 묶인다.",
            "focus_sectors": [row["sector"] for row in underpricing[:8]],
            "success_metric": "selected sectors reduce under-0.67x share without increasing public over-1.5x cases.",
        },
        {
            "id": "exact_combo_sector_recovery",
            "priority": "P1",
            "why": "추천/비교군 부족 때문에 publication이 과보수화되고 none-mode 의존이 커진다.",
            "focus_sectors": [row["sector"] for row in sparse[:8]],
            "success_metric": "selected sectors reach >=2 display neighbors or remain explicitly consult-only by policy.",
        },
        {
            "id": "unobserved_sector_catalog_review",
            "priority": "P2",
            "why": "미관측 업종은 모델 문제보다 데이터/카탈로그 문제일 가능성이 크다.",
            "focus_sectors": [row["sector"] for row in unobserved[:12]],
            "success_metric": "missing sectors are either mapped, merged, or explicitly excluded with rationale.",
        },
    ]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "target_sector_count": len(TARGET_SPECS),
            "observed_sector_count": len(observed),
            "unobserved_sector_count": len(unobserved),
            "special_inherited_sector_count": sum(1 for spec in TARGET_SPECS if spec.inherited_special_tests),
            "status_counts": dict(status_counter),
            "settlement_invariants_green": special_green,
            "records_evaluated": _safe_int(balance_cv.get("records_evaluated")),
        },
        "hotspots": {
            "underpricing": underpricing[:12],
            "sparse_support": sparse[:12],
            "unobserved": unobserved[:20],
        },
        "next_actions": next_actions,
        "sectors": sectors,
    }

def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    lines: List[str] = ["# Yangdo Sector Price Audit", "", "## Summary"]
    for key in ["target_sector_count", "observed_sector_count", "unobserved_sector_count", "special_inherited_sector_count", "settlement_invariants_green", "records_evaluated"]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.append(f"- status_counts: `{json.dumps(summary.get('status_counts') or {}, ensure_ascii=False)}`")

    lines.extend(["", "## Underpricing Hotspots"])
    for row in report.get("hotspots", {}).get("underpricing", [])[:12]:
        metrics = row.get("price_metrics") or {}
        lines.append(f"- {row.get('sector')} | observed={row.get('observed_record_count')} | under_67_share={metrics.get('under_67_share')} | median_signed_pct={metrics.get('median_signed_pct')} | action={row.get('recommended_action')}")

    lines.extend(["", "## Sparse Support Hotspots"])
    for row in report.get("hotspots", {}).get("sparse_support", [])[:12]:
        support = row.get("comparable_support") or {}
        lines.append(f"- {row.get('sector')} | observed={row.get('observed_record_count')} | display_neighbors={support.get('avg_display_neighbor_count')} | same_combo={support.get('avg_same_combo_ratio')} | action={row.get('recommended_action')}")

    lines.extend(["", "## Unobserved or Unmapped"])
    for row in report.get("hotspots", {}).get("unobserved", [])[:20]:
        lines.append(f"- {row.get('sector')} | aliases={', '.join(row.get('aliases') or [])}")

    lines.extend(["", "## Next Actions"])
    for item in report.get("next_actions", []) or []:
        lines.append(f"- `{item.get('id')}` [{item.get('priority')}] {item.get('why')} / focus={json.dumps(item.get('focus_sectors') or [], ensure_ascii=False)} / metric {item.get('success_metric')}")

    lines.extend(["", "## Sector Snapshot"])
    for row in report.get("sectors", []) or []:
        metrics = row.get("price_metrics") or {}
        support = row.get("comparable_support") or {}
        lines.append(
            f"- {row.get('sector')} | status={row.get('status')} | observed={row.get('observed_record_count')} | visible={row.get('visible_estimate_count')} | under_67={metrics.get('under_67_share')} | over_150={metrics.get('over_150_share')} | clusters={support.get('avg_effective_cluster_count')} | display={support.get('avg_display_neighbor_count')}"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a full-sector Yangdo price audit.")
    parser.add_argument("--balance-cv-input", type=Path, default=DEFAULT_BALANCE_CV_INPUT)
    parser.add_argument("--combo-audit-input", type=Path, default=DEFAULT_COMBO_AUDIT_INPUT)
    parser.add_argument("--comparable-audit-input", type=Path, default=DEFAULT_COMPARABLE_AUDIT_INPUT)
    parser.add_argument("--settlement-input", type=Path, default=DEFAULT_SETTLEMENT_INPUT)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        balance_cv=_load_json(args.balance_cv_input),
        combo_audit=_load_json(args.combo_audit_input),
        comparable_audit=_load_json(args.comparable_audit_input),
        settlement_report=_load_json(args.settlement_input),
    )
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    print(f"[ok] wrote {args.json_output}")
    print(f"[ok] wrote {args.md_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
