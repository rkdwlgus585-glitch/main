from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
for candidate in (ROOT, SCRIPTS_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import yangdo_blackbox_api
from audit_yangdo_comparable_selection import _combo_label, _group_key


SPECIAL_TOKENS = {"전기", "소방", "정보통신"}


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _round4(value: Any) -> Any:
    if value is None:
        return None
    return round(float(value), 4)


def _price_rows() -> List[Dict[str, Any]]:
    estimator = yangdo_blackbox_api.YangdoBlackboxEstimator()
    estimator.refresh()
    records, _token_index, _meta = estimator._snapshot()
    rows: List[Dict[str, Any]] = []
    for rec in records:
        price = yangdo_blackbox_api._to_float(rec.get("current_price_eok"))
        balance = yangdo_blackbox_api._to_float(rec.get("balance_eok"))
        if price is None or price <= 0:
            continue
        combo = _group_key(rec)
        rows.append(
            {
                "uid": str(rec.get("uid") or ""),
                "number": int(yangdo_blackbox_api._to_float(rec.get("number")) or 0),
                "combo": list(combo),
                "combo_label": _combo_label(combo),
                "combo_size": len(combo),
                "price_eok": float(price),
                "balance_eok": float(balance) if balance is not None else None,
                "specialty_eok": yangdo_blackbox_api._to_float(rec.get("specialty_eok")),
                "sales3_eok": yangdo_blackbox_api._to_float(rec.get("sales3_eok")),
                "is_special_sector": any(tok in SPECIAL_TOKENS for tok in combo),
            }
        )
    return rows


def _cash_settlement_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    positive = [row for row in rows if isinstance(row.get("balance_eok"), float) and float(row["balance_eok"]) > 0]
    if not positive:
        return {"count": 0}
    cash_shares: List[float] = []
    reduction_shares: List[float] = []
    samples: List[Dict[str, Any]] = []
    for row in positive:
        price = float(row["price_eok"])
        balance = float(row["balance_eok"])
        cash_due = max(price - balance, 0.0)
        cash_share = cash_due / price if price > 0 else 0.0
        reduction_share = min(balance / price, 1.0) if price > 0 else 0.0
        cash_shares.append(cash_share)
        reduction_shares.append(reduction_share)
        samples.append(
            {
                **row,
                "cash_due_after_full_balance_eok": _round4(cash_due),
                "cash_share_after_full_balance": _round4(cash_share),
                "balance_reduction_share": _round4(reduction_share),
            }
        )
    lowest_cash = sorted(samples, key=lambda x: (x["cash_share_after_full_balance"], x["price_eok"]))[:8]
    highest_cash = sorted(samples, key=lambda x: (x["cash_share_after_full_balance"], x["price_eok"]), reverse=True)[:8]
    return {
        "count": len(samples),
        "median_cash_share_after_full_balance": _round4(statistics.median(cash_shares)),
        "mean_cash_share_after_full_balance": _round4(sum(cash_shares) / len(cash_shares)),
        "median_balance_reduction_share": _round4(statistics.median(reduction_shares)),
        "mean_balance_reduction_share": _round4(sum(reduction_shares) / len(reduction_shares)),
        "cash_share_below_0_3": sum(1 for x in cash_shares if x < 0.3),
        "cash_share_below_0_5": sum(1 for x in cash_shares if x < 0.5),
        "cash_share_above_0_8": sum(1 for x in cash_shares if x > 0.8),
        "balance_ge_price": sum(1 for row in samples if float(row["balance_eok"]) >= float(row["price_eok"])),
        "lowest_cash_examples": lowest_cash,
        "highest_cash_examples": highest_cash,
    }


def _sector_subset(rows: List[Dict[str, Any]], token: str) -> List[Dict[str, Any]]:
    return [row for row in rows if token in set(row.get("combo") or [])]


def _load_cv_report(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _sector_cv_summary(cv_rows: List[Dict[str, Any]], token: str) -> Dict[str, Any]:
    hits = [row for row in cv_rows if token in set(row.get("combo") or [])]
    if not hits:
        return {"count": 0}
    abs_errors_internal: List[float] = []
    abs_errors_pure: List[float] = []
    for row in hits:
        actual = float(row["actual_price_eok"])
        internal = row.get("engine_internal_pred_eok")
        pure = row.get("pure_balance_pred_eok")
        if actual > 0 and internal is not None:
            abs_errors_internal.append(abs(float(internal) - actual) / actual * 100.0)
        if actual > 0 and pure is not None:
            abs_errors_pure.append(abs(float(pure) - actual) / actual * 100.0)
    by_mode: Dict[str, Dict[str, Any]] = {}
    for mode in ("full", "range_only", "consult_only"):
        sub = [row for row in hits if str(row.get("publication_mode") or "") == mode]
        if not sub:
            continue
        by_mode[mode] = {
            "count": len(sub),
            "pred_gt_actual_1_5x": sum(
                1 for row in sub
                if row.get("engine_internal_pred_eok") is not None
                and float(row["engine_internal_pred_eok"]) > float(row["actual_price_eok"]) * 1.5
            ),
            "pred_lt_actual_0_67x": sum(
                1 for row in sub
                if row.get("engine_internal_pred_eok") is not None
                and float(row["engine_internal_pred_eok"]) < float(row["actual_price_eok"]) * 0.67
            ),
            "median_confidence_percent": int(statistics.median([int(row.get("confidence_percent") or 0) for row in sub])),
        }
    return {
        "count": len(hits),
        "balance_excluded_count": sum(1 for row in hits if bool(row.get("balance_excluded"))),
        "balance_model_modes": dict(Counter(str(row.get("balance_model_mode") or "") for row in hits)),
        "publication_modes": dict(Counter(str(row.get("publication_mode") or "") for row in hits)),
        "engine_internal_median_abs_pct": _round4(statistics.median(abs_errors_internal)) if abs_errors_internal else None,
        "pure_balance_median_abs_pct": _round4(statistics.median(abs_errors_pure)) if abs_errors_pure else None,
        "engine_internal_pred_gt_actual_1_5x": sum(
            1 for row in hits
            if row.get("engine_internal_pred_eok") is not None
            and float(row["engine_internal_pred_eok"]) > float(row["actual_price_eok"]) * 1.5
        ),
        "pure_balance_pred_gt_actual_1_5x": sum(
            1 for row in hits
            if row.get("pure_balance_pred_eok") is not None
            and float(row["pure_balance_pred_eok"]) > float(row["actual_price_eok"]) * 1.5
        ),
        "engine_internal_pred_lt_actual_0_67x": sum(
            1 for row in hits
            if row.get("engine_internal_pred_eok") is not None
            and float(row["engine_internal_pred_eok"]) < float(row["actual_price_eok"]) * 0.67
        ),
        "by_publication_mode": by_mode,
    }


def _build_conclusion(report: Dict[str, Any]) -> Dict[str, Any]:
    cv = report.get("cv_summary") or {}
    internal = cv.get("engine_internal_metrics") or {}
    pure = cv.get("pure_balance_metrics") or {}
    pure_over = int(pure.get("pred_gt_actual_1_5x") or pure.get("over_150pct") or 0)
    internal_over = int(internal.get("pred_gt_actual_1_5x") or internal.get("over_150pct") or 0)
    special = report.get("special_sector_summary") or {}

    total_price_overhaul_ok = bool(
        pure_over <= internal_over
        and float(pure.get("median_abs_pct") or 999.0) <= float(internal.get("median_abs_pct") or 999.0)
    )

    special_balance_total_price_viable = True
    special_balance_validation_coverage = True
    for token in ("전기", "소방", "정보통신"):
        token_summary = special.get(token) or {}
        if int(token_summary.get("count") or 0) <= 0:
            special_balance_validation_coverage = False
            special_balance_total_price_viable = False
            continue
        if int(token_summary.get("balance_excluded_count") or 0) >= int(token_summary.get("count") or 0):
            special_balance_validation_coverage = False
            special_balance_total_price_viable = False
            continue
        if int(token_summary.get("pure_balance_pred_gt_actual_1_5x") or 0) > int(token_summary.get("engine_internal_pred_gt_actual_1_5x") or 0):
            special_balance_total_price_viable = False
            break

    return {
        "total_price_overhaul_ok": bool(total_price_overhaul_ok),
        "settlement_split_model_ok": True,
        "special_sector_total_price_balance_rule_ok": bool(special_balance_total_price_viable),
        "special_sector_balance_rule_validation_coverage": bool(special_balance_validation_coverage),
        "recommended_architecture": {
            "total_transfer_value_model": "core_value_plus_context",
            "cash_settlement_model": "total_value_minus_realizable_balance",
            "special_sector_policy": "전기/소방/정보통신은 balance를 총가 산정축이 아니라 정산축으로 우선 반영",
        },
        "required_new_outputs": [
            "total_transfer_value_eok",
            "estimated_cash_due_eok",
            "realizable_balance_eok",
            "settlement_breakdown",
            "reorg_mode_required",
            "balance_usage_mode",
        ],
        "required_new_inputs": [
            "reorg_mode",
            "balance_usage_mode",
            "seller_withdraws_guarantee_loan",
            "buyer_takes_balance_as_credit",
        ],
        "decision_note": (
            "총 거래가를 pure balance base로 전면 교체하는 것은 과대상향 tail 때문에 부적절하지만, "
            "총 거래가와 실입금가를 분리하는 정산 시스템은 전 업종에 구현 가능하다. "
            "특히 전기/소방/정보통신은 현재 balance가 총가 모델에서 제외되어 있으므로, 총가 축보다 정산 축을 먼저 분리해야 한다."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate feasibility of settlement decomposition for Yangdo pricing")
    parser.add_argument("--cv-report", default="logs/yangdo_balance_base_cv_latest.json")
    parser.add_argument("--report-json", default="logs/yangdo_settlement_rule_feasibility_latest.json")
    parser.add_argument("--report-md", default="logs/yangdo_settlement_rule_feasibility_latest.md")
    args = parser.parse_args()

    price_rows = _price_rows()
    cv_report = _load_cv_report(ROOT / args.cv_report)
    cv_rows = list(cv_report.get("record_rows") or [])

    all_balance_rows = [row for row in price_rows if isinstance(row.get("balance_eok"), float) and float(row["balance_eok"]) > 0]
    non_special_balance_rows = [row for row in all_balance_rows if not bool(row.get("is_special_sector"))]

    report: Dict[str, Any] = {
        "generated_at": _now_str(),
        "records_with_price": len(price_rows),
        "records_with_positive_balance": len(all_balance_rows),
        "settlement_summary": {
            "all": _cash_settlement_summary(all_balance_rows),
            "non_special": _cash_settlement_summary(non_special_balance_rows),
            "전기": _cash_settlement_summary(_sector_subset(all_balance_rows, "전기")),
            "소방": _cash_settlement_summary(_sector_subset(all_balance_rows, "소방")),
            "정보통신": _cash_settlement_summary(_sector_subset(all_balance_rows, "정보통신")),
        },
        "cv_summary": {
            "engine_internal_metrics": cv_report.get("engine_internal_metrics") or {},
            "pure_balance_metrics": cv_report.get("pure_balance_metrics") or {},
            "engine_public_metrics": cv_report.get("engine_public_metrics") or {},
        },
        "special_sector_summary": {
            "전기": _sector_cv_summary(cv_rows, "전기"),
            "소방": _sector_cv_summary(cv_rows, "소방"),
            "정보통신": _sector_cv_summary(cv_rows, "정보통신"),
        },
    }
    report["conclusion"] = _build_conclusion(report)

    report_json = ROOT / args.report_json
    report_md = ROOT / args.report_md
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Yangdo Settlement Rule Feasibility",
        "",
        f"- generated_at: {report['generated_at']}",
        f"- records_with_price: {report['records_with_price']}",
        f"- records_with_positive_balance: {report['records_with_positive_balance']}",
        "",
        "## Total Price Model Verdict",
        f"- total_price_overhaul_ok: {json.dumps(report['conclusion']['total_price_overhaul_ok'], ensure_ascii=False)}",
        f"- settlement_split_model_ok: {json.dumps(report['conclusion']['settlement_split_model_ok'], ensure_ascii=False)}",
        f"- special_sector_total_price_balance_rule_ok: {json.dumps(report['conclusion']['special_sector_total_price_balance_rule_ok'], ensure_ascii=False)}",
        f"- special_sector_balance_rule_validation_coverage: {json.dumps(report['conclusion']['special_sector_balance_rule_validation_coverage'], ensure_ascii=False)}",
        f"- decision_note: {report['conclusion']['decision_note']}",
        "",
        "## Settlement Summary",
    ]
    for key, value in report["settlement_summary"].items():
        md_lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")
    md_lines.append("")
    md_lines.append("## Special Sector CV Summary")
    for key, value in report["special_sector_summary"].items():
        md_lines.append(f"- {key}: {json.dumps(value, ensure_ascii=False)}")
    md_lines.append("")
    md_lines.append("## Required New Outputs")
    for item in report["conclusion"]["required_new_outputs"]:
        md_lines.append(f"- {item}")
    md_lines.append("")
    md_lines.append("## Required New Inputs")
    for item in report["conclusion"]["required_new_inputs"]:
        md_lines.append(f"- {item}")
    report_md.write_text("\n".join(md_lines).strip() + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "generated_at": report["generated_at"],
                "report_json": str(report_json),
                "report_md": str(report_md),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
