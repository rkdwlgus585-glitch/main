#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_JSON = LOG_DIR / "partner_gate_placement_latest.json"
DEFAULT_MD = LOG_DIR / "partner_gate_placement_latest.md"
REGRESSION_REPORT = LOG_DIR / "yangdo_operational_regression_latest.json"
PARTNER_REPORT = LOG_DIR / "partner_api_contract_smoke_latest.json"

KEEP_DURATION_SEC = 12.0
KEEP_SHARE_PCT = 20.0
MOVE_DURATION_SEC = 20.0
MOVE_SHARE_PCT = 35.0


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            data = json.loads(path.read_text(encoding=encoding))
            return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


def _float(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except Exception:
        return None


def _health_contract_match_count(partner_report: Dict[str, Any]) -> int:
    total = 0
    for block_name in ("live_blackbox", "ephemeral_permit"):
        block = partner_report.get(block_name) if isinstance(partner_report.get(block_name), dict) else {}
        result = block.get("result") if isinstance(block.get("result"), dict) else {}
        rows = result.get("results") if isinstance(result.get("results"), list) else []
        for row in rows:
            if not isinstance(row, dict):
                continue
            checks = row.get("checks") if isinstance(row.get("checks"), list) else []
            for check in checks:
                if isinstance(check, dict) and str(check.get("name") or "") == "health_contract_match_local" and bool(check.get("ok")):
                    total += 1
    return total


def _coverage_notes(partner_report: Dict[str, Any]) -> List[str]:
    notes: List[str] = []
    if bool((((partner_report.get("live_blackbox") or {}).get("ok")))):
        notes.append("live blackbox의 health contract와 업무 endpoint 헤더를 실제 운영 포트에서 확인한다")
    if bool((((partner_report.get("ephemeral_permit") or {}).get("ok")))):
        notes.append("permit partner API를 ephemeral 프로세스로 띄워 health contract와 precheck endpoint를 함께 확인한다")
    if _health_contract_match_count(partner_report) >= 2:
        notes.append("로컬 dashboard 기준 health contract text와 API 응답 text가 실제로 일치하는지 검증한다")
    return notes


def build_payload() -> Dict[str, Any]:
    regression = _read_json(REGRESSION_REPORT)
    partner = _read_json(PARTNER_REPORT)

    timings = regression.get("timings") if isinstance(regression.get("timings"), dict) else {}
    total_duration_sec = _float(regression.get("total_duration_sec"))
    partner_duration_sec = _float((timings or {}).get("partner_api_contract_smoke_sec"))
    if partner_duration_sec is None:
        partner_duration_sec = _float(((partner.get("timing") or {}).get("total_duration_sec")))
    share_pct = None
    if total_duration_sec and partner_duration_sec is not None and total_duration_sec > 0:
        share_pct = round((partner_duration_sec / total_duration_sec) * 100.0, 2)

    unique_contract_checks = _health_contract_match_count(partner)
    coverage_notes = _coverage_notes(partner)

    if partner_duration_sec is None or total_duration_sec is None:
        recommendation = "insufficient_data"
        decision = "보류"
        rationale = [
            "최신 회귀 리포트에 timing 데이터가 없어 publish gate 비용을 비교할 수 없다",
            "먼저 회귀와 partner smoke를 timing 포함 버전으로 한 번 더 실행해야 한다",
        ]
    elif partner_duration_sec <= KEEP_DURATION_SEC and (share_pct is None or share_pct <= KEEP_SHARE_PCT) and unique_contract_checks >= 2:
        recommendation = "keep_in_publish_gate"
        decision = "유지"
        rationale = [
            f"partner smoke 실측 시간 {partner_duration_sec:.3f}s 는 publish gate 기준으로 과하지 않다",
            f"회귀 전체 대비 비중 {share_pct:.2f}% 로 브라우저 smoke 같은 고비용 단계보다 작다" if share_pct is not None else "회귀 전체 대비 비중 계산은 생략했다",
            "browser/public verify가 잡지 못하는 partner health contract와 API header 규약을 별도로 확인한다",
        ]
    elif partner_duration_sec >= MOVE_DURATION_SEC or (share_pct is not None and share_pct >= MOVE_SHARE_PCT):
        recommendation = "move_to_ops_loop"
        decision = "분리"
        rationale = [
            f"partner smoke 실측 시간 {partner_duration_sec:.3f}s 가 gate 비용으로 크다",
            f"회귀 전체 대비 비중 {share_pct:.2f}% 로 publish 임계비용을 초과한다" if share_pct is not None else "회귀 전체 대비 비중 계산은 생략했다",
            "publish gate에서는 핵심 smoke만 남기고 partner contract는 별도 ops loop로 돌리는 편이 낫다",
        ]
    else:
        recommendation = "keep_but_watch_cost"
        decision = "조건부 유지"
        rationale = [
            f"partner smoke 실측 시간 {partner_duration_sec:.3f}s 로 즉시 분리할 수준은 아니지만 비용 감시는 필요하다",
            f"회귀 전체 대비 비중 {share_pct:.2f}% 이다" if share_pct is not None else "회귀 전체 대비 비중 계산은 생략했다",
            "unique contract coverage가 있어 당장은 gate에 남기되, public deploy 빈도가 늘면 재평가한다",
        ]

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "ok": recommendation != "insufficient_data",
        "recommendation": recommendation,
        "decision_label": decision,
        "timing": {
            "regression_total_sec": total_duration_sec,
            "partner_api_contract_smoke_sec": partner_duration_sec,
            "partner_share_pct": share_pct,
            "thresholds": {
                "keep_duration_sec": KEEP_DURATION_SEC,
                "keep_share_pct": KEEP_SHARE_PCT,
                "move_duration_sec": MOVE_DURATION_SEC,
                "move_share_pct": MOVE_SHARE_PCT,
            },
        },
        "coverage": {
            "unique_health_contract_match_count": unique_contract_checks,
            "notes": coverage_notes,
        },
        "rationale": rationale,
        "next_actions": [
            "publish gate에는 현재 결정에 맞는 profile만 남긴다",
            "wp_surface_lab fallback smoke를 다음 병목 후보로 올린다",
            "public deploy 빈도가 높아지면 partner smoke 비용을 다시 계측한다",
        ],
        "sources": {
            "regression_report": str(REGRESSION_REPORT),
            "partner_report": str(PARTNER_REPORT),
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    timing = payload.get("timing") if isinstance(payload.get("timing"), dict) else {}
    coverage = payload.get("coverage") if isinstance(payload.get("coverage"), dict) else {}
    lines = [
        "# Partner Gate Placement Review",
        "",
        f"Updated: {payload.get('generated_at', '')}",
        "",
        "## Decision",
        f"- Recommendation: `{payload.get('recommendation')}`",
        f"- Decision label: `{payload.get('decision_label')}`",
        "",
        "## Timing",
        f"- Regression total: `{timing.get('regression_total_sec')}` sec",
        f"- Partner smoke: `{timing.get('partner_api_contract_smoke_sec')}` sec",
        f"- Partner share: `{timing.get('partner_share_pct')}`%",
        "",
        "## Coverage",
        f"- Unique health-contract matches: `{coverage.get('unique_health_contract_match_count')}`",
    ]
    for note in coverage.get("notes") or []:
        lines.append(f"- {note}")
    lines.extend(["", "## Rationale"])
    for row in payload.get("rationale") or []:
        lines.append(f"- {row}")
    lines.extend(["", "## Next Actions"])
    for row in payload.get("next_actions") or []:
        lines.append(f"- {row}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate whether partner API contract smoke should remain in the publish gate.")
    parser.add_argument("--json", default=str(DEFAULT_JSON))
    parser.add_argument("--md", default=str(DEFAULT_MD))
    args = parser.parse_args()
    payload = build_payload()
    json_path = Path(str(args.json)).resolve()
    md_path = Path(str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    rendered = json.dumps({"ok": True, "json": str(json_path), "md": str(md_path)}, ensure_ascii=False, indent=2) + "\n"
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
