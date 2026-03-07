from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"

MATRIX_PATH = LOG_DIR / "special_sector_settlement_matrix_latest.json"
OUT_JSON = LOG_DIR / "special_sector_auto_policy_brainstorm_latest.json"
OUT_MD = LOG_DIR / "special_sector_auto_policy_brainstorm_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            data = json.loads(path.read_text(encoding=encoding))
            return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


def _to_float(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except Exception:
        return None


def _median(values: List[float]) -> float | None:
    nums = [float(v) for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return float(median(nums))


def _percentile(values: List[float], q: float) -> float | None:
    nums = sorted(float(v) for v in values if isinstance(v, (int, float)))
    if not nums:
        return None
    if len(nums) == 1:
        return float(nums[0])
    q = max(0.0, min(1.0, float(q)))
    pos = q * (len(nums) - 1)
    low = int(pos)
    high = min(len(nums) - 1, low + 1)
    weight = pos - low
    return float(nums[low] * (1.0 - weight) + nums[high] * weight)


def _round4(value: Any) -> float | None:
    num = _to_float(value)
    if num is None:
        return None
    return round(float(num), 4)


def _meaningful_threshold(value: float | None, *, floor: float = 0.0005) -> float | None:
    num = _to_float(value)
    if num is None:
        return None
    if abs(float(num)) < float(floor):
        return None
    return float(num)


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _clean_sector_label(raw: Any) -> str:
    text = str(raw or "")
    if "전기" in text or "?꾧린" in text:
        return "전기"
    if "소방" in text or "?뚮갑" in text:
        return "소방"
    if "정보통신" in text or "?뺣낫?듭떊" in text or "?듭떊" in text:
        return "정보통신"
    return text or "unknown"


def _clean_reorg_label(raw: Any) -> str:
    text = str(raw or "")
    lower = text.lower()
    if "포괄" in text or "?ш큵" in text or "comprehensive" in lower:
        return "포괄"
    if "분할" in text or "합병" in text or "遺꾪븷" in text or "?⑸퀝" in text or "split" in lower or "merge" in lower:
        return "분할/합병"
    return text or "unknown"


def _pair_rows(rows: List[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Dict[str, Any]]]:
    paired: Dict[Tuple[str, str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = (
            str(row.get("uid") or ""),
            _clean_sector_label(row.get("sector")),
            _clean_reorg_label(row.get("reorg_mode")),
        )
        mode = str(row.get("balance_mode") or "")
        paired[key][mode] = row
    return paired


def _recommendations_for_group(group_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    auto_none_shares: List[float] = []
    auto_loan_shares: List[float] = []
    auto_none_balances: List[float] = []
    auto_loan_balances: List[float] = []
    credit_extra_deltas: List[float] = []
    loan_vs_none_deltas: List[float] = []

    paired = _pair_rows(group_rows)
    for rows in paired.values():
        auto_row = rows.get("auto")
        loan_row = rows.get("loan_withdrawal")
        credit_row = rows.get("credit_transfer")
        none_row = rows.get("none")
        if not all(isinstance(item, dict) for item in (auto_row, loan_row, credit_row, none_row)):
            continue

        total = _to_float(auto_row.get("total_transfer_value_eok"))
        raw_balance = _to_float(auto_row.get("raw_balance_input_eok"))
        auto_cash = _to_float(auto_row.get("estimated_cash_due_eok"))
        loan_cash = _to_float(loan_row.get("estimated_cash_due_eok"))
        credit_cash = _to_float(credit_row.get("estimated_cash_due_eok"))
        none_cash = _to_float(none_row.get("estimated_cash_due_eok"))
        auto_model = str(auto_row.get("settlement_model") or "")

        if total and total > 0 and raw_balance is not None:
            share = raw_balance / total
            if auto_model == "none":
                auto_none_shares.append(share)
                auto_none_balances.append(raw_balance)
            elif auto_model == "loan_withdrawal":
                auto_loan_shares.append(share)
                auto_loan_balances.append(raw_balance)

        if None not in (loan_cash, credit_cash):
            credit_extra_deltas.append(max(0.0, loan_cash - credit_cash))
        if None not in (auto_cash, none_cash):
            loan_vs_none_deltas.append(max(0.0, none_cash - auto_cash))

    none_share_max = max(auto_none_shares) if auto_none_shares else None
    loan_share_min = min(auto_loan_shares) if auto_loan_shares else None
    none_balance_max = max(auto_none_balances) if auto_none_balances else None
    loan_balance_min = min(auto_loan_balances) if auto_loan_balances else None

    share_cutoff = None
    if none_share_max is not None and loan_share_min is not None and none_share_max < loan_share_min:
        share_cutoff = (none_share_max + loan_share_min) / 2.0

    balance_cutoff = None
    if none_balance_max is not None and loan_balance_min is not None and none_balance_max < loan_balance_min:
        balance_cutoff = (none_balance_max + loan_balance_min) / 2.0

    overlap_detected = bool(auto_none_shares and auto_loan_shares and share_cutoff is None)
    conservative_none_share_cap = _meaningful_threshold(_percentile(auto_none_shares, 0.90) if overlap_detected else None)
    conservative_none_balance_cap = _meaningful_threshold(
        _percentile(auto_none_balances, 0.90)
        if auto_none_balances and auto_loan_balances and balance_cutoff is None
        else None
    )

    recommendation_lines: List[str] = []
    if share_cutoff is not None:
        recommendation_lines.append(f"share cutoff candidate ~= {round(share_cutoff, 4)}")
    elif conservative_none_share_cap is not None:
        recommendation_lines.append(
            f"overlap remains; conservative none share cap candidate ~= {round(conservative_none_share_cap, 4)}"
        )
    if balance_cutoff is not None:
        recommendation_lines.append(f"balance cutoff candidate ~= {round(balance_cutoff, 4)}")
    elif conservative_none_balance_cap is not None:
        recommendation_lines.append(
            f"overlap remains; conservative none balance cap candidate ~= {round(conservative_none_balance_cap, 4)}"
        )

    credit_extra = _median(credit_extra_deltas)
    loan_gain = _median(loan_vs_none_deltas)
    if _to_float(credit_extra) is not None and float(credit_extra or 0.0) >= 0.03:
        recommendation_lines.append("credit_transfer should stay visible as an explicit negotiation scenario")
    if _to_float(loan_gain) is not None and float(loan_gain or 0.0) < 0.02:
        recommendation_lines.append("auto loan benefit is small; consider stronger none defaulting in low-balance cases")
    elif _to_float(loan_gain) is not None:
        recommendation_lines.append("loan_withdrawal remains a defensible auto default when balance threshold is cleared")

    return {
        "auto_none_count": len(auto_none_shares),
        "auto_loan_count": len(auto_loan_shares),
        "none_share_max": _round4(none_share_max),
        "loan_share_min": _round4(loan_share_min),
        "none_balance_max": _round4(none_balance_max),
        "loan_balance_min": _round4(loan_balance_min),
        "candidate_share_cutoff": _round4(share_cutoff),
        "candidate_balance_cutoff": _round4(balance_cutoff),
        "conservative_none_share_cap": _round4(conservative_none_share_cap),
        "conservative_none_balance_cap": _round4(conservative_none_balance_cap),
        "overlap_detected": overlap_detected,
        "median_credit_extra_vs_loan_eok": _round4(credit_extra),
        "median_loan_gain_vs_none_eok": _round4(loan_gain),
        "recommendation_lines": recommendation_lines,
    }


def build_report() -> Dict[str, Any]:
    matrix = _load_json(MATRIX_PATH)
    rows_by_sector_reorg: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

    for reorg_mode, mode_map in (matrix.get("overall") or {}).items():
        if not isinstance(mode_map, dict):
            continue

    # Rebuild from raw evaluation rows if present in future; for now flatten by_sector summary is insufficient,
    # so regenerate from the matrix file structure only when detailed rows are absent.
    raw_rows = matrix.get("rows")
    if isinstance(raw_rows, list) and raw_rows:
        iterable_rows = [row for row in raw_rows if isinstance(row, dict)]
    else:
        # Fallback: derive rows from current matrix schema samples is not enough, so read from audit source report.
        audit_source = _load_json(MATRIX_PATH)
        iterable_rows = [row for row in audit_source.get("results", []) if isinstance(row, dict)]

    # Compatibility with current audit output: if raw rows are not embedded, load from sidecar rebuild file if added later.
    if not iterable_rows:
        # The current matrix report does not persist all rows. Report only from aggregate summaries.
        return {
            "generated_at": _now(),
            "ok": True,
            "source": str(MATRIX_PATH),
            "mode": "aggregate_only",
            "recommendations": [
                "Persist per-row settlement audit results to support data-driven auto policy tuning.",
                "Current aggregate snapshot shows auto ~= loan_withdrawal for electric/telecom and high none-rate for fire.",
                "Next engine change should be guided by share/balance cutoffs computed from raw rows, not by intuition.",
            ],
            "by_sector": {},
        }

    for row in iterable_rows:
        sector = _clean_sector_label(row.get("sector"))
        reorg_mode = _clean_reorg_label(row.get("reorg_mode"))
        rows_by_sector_reorg[(sector, reorg_mode)].append(row)

    by_sector: Dict[str, Dict[str, Any]] = defaultdict(dict)
    top_recommendations: List[str] = []
    seen_recommendations: set[str] = set()

    def push_recommendation(text: str) -> None:
        item = str(text or "").strip()
        if not item or item in seen_recommendations:
            return
        seen_recommendations.add(item)
        top_recommendations.append(item)

    for (sector, reorg_mode), rows in sorted(rows_by_sector_reorg.items()):
        analysis = _recommendations_for_group(rows)
        by_sector[sector][reorg_mode] = analysis
        for line in analysis.get("recommendation_lines") or []:
            push_recommendation(f"{sector} / {reorg_mode}: {line}")

    return {
        "generated_at": _now(),
        "ok": True,
        "source": str(MATRIX_PATH),
        "mode": "row_analysis",
        "recommendations": top_recommendations[:20],
        "by_sector": by_sector,
    }


def to_markdown(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Special Sector Auto Policy Brainstorm")
    lines.append("")
    lines.append(f"- generated_at: {report.get('generated_at')}")
    lines.append(f"- source: {report.get('source')}")
    lines.append(f"- mode: {report.get('mode')}")
    lines.append("")
    lines.append("## Top Recommendations")
    for line in report.get("recommendations") or []:
        lines.append(f"- {line}")
    lines.append("")
    lines.append("## By Sector")
    for sector, reorg_map in (report.get("by_sector") or {}).items():
        lines.append(f"### {sector}")
        for reorg_mode, row in reorg_map.items():
            lines.append(
                f"- {reorg_mode}: auto_none={row.get('auto_none_count')} auto_loan={row.get('auto_loan_count')} "
                f"share_cutoff={row.get('candidate_share_cutoff')} balance_cutoff={row.get('candidate_balance_cutoff')} "
                f"conservative_share_cap={row.get('conservative_none_share_cap')} conservative_balance_cap={row.get('conservative_none_balance_cap')} "
                f"credit_extra={row.get('median_credit_extra_vs_loan_eok')} loan_gain={row.get('median_loan_gain_vs_none_eok')}"
            )
            for item in row.get("recommendation_lines") or []:
                lines.append(f"  - {item}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    report = build_report()
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(to_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(OUT_JSON), "md": str(OUT_MD), "mode": report.get("mode")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
