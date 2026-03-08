#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BALANCE_CV_INPUT = ROOT / "logs" / "yangdo_balance_base_cv_latest.json"
DEFAULT_COMBO_AUDIT_INPUT = ROOT / "logs" / "yangdo_combo_audit_latest.json"
DEFAULT_COMPARABLE_OVERALL_INPUT = ROOT / "logs" / "yangdo_comparable_selection_overall_latest.json"
DEFAULT_COMPARABLE_AUDIT_INPUT = ROOT / "logs" / "yangdo_comparable_selection_audit_latest.json"
DEFAULT_SETTLEMENT_INPUT = ROOT / "logs" / "special_sector_settlement_matrix_latest.json"
DEFAULT_NONE_MODE_EXPERIMENT_INPUT = ROOT / "logs" / "yangdo_none_mode_sector_experiment_latest.json"
DEFAULT_PROMPT_DOC_INPUT = ROOT / "docs" / "yangdo_price_logic_critical_prompt.md"
DEFAULT_RUNTIME_SOURCE = ROOT / "yangdo_blackbox_api.py"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "yangdo_price_logic_brainstorm_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "yangdo_price_logic_brainstorm_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig")


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


def _doc_excerpt(prompt_doc: str, limit: int = 10) -> str:
    lines = [line.rstrip() for line in str(prompt_doc or "").splitlines() if line.strip()]
    return "\n".join(lines[:limit])


def _load_runtime_flags(source_text: str) -> Dict[str, bool]:
    text = str(source_text or "")
    return {
        "settlement_split_ready": all(
            marker in text
            for marker in [
                "total_transfer_value_eok",
                "estimated_cash_due_eok",
                "settlement_breakdown",
            ]
        ),
        "comparable_guard_ready": (
            "collapse_duplicate_neighbors" in text
            and (
                "strict_same_core_miss" in text
                or "_is_single_token_same_core" in text
            )
        ),
        "publication_contract_ready": "publication_mode" in text,
        "balance_mode_label_ready": "balance_model_mode" in text,
    }


def _row_metrics(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    ratios: List[float] = []
    abs_pcts: List[float] = []
    signed_pcts: List[float] = []
    under_67 = 0
    under_33 = 0
    over_150 = 0
    over_250 = 0
    confidence_values: List[float] = []
    neighbor_values: List[float] = []
    cluster_values: List[float] = []

    for row in rows:
        actual = _safe_float(row.get("actual_price_eok"))
        predicted = _safe_float(row.get("engine_internal_pred_eok"))
        if actual <= 0 or predicted <= 0:
            continue
        ratio = predicted / actual
        ratios.append(ratio)
        abs_pct = abs(ratio - 1.0) * 100.0
        signed_pct = (ratio - 1.0) * 100.0
        abs_pcts.append(abs_pct)
        signed_pcts.append(signed_pct)
        if ratio < 0.67:
            under_67 += 1
        if ratio < 0.33:
            under_33 += 1
        if ratio > 1.5:
            over_150 += 1
        if ratio > 2.5:
            over_250 += 1
        confidence_values.append(_safe_float(row.get("confidence_percent")))
        neighbor_values.append(_safe_float(row.get("neighbor_count")))
        cluster_values.append(_safe_float(row.get("effective_cluster_count")))

    count = len(ratios)
    return {
        "count": count,
        "median_abs_pct": _round4(median(abs_pcts)) if abs_pcts else 0.0,
        "median_signed_pct": _round4(median(signed_pcts)) if signed_pcts else 0.0,
        "pred_lt_actual_0_67x": under_67,
        "pred_lt_actual_0_33x": under_33,
        "pred_gt_actual_1_5x": over_150,
        "pred_gt_actual_2_5x": over_250,
        "under_67_share": _round4(_ratio(under_67, count)),
        "over_150_share": _round4(_ratio(over_150, count)),
        "median_confidence_percent": _round4(median(confidence_values)) if confidence_values else 0.0,
        "median_neighbor_count": _round4(median(neighbor_values)) if neighbor_values else 0.0,
        "median_cluster_count": _round4(median(cluster_values)) if cluster_values else 0.0,
    }


def _filter_rows(rows: Iterable[Dict[str, Any]], **criteria: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        keep = True
        for key, expected in criteria.items():
            if row.get(key) != expected:
                keep = False
                break
        if keep:
            out.append(row)
    return out


def _settlement_invariants_green(settlement_matrix: Dict[str, Any]) -> bool:
    failures = dict(settlement_matrix.get("invariant_failures") or {})
    return all(_safe_int(value) == 0 for value in failures.values())


def _make_item(*, item_id: str, priority: str, title: str, current_gap: str, evidence: str, proposed_next_step: str, success_metric: str, parallelizable_with: List[str]) -> Dict[str, Any]:
    return {
        "id": item_id,
        "priority": priority,
        "title": title,
        "current_gap": current_gap,
        "evidence": evidence,
        "proposed_next_step": proposed_next_step,
        "success_metric": success_metric,
        "parallelizable_with": parallelizable_with,
    }


def _select_execution_lane(*, full_over_150: int, none_mode_count: int, none_mode_under_share: float, one_or_less_display_total: int, single_license_under_share: float, visible_estimate_ratio: float, special_sector_invariants_green: bool) -> str:
    if full_over_150 >= 2:
        return "full_public_overpricing_guard"
    if none_mode_count >= 250 and none_mode_under_share >= 0.5:
        return "balance_model_none_replacement"
    if one_or_less_display_total >= 250:
        return "exact_combo_support_recovery"
    if single_license_under_share >= 0.35:
        return "single_license_underpricing_recovery"
    if visible_estimate_ratio < 0.05:
        return "publication_unlock_after_bias_repair"
    if not special_sector_invariants_green:
        return "special_sector_settlement_repair"
    return "publication_unlock_after_bias_repair"

def _select_parallel_lane(*, primary_id: str, none_mode_under_share: float, one_or_less_display_total: int, single_license_under_share: float, visible_estimate_ratio: float, special_sector_invariants_green: bool) -> str:
    candidates: List[str] = []
    if none_mode_under_share >= 0.5:
        candidates.append("balance_model_none_replacement")
    if one_or_less_display_total >= 250:
        candidates.append("exact_combo_support_recovery")
    if single_license_under_share >= 0.35:
        candidates.append("single_license_underpricing_recovery")
    if visible_estimate_ratio < 0.05:
        candidates.append("publication_unlock_after_bias_repair")
    if not special_sector_invariants_green:
        candidates.append("special_sector_settlement_repair")
    for candidate in candidates:
        if candidate != primary_id:
            return candidate
    return ""


def _build_critical_prompt(*, primary_title: str, records_evaluated: int, visible_estimate_ratio: float, none_mode_count: int, none_mode_under_67: int, single_license_under_67: int, one_or_less_display_total: int) -> str:
    return "\n".join([
        "You own SeoulMNA transfer-price logic, not just its UI.",
        f"The primary pricing bottleneck in this batch is '{primary_title}'.",
        (
            "State before changes: "
            f"{records_evaluated} evaluated records, "
            f"visible estimate ratio {visible_estimate_ratio:.4f}, "
            f"balance_model_mode=none count {none_mode_count}, "
            f"none-mode under-0.67x count {none_mode_under_67}, "
            f"single-license under-0.67x count {single_license_under_67}, "
            f"one-or-less comparable displays {one_or_less_display_total}."
        ),
        "Decompose the problem into comparable selection, core prior, balance handling, and publication gating.",
        "Do not confuse hiding a weak estimate with repairing the pricing model.",
        "Delete or merge branches that exist only to mask missing comparables.",
        "Total transfer value, balance usage, and cash due must stay separate in both model logic and explanation.",
        "Ship one smallest change that improves price accuracy without increasing public overpricing risk.",
    ])


def _build_first_principles_prompt(primary_title: str) -> str:
    return "\n".join([
        f"Rebuild '{primary_title}' from first principles.",
        "Ask whether the current guard is protecting users or merely hiding model weakness.",
        "If a branch only exists because support is weak, repair cohort selection before adding more copy.",
        "If balance-based fallback overprices and none-mode fallback underprices, design the smallest middle path.",
        "Treat single-license underpricing and sparse multi-license support as separate failure classes.",
        "Do not spend another batch on special-sector settlement if its invariants are already green.",
        "End with exactly three outputs: do now, hold, falsification test.",
    ])


def _musk_style_questions() -> List[str]:
    return [
        "Which branch should be deleted instead of improved?",
        "What is the minimum cohort needed to justify a public center price?",
        "Where is publication policy hiding model debt?",
        "If balance is not the root value, what is the smallest reliable core prior?",
        "What single falsification test would prove this next idea wrong?",
    ]


def build_brainstorm(*, balance_cv: Dict[str, Any], combo_audit: Dict[str, Any], comparable_overall: Dict[str, Any], comparable_audit: Dict[str, Any], settlement_matrix: Dict[str, Any], none_mode_experiment: Dict[str, Any] | None = None, prompt_doc: str = "", runtime_source_text: str = "") -> Dict[str, Any]:
    none_mode_experiment = dict(none_mode_experiment or {})
    record_rows = list(balance_cv.get("record_rows") or [])
    runtime_flags = _load_runtime_flags(runtime_source_text)

    engine_internal_metrics = dict(balance_cv.get("engine_internal_metrics") or {})
    engine_public_metrics = dict(balance_cv.get("engine_public_metrics") or {})
    combo_overall = dict(combo_audit.get("overall") or {})
    settlement_green = _settlement_invariants_green(settlement_matrix)

    none_mode_rows = _filter_rows(record_rows, balance_model_mode="none")
    single_license_rows = [row for row in record_rows if _safe_int(row.get("combo_size")) == 1]
    none_mode_metrics = _row_metrics(none_mode_rows)
    single_license_metrics = _row_metrics(single_license_rows)

    full_over_150 = _safe_int(engine_public_metrics.get("pred_gt_actual_1_5x"))
    visible_estimate_count = _safe_int(combo_overall.get("visible_estimate_count"))
    records_checked = max(1, _safe_int(combo_overall.get("records")))
    visible_estimate_ratio = _ratio(visible_estimate_count, records_checked)
    one_or_less_display_total = _safe_int(comparable_overall.get("records_one_or_less_display"))
    zero_display_total = _safe_int(comparable_overall.get("records_zero_display"))
    sparse_support_hotspots = list(comparable_audit.get("sparse_support_hotspots") or [])
    broad_match_hotspots = list(comparable_audit.get("broad_match_hotspots") or [])
    publication_modes = Counter(balance_cv.get("overall_publication_modes") or {})
    experiment_takeaways = list(none_mode_experiment.get("critical_takeaways") or [])
    experiment_sector_results = list(none_mode_experiment.get("sector_results") or [])
    experiment_ready_count = sum(1 for item in experiment_sector_results if item.get("conservative_candidate"))

    primary_id = _select_execution_lane(
        full_over_150=full_over_150,
        none_mode_count=none_mode_metrics["count"],
        none_mode_under_share=_safe_float(none_mode_metrics.get("under_67_share")),
        one_or_less_display_total=one_or_less_display_total,
        single_license_under_share=_safe_float(single_license_metrics.get("under_67_share")),
        visible_estimate_ratio=visible_estimate_ratio,
        special_sector_invariants_green=settlement_green,
    )
    parallel_id = _select_parallel_lane(
        primary_id=primary_id,
        none_mode_under_share=_safe_float(none_mode_metrics.get("under_67_share")),
        one_or_less_display_total=one_or_less_display_total,
        single_license_under_share=_safe_float(single_license_metrics.get("under_67_share")),
        visible_estimate_ratio=visible_estimate_ratio,
        special_sector_invariants_green=settlement_green,
    )

    items = [
        _make_item(
            item_id="balance_model_none_replacement",
            priority="P0",
            title="Replace the no-balance fallback with a bounded core prior",
            current_gap="The none-mode fallback is the largest systematic underpricing bucket and still drives many consult/range-only outcomes.",
            evidence=(
                f"none-mode count={none_mode_metrics['count']}, "
                f"under-0.67x={none_mode_metrics['pred_lt_actual_0_67x']}, "
                f"median_signed_pct={none_mode_metrics['median_signed_pct']}"
            ),
            proposed_next_step="Build a small same-license prior plus residual model for none-mode records and compare it against the current none-mode path without widening public overpricing.",
            success_metric="none-mode under-0.67x share drops below 0.40 while full-public over-1.5x does not increase.",
            parallelizable_with=["exact_combo_support_recovery"],
        ),
        _make_item(
            item_id="exact_combo_support_recovery",
            priority="P1",
            title="Recover exact-combo support before adding more publication surface",
            current_gap="Too many records have one or zero display comparables, so the model is forced into conservative publication even when the UI is clean.",
            evidence=(
                f"records_one_or_less_display={one_or_less_display_total}, "
                f"records_zero_display={zero_display_total}, "
                f"sparse_hotspots={len(sparse_support_hotspots)}"
            ),
            proposed_next_step="Separate exact-combo cohorts from partial-overlap cohorts and measure how many none-mode or zero-display records recover to at least two effective clusters.",
            success_metric="records_one_or_less_display falls below 250 and zero-display falls below 12 without new public overpricing failures.",
            parallelizable_with=["balance_model_none_replacement", "single_license_underpricing_recovery"],
        ),
        _make_item(
            item_id="single_license_underpricing_recovery",
            priority="P1",
            title="Recover single-license underpricing without reopening full-public risk",
            current_gap="Single-license records carry most of the systematic underpricing bias in the current engine.",
            evidence=(
                f"single-license count={single_license_metrics['count']}, "
                f"under-0.67x={single_license_metrics['pred_lt_actual_0_67x']}, "
                f"median_signed_pct={single_license_metrics['median_signed_pct']}"
            ),
            proposed_next_step="Audit single-license priors by sector and add a bounded upward calibration only where the comparable cohort is exact and cluster count is stable.",
            success_metric="single-license under-0.67x share drops below 0.30 with full-public over-1.5x remaining <= 1.",
            parallelizable_with=["exact_combo_support_recovery"],
        ),
        _make_item(
            item_id="publication_unlock_after_bias_repair",
            priority="P2",
            title="Unlock more visible estimates only after bias repair",
            current_gap="The engine is safe but still exposes very few center prices, which limits operator and customer utility.",
            evidence=(
                f"visible_estimate_count={visible_estimate_count}, "
                f"records_checked={records_checked}, "
                f"visible_ratio={visible_estimate_ratio:.4f}"
            ),
            proposed_next_step="Define a staged publication unlock rule tied to repaired none-mode bias and recovered exact-combo support instead of copy-only changes.",
            success_metric="visible_estimate_ratio exceeds 0.05 while public over-1.5x stays <= 1.",
            parallelizable_with=["balance_model_none_replacement"],
        ),
        _make_item(
            item_id="special_sector_settlement_repair",
            priority="P3",
            title="Keep special-sector settlement stable and do not let it steal the pricing batch",
            current_gap="Special-sector settlement is no longer the main failure axis, but it can still distract the batch if treated as open pricing debt.",
            evidence=f"settlement_invariants_green={settlement_green}",
            proposed_next_step="Freeze this lane unless a new invariant fails and keep price logic work focused on cohort and fallback repair.",
            success_metric="special-sector invariant failures remain zero while pricing bias work advances.",
            parallelizable_with=[],
        ),
    ]
    item_by_id = {item["id"]: item for item in items}
    primary_item = item_by_id.get(primary_id) or items[0]
    parallel_item = item_by_id.get(parallel_id) if parallel_id else {}

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "records_evaluated": _safe_int(balance_cv.get("records_evaluated")),
            "records_checked": records_checked,
            "visible_estimate_count": visible_estimate_count,
            "visible_estimate_ratio": _round4(visible_estimate_ratio),
            "full_public_count": _safe_int(publication_modes.get("full")),
            "range_only_count": _safe_int(publication_modes.get("range_only")),
            "consult_only_count": _safe_int(publication_modes.get("consult_only")),
            "engine_internal_median_abs_pct": _safe_float(engine_internal_metrics.get("median_abs_pct")),
            "engine_internal_median_signed_pct": _safe_float(engine_internal_metrics.get("median_signed_pct")),
            "engine_internal_pred_lt_actual_0_67x": _safe_int(engine_internal_metrics.get("pred_lt_actual_0_67x")),
            "engine_internal_pred_gt_actual_1_5x": _safe_int(engine_internal_metrics.get("pred_gt_actual_1_5x")),
            "none_mode_count": none_mode_metrics["count"],
            "none_mode_under_67_share": none_mode_metrics["under_67_share"],
            "none_mode_pred_lt_actual_0_67x": none_mode_metrics["pred_lt_actual_0_67x"],
            "single_license_count": single_license_metrics["count"],
            "single_license_under_67_share": single_license_metrics["under_67_share"],
            "single_license_pred_lt_actual_0_67x": single_license_metrics["pred_lt_actual_0_67x"],
            "records_one_or_less_display": one_or_less_display_total,
            "records_zero_display": zero_display_total,
            "sparse_support_hotspot_count": len(sparse_support_hotspots),
            "broad_match_hotspot_count": len(broad_match_hotspots),
            "special_sector_invariants_green": settlement_green,
            "settlement_split_ready": runtime_flags["settlement_split_ready"],
            "comparable_guard_ready": runtime_flags["comparable_guard_ready"],
            "publication_contract_ready": runtime_flags["publication_contract_ready"],
            "balance_mode_label_ready": runtime_flags["balance_mode_label_ready"],
            "prompt_doc_ready": bool(prompt_doc.strip()),
            "none_mode_experiment_ready_count": experiment_ready_count,
            "execution_lane": primary_item["id"],
            "parallel_lane": parallel_item.get("id", ""),
        },
        "current_execution_lane": primary_item,
        "parallel_brainstorm_lane": parallel_item,
        "key_evidence": [
            f"engine_internal median_abs_pct={_safe_float(engine_internal_metrics.get('median_abs_pct'))}, median_signed_pct={_safe_float(engine_internal_metrics.get('median_signed_pct'))}",
            f"none-mode count={none_mode_metrics['count']}, under-0.67x={none_mode_metrics['pred_lt_actual_0_67x']}, under_share={none_mode_metrics['under_67_share']}",
            f"single-license count={single_license_metrics['count']}, under-0.67x={single_license_metrics['pred_lt_actual_0_67x']}, under_share={single_license_metrics['under_67_share']}",
            f"records_one_or_less_display={one_or_less_display_total}, records_zero_display={zero_display_total}, avg_display_neighbors={_safe_float(comparable_overall.get('avg_display_neighbors'))}",
            f"special-sector invariants green={settlement_green}",
            f"none-mode experiment ready_count={experiment_ready_count}",
        ],
        "critical_prompt": _build_critical_prompt(
            primary_title=primary_item["title"],
            records_evaluated=_safe_int(balance_cv.get("records_evaluated")),
            visible_estimate_ratio=visible_estimate_ratio,
            none_mode_count=none_mode_metrics["count"],
            none_mode_under_67=none_mode_metrics["pred_lt_actual_0_67x"],
            single_license_under_67=single_license_metrics["pred_lt_actual_0_67x"],
            one_or_less_display_total=one_or_less_display_total,
        ),
        "first_principles_prompt": _build_first_principles_prompt(primary_item["title"]),
        "musk_style_questions": _musk_style_questions(),
        "kill_list": [
            "copy-only fixes that do not change cohort or fallback behavior",
            "full-public expansion before none-mode underpricing is reduced",
            "using special-sector settlement work as a substitute for pricing repair",
            "mixing total transfer value, balance usage, and cash due in one metric",
        ],
        "brainstorm_items": items,
        "none_mode_experiment": {
            "generated_at": none_mode_experiment.get("generated_at", ""),
            "critical_takeaways": experiment_takeaways,
            "sector_results": experiment_sector_results,
        },
        "prompt_doc_excerpt": _doc_excerpt(prompt_doc),
        "release_decision": {
            "do_now": "Use the none-mode sector experiment to patch only guarded-ready sectors first, then re-run exact-combo recovery before any publication unlock.",
            "hold": "Do not widen full-public exposure or re-open pure balance-base rollout until none-mode bias is repaired and overpricing budget remains controlled.",
            "falsification_test": "Fail the next candidate immediately if any guarded-ready sector breaches its overpricing budget or if exact-combo sparse records still stay at one-or-less display neighbors.",
        },
    }
    return report

def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    primary = dict(report.get("current_execution_lane") or {})
    parallel = dict(report.get("parallel_brainstorm_lane") or {})
    lines: List[str] = ["# Yangdo Price Logic Brainstorm", "", "## Summary"]
    for key in [
        "records_evaluated",
        "records_checked",
        "visible_estimate_count",
        "visible_estimate_ratio",
        "full_public_count",
        "range_only_count",
        "consult_only_count",
        "engine_internal_median_abs_pct",
        "engine_internal_median_signed_pct",
        "engine_internal_pred_lt_actual_0_67x",
        "engine_internal_pred_gt_actual_1_5x",
        "none_mode_count",
        "none_mode_under_67_share",
        "single_license_count",
        "single_license_under_67_share",
        "records_one_or_less_display",
        "records_zero_display",
        "sparse_support_hotspot_count",
        "broad_match_hotspot_count",
        "special_sector_invariants_green",
        "settlement_split_ready",
        "comparable_guard_ready",
        "publication_contract_ready",
        "prompt_doc_ready",
        "none_mode_experiment_ready_count",
    ]:
        lines.append(f"- {key}: `{summary.get(key)}`")
    lines.extend([
        "",
        "## Active Execution Lane",
        f"- id: `{primary.get('id', '')}`",
        f"- title: {primary.get('title', '')}",
        f"- current_gap: {primary.get('current_gap', '')}",
        f"- evidence: {primary.get('evidence', '')}",
        f"- proposed_next_step: {primary.get('proposed_next_step', '')}",
        f"- success_metric: {primary.get('success_metric', '')}",
        "",
        "## Parallel Brainstorm Lane",
    ])
    if parallel:
        lines.extend([
            f"- id: `{parallel.get('id', '')}`",
            f"- title: {parallel.get('title', '')}",
            f"- current_gap: {parallel.get('current_gap', '')}",
            f"- evidence: {parallel.get('evidence', '')}",
            f"- proposed_next_step: {parallel.get('proposed_next_step', '')}",
        ])
    else:
        lines.append("- none")
    lines.extend(["", "## Key Evidence"])
    for evidence in report.get("key_evidence") or []:
        lines.append(f"- {evidence}")
    lines.extend(["", "## Critical Prompt", "```text", report.get("critical_prompt", ""), "```"])
    lines.extend(["", "## First-Principles Prompt", "```text", report.get("first_principles_prompt", ""), "```"])
    lines.extend(["", "## Musk-Style Questions"])
    for question in report.get("musk_style_questions") or []:
        lines.append(f"- {question}")
    lines.extend(["", "## Prompt Doc Excerpt", "```text", report.get("prompt_doc_excerpt", ""), "```"])
    experiment = dict(report.get("none_mode_experiment") or {})
    lines.extend(["", "## None-Mode Experiment"])
    lines.append(f"- generated_at: `{experiment.get('generated_at', '')}`")
    for item in experiment.get("critical_takeaways") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Kill List"])
    for item in report.get("kill_list") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Brainstorm Items"])
    for item in report.get("brainstorm_items") or []:
        lines.append(f"- `{item.get('id')}` [{item.get('priority')}] {item.get('title')} / {item.get('proposed_next_step')} / metric {item.get('success_metric')}")
    decision = dict(report.get("release_decision") or {})
    lines.extend([
        "",
        "## Release Decision",
        f"- Do now: {decision.get('do_now', '')}",
        f"- Hold: {decision.get('hold', '')}",
        f"- Falsification test: {decision.get('falsification_test', '')}",
    ])
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a focused brainstorm packet for Yangdo price logic.")
    parser.add_argument("--balance-cv-input", type=Path, default=DEFAULT_BALANCE_CV_INPUT)
    parser.add_argument("--combo-audit-input", type=Path, default=DEFAULT_COMBO_AUDIT_INPUT)
    parser.add_argument("--comparable-overall-input", type=Path, default=DEFAULT_COMPARABLE_OVERALL_INPUT)
    parser.add_argument("--comparable-audit-input", type=Path, default=DEFAULT_COMPARABLE_AUDIT_INPUT)
    parser.add_argument("--settlement-input", type=Path, default=DEFAULT_SETTLEMENT_INPUT)
    parser.add_argument("--none-mode-experiment-input", type=Path, default=DEFAULT_NONE_MODE_EXPERIMENT_INPUT)
    parser.add_argument("--prompt-doc-input", type=Path, default=DEFAULT_PROMPT_DOC_INPUT)
    parser.add_argument("--runtime-source", type=Path, default=DEFAULT_RUNTIME_SOURCE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_brainstorm(
        balance_cv=_load_json(args.balance_cv_input),
        combo_audit=_load_json(args.combo_audit_input),
        comparable_overall=_load_json(args.comparable_overall_input),
        comparable_audit=_load_json(args.comparable_audit_input),
        settlement_matrix=_load_json(args.settlement_input),
        none_mode_experiment=_load_json(args.none_mode_experiment_input),
        prompt_doc=_load_text(args.prompt_doc_input),
        runtime_source_text=_load_text(args.runtime_source),
    )
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    print(f"[ok] wrote {args.json_output}")
    print(f"[ok] wrote {args.md_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
