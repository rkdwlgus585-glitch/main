import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import yangdo_blackbox_api


LOG_DIR = ROOT / "logs"
JSON_PATH = LOG_DIR / "special_sector_settlement_matrix_latest.json"
MD_PATH = LOG_DIR / "special_sector_settlement_matrix_latest.md"

REORG_MODES = ("포괄", "분할/합병")
BALANCE_MODES = ("auto", "loan_withdrawal", "credit_transfer", "none")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        num = float(value)
        if num != num:
            return None
        return num
    except Exception:
        return None


def median_or_none(values: List[float]) -> Optional[float]:
    nums = [float(v) for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return float(median(nums))


def round4(value: Any) -> Optional[float]:
    num = to_float(value)
    if num is None:
        return None
    return round(float(num), 4)


def sector_bucket(text: str) -> str:
    raw = str(text or "")
    if "전기" in raw:
        return "전기"
    if "소방" in raw:
        return "소방"
    if ("정보통신" in raw) or ("통신" in raw):
        return "정보통신"
    return "기타"


def build_payload(rec: Dict[str, Any], *, reorg_mode: str, balance_mode: str) -> Dict[str, Any]:
    return {
        "license_text": rec.get("license_text") or "",
        "license_year": rec.get("license_year"),
        "specialty": rec.get("specialty"),
        "y23": rec.get("y23"),
        "y24": rec.get("y24"),
        "y25": rec.get("y25"),
        "sales3_eok": rec.get("sales3_eok"),
        "sales5_eok": rec.get("sales5_eok"),
        "balance_eok": rec.get("input_balance_eok") if rec.get("input_balance_eok") is not None else rec.get("balance_eok"),
        "capital_eok": rec.get("capital_eok"),
        "surplus_eok": rec.get("surplus_eok"),
        "debt_ratio": rec.get("debt_ratio"),
        "liq_ratio": rec.get("liq_ratio"),
        "company_type": rec.get("company_type") or "",
        "credit_level": rec.get("credit_level") or "",
        "admin_history": rec.get("admin_history") or "",
        "reorg_mode": reorg_mode,
        "balance_usage_mode": balance_mode,
        "ok_capital": True,
        "ok_engineer": True,
        "ok_office": True,
    }


def summarize_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    publication_counts = Counter(str(row.get("publication_mode") or "") for row in rows)
    settlement_model_counts = Counter(str(row.get("settlement_model") or "") for row in rows)
    total_vals = [row.get("total_transfer_value_eok") for row in rows if row.get("total_transfer_value_eok") is not None]
    balance_vals = [row.get("realizable_balance_eok") for row in rows if row.get("realizable_balance_eok") is not None]
    cash_vals = [row.get("estimated_cash_due_eok") for row in rows if row.get("estimated_cash_due_eok") is not None]
    reduction_share_vals = []
    for row in rows:
        total = to_float(row.get("total_transfer_value_eok"))
        cash = to_float(row.get("estimated_cash_due_eok"))
        if total is None or cash is None or total <= 0:
            continue
        reduction_share_vals.append(max(0.0, min(1.0, 1.0 - (cash / total))))
    return {
        "count": len(rows),
        "publication_counts": dict(sorted(publication_counts.items())),
        "settlement_model_counts": dict(sorted(settlement_model_counts.items())),
        "median_total_transfer_value_eok": round4(median_or_none(total_vals)),
        "median_realizable_balance_eok": round4(median_or_none(balance_vals)),
        "median_estimated_cash_due_eok": round4(median_or_none(cash_vals)),
        "median_cash_reduction_share": round4(median_or_none(reduction_share_vals)),
    }


def run() -> Dict[str, Any]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    est = yangdo_blackbox_api.YangdoBlackboxEstimator()
    est.refresh()
    train_records, _, _ = est._snapshot()
    special_records = [
        rec
        for rec in train_records
        if est._is_separate_balance_group_token(rec.get("license_text") or "")
        and isinstance(rec.get("current_price_eok"), (int, float))
        and float(rec.get("current_price_eok") or 0.0) > 0
    ]
    results: List[Dict[str, Any]] = []
    invariant_failures: Dict[str, List[Dict[str, Any]]] = {
        "total_invariant": [],
        "publication_drift": [],
        "cash_order": [],
        "balance_order": [],
        "auto_out_of_window": [],
    }

    for rec in special_records:
        uid = str(rec.get("uid") or "")
        license_text = str(rec.get("license_text") or "")
        sector = sector_bucket(license_text)
        for reorg_mode in REORG_MODES:
            mode_outputs: Dict[str, Dict[str, Any]] = {}
            for balance_mode in BALANCE_MODES:
                payload = build_payload(rec, reorg_mode=reorg_mode, balance_mode=balance_mode)
                out = est.estimate(payload)
                if not out.get("ok"):
                    mode_outputs[balance_mode] = {
                        "ok": False,
                        "error": str(out.get("error") or ""),
                    }
                    continue
                row = {
                    "uid": uid,
                    "license_text": license_text,
                    "sector": sector,
                    "reorg_mode": reorg_mode,
                    "balance_mode": balance_mode,
                    "raw_balance_input_eok": round4(out.get("raw_balance_input_eok")),
                    "total_transfer_value_eok": round4(out.get("total_transfer_value_eok")),
                    "realizable_balance_eok": round4(out.get("realizable_balance_eok")),
                    "estimated_cash_due_eok": round4(out.get("estimated_cash_due_eok")),
                    "publication_mode": str(out.get("publication_mode") or ""),
                    "estimate_low_eok": round4(out.get("estimate_low_eok")),
                    "estimate_high_eok": round4(out.get("estimate_high_eok")),
                    "confidence_percent": int(out.get("confidence_percent") or 0),
                    "settlement_model": str((out.get("settlement_breakdown") or {}).get("model") or ""),
                }
                mode_outputs[balance_mode] = row
                results.append(row)

            auto_row = mode_outputs.get("auto")
            loan_row = mode_outputs.get("loan_withdrawal")
            credit_row = mode_outputs.get("credit_transfer")
            none_row = mode_outputs.get("none")
            comparable = [row for row in [auto_row, loan_row, credit_row, none_row] if isinstance(row, dict) and row.get("ok", True)]
            if len(comparable) < 4:
                continue

            totals = {
                name: to_float(row.get("total_transfer_value_eok"))
                for name, row in mode_outputs.items()
                if isinstance(row, dict)
            }
            total_values = [value for value in totals.values() if value is not None]
            if total_values and (max(total_values) - min(total_values) > 0.0001):
                invariant_failures["total_invariant"].append(
                    {"uid": uid, "license_text": license_text, "sector": sector, "reorg_mode": reorg_mode, "totals": totals}
                )

            publications = {name: str(row.get("publication_mode") or "") for name, row in mode_outputs.items()}
            if len(set(publications.values())) > 1:
                invariant_failures["publication_drift"].append(
                    {"uid": uid, "license_text": license_text, "sector": sector, "reorg_mode": reorg_mode, "publication_modes": publications}
                )

            auto_cash = to_float(auto_row.get("estimated_cash_due_eok"))
            loan_cash = to_float(loan_row.get("estimated_cash_due_eok"))
            credit_cash = to_float(credit_row.get("estimated_cash_due_eok"))
            none_cash = to_float(none_row.get("estimated_cash_due_eok"))
            if None not in (auto_cash, loan_cash, credit_cash, none_cash):
                if not (credit_cash <= loan_cash + 0.0001 <= none_cash + 0.0001):
                    invariant_failures["cash_order"].append(
                        {
                            "uid": uid,
                            "license_text": license_text,
                            "sector": sector,
                            "reorg_mode": reorg_mode,
                            "cash": {
                                "credit_transfer": round4(credit_cash),
                                "loan_withdrawal": round4(loan_cash),
                                "none": round4(none_cash),
                            },
                        }
                    )
                if not (credit_cash - 0.0001 <= auto_cash <= none_cash + 0.0001):
                    invariant_failures["auto_out_of_window"].append(
                        {
                            "uid": uid,
                            "license_text": license_text,
                            "sector": sector,
                            "reorg_mode": reorg_mode,
                            "auto_cash": round4(auto_cash),
                            "credit_cash": round4(credit_cash),
                            "loan_cash": round4(loan_cash),
                            "none_cash": round4(none_cash),
                        }
                    )

            auto_balance = to_float(auto_row.get("realizable_balance_eok"))
            loan_balance = to_float(loan_row.get("realizable_balance_eok"))
            credit_balance = to_float(credit_row.get("realizable_balance_eok"))
            none_balance = to_float(none_row.get("realizable_balance_eok"))
            if None not in (auto_balance, loan_balance, credit_balance, none_balance):
                if not (credit_balance + 0.0001 >= loan_balance >= none_balance - 0.0001):
                    invariant_failures["balance_order"].append(
                        {
                            "uid": uid,
                            "license_text": license_text,
                            "sector": sector,
                            "reorg_mode": reorg_mode,
                            "realizable_balance": {
                                "credit_transfer": round4(credit_balance),
                                "loan_withdrawal": round4(loan_balance),
                                "none": round4(none_balance),
                            },
                        }
                    )

    by_reorg_mode: Dict[str, Any] = {}
    by_sector: Dict[str, Dict[str, Any]] = defaultdict(dict)
    for reorg_mode in REORG_MODES:
        reorg_rows = [row for row in results if row.get("reorg_mode") == reorg_mode]
        by_reorg_mode[reorg_mode] = {
            mode: summarize_rows([row for row in reorg_rows if row.get("balance_mode") == mode])
            for mode in BALANCE_MODES
        }
    sectors = sorted({str(row.get("sector") or "") for row in results})
    for sector in sectors:
        sector_rows = [row for row in results if row.get("sector") == sector]
        for reorg_mode in REORG_MODES:
            reorg_rows = [row for row in sector_rows if row.get("reorg_mode") == reorg_mode]
            by_sector[sector][reorg_mode] = {
                mode: summarize_rows([row for row in reorg_rows if row.get("balance_mode") == mode])
                for mode in BALANCE_MODES
            }

    report = {
        "generated_at": now_str(),
        "records": len(special_records),
        "evaluations": len(results),
        "balance_modes": list(BALANCE_MODES),
        "reorg_modes": list(REORG_MODES),
        "rows": results,
        "overall": by_reorg_mode,
        "by_sector": by_sector,
        "invariant_failures": {
            key: {
                "count": len(value),
                "samples": value[:20],
            }
            for key, value in invariant_failures.items()
        },
    }
    return report


def to_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Special Sector Settlement Matrix Audit")
    lines.append("")
    lines.append(f"- generated_at: {report.get('generated_at')}")
    lines.append(f"- records: {report.get('records')}")
    lines.append(f"- evaluations: {report.get('evaluations')}")
    lines.append("")
    lines.append("## Invariants")
    for key, row in (report.get("invariant_failures") or {}).items():
        lines.append(f"- {key}: {row.get('count')}")
    lines.append("")
    lines.append("## Overall")
    overall = report.get("overall") or {}
    for reorg_mode, mode_map in overall.items():
        lines.append(f"### {reorg_mode}")
        for balance_mode, summary in mode_map.items():
            lines.append(
                f"- {balance_mode}: count={summary.get('count')} publication={summary.get('publication_counts')} model={summary.get('settlement_model_counts')} "
                f"median_total={summary.get('median_total_transfer_value_eok')} "
                f"median_balance={summary.get('median_realizable_balance_eok')} "
                f"median_cash={summary.get('median_estimated_cash_due_eok')} "
                f"cash_reduction_share={summary.get('median_cash_reduction_share')}"
            )
        lines.append("")
    lines.append("## By Sector")
    for sector, sector_map in (report.get("by_sector") or {}).items():
        lines.append(f"### {sector}")
        for reorg_mode, mode_map in sector_map.items():
            lines.append(f"- {reorg_mode}")
            for balance_mode, summary in mode_map.items():
                lines.append(
                    f"  - {balance_mode}: count={summary.get('count')} publication={summary.get('publication_counts')} model={summary.get('settlement_model_counts')} "
                    f"median_total={summary.get('median_total_transfer_value_eok')} "
                    f"median_balance={summary.get('median_realizable_balance_eok')} "
                    f"median_cash={summary.get('median_estimated_cash_due_eok')}"
                )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    report = run()
    JSON_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    MD_PATH.write_text(to_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(JSON_PATH), "md": str(MD_PATH)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
