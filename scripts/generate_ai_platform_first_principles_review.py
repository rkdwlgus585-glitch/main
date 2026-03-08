#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_JSON = LOG_DIR / "ai_platform_first_principles_review_latest.json"
DEFAULT_MD = LOG_DIR / "ai_platform_first_principles_review_latest.md"
DEFAULT_DASHBOARD = LOG_DIR / "ai_admin_dashboard_latest.json"
DEFAULT_REGRESSION = LOG_DIR / "yangdo_operational_regression_latest.json"
DEFAULT_BRAINSTORM = LOG_DIR / "ai_platform_next_brainstorm_latest.md"
DEFAULT_GATE_REVIEW = LOG_DIR / "partner_gate_placement_latest.json"
DEFAULT_FALLBACK_SMOKE = LOG_DIR / "wp_surface_lab_fallback_smoke_latest.json"


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


def _lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _brainstorm_candidates(lines: List[str]) -> List[str]:
    items: List[str] = []
    in_candidates = False
    for raw in lines:
        text = str(raw or "").rstrip()
        if text.startswith("## Next Candidates"):
            in_candidates = True
            continue
        if in_candidates and text.startswith("## "):
            break
        if in_candidates and text[:2] in {"1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."}:
            items.append(text)
    return items


def _one_line(dashboard: Dict[str, Any]) -> str:
    return str(((dashboard.get("one_line_summary") or {}).get("text")) or "").strip()


def build_review_payload() -> Dict[str, Any]:
    dashboard = _read_json(DEFAULT_DASHBOARD)
    regression = _read_json(DEFAULT_REGRESSION)
    gate_review = _read_json(DEFAULT_GATE_REVIEW)
    fallback_smoke = _read_json(DEFAULT_FALLBACK_SMOKE)
    brainstorm_lines = _lines(DEFAULT_BRAINSTORM)
    next_candidates = _brainstorm_candidates(brainstorm_lines)

    one_line = _one_line(dashboard) or "CHECK | dashboard=missing"
    blocking = [str(x) for x in list(regression.get("blocking_issues") or [])]
    permit_integrity_ok = bool(((dashboard.get("permit_integrity") or {}).get("ok", True)))
    partner_api_ok = bool(((dashboard.get("partner_api_contract_smoke") or {}).get("ok")))
    browser_ok = bool(((dashboard.get("browser_smoke") or {}).get("ok")))
    secure_ok = bool(((dashboard.get("secure_stack") or {}).get("ok")))
    gate_recommendation = str(gate_review.get("recommendation") or "").strip() or "unknown"
    gate_share_pct = ((gate_review.get("timing") or {}).get("partner_share_pct")) if isinstance(gate_review.get("timing"), dict) else None
    fallback_smoke_ok = bool(fallback_smoke.get("ok"))

    current_bottleneck = "partner API smoke 위치 결정"
    if gate_recommendation == "keep_in_publish_gate":
        current_bottleneck = "wp_surface_lab fallback bootstrap smoke 부재"
    elif gate_recommendation == "move_to_ops_loop":
        current_bottleneck = "publish gate 비용 과다"
    elif gate_recommendation == "keep_but_watch_cost":
        current_bottleneck = "partner API smoke 비용 감시 필요"

    if not partner_api_ok:
        current_bottleneck = "partner API contract 불일치"
    elif not browser_ok:
        current_bottleneck = "browser smoke 불안정"
    elif not secure_ok:
        current_bottleneck = "secure stack 실행 경로"
    elif not permit_integrity_ok:
        current_bottleneck = "permit generated HTML integrity"
    elif blocking:
        current_bottleneck = f"회귀 blocking issue {blocking[0]}"
    elif fallback_smoke_ok:
        current_bottleneck = "failure artifact가 아직 로컬 경로에만 남음"

    prompt_block = """너는 기능 추가자가 아니라 시스템 책임자다.
목표는 기능 수를 늘리는 것이 아니라 운영 변수와 오해 가능성을 줄이고, 재현 가능한 검증 경로를 고정하는 것이다.
아래 순서로만 판단하라.
1. 이 기능을 완전히 제거하면 무엇이 망가지는가.
2. 제거해도 안 망가지면 왜 아직 존재하는가.
3. 꼭 필요하다면 가장 작은 인터페이스는 무엇인가.
4. 운영자가 선택해야 하는 분기 수는 몇 개인가. 하나로 줄일 수 있는가.
5. smoke/regression 없이도 안전한가. 아니라면 배포 전에 어떤 자동 검증이 강제되어야 하는가.
6. 고객이 실제로 이해해야 하는 출력은 무엇인가. 많은 정보가 아니라 직접 의사결정에 필요한 정보인가.
7. 지금 병목은 코드 복잡성인가, 데이터 품질인가, 배포 동선인가, 설명 UX인가. 가장 큰 병목 하나만 먼저 친다.

추가 규율:
- 비교 기준은 현재 구현이 아니라 시장의 실제 의사결정 흐름이다.
- 총 거래가, 공제 활용분, 현금 정산액을 절대 섞지 않는다.
- public/private/partner가 서로 다른 규칙을 쓰면 버그로 간주한다.
- 설명 문구는 길게 쓰지 말고, 이유를 한 줄 칩이나 한 문장으로 압축한다.
- 실패 아티팩트는 재현 가능한 형태로 남겨야 하며, 로그만 남기고 끝내지 않는다."""

    musk_questions = [
        "무엇을 만들지보다 무엇을 지워야 하는가.",
        "운영자의 수동 판단이 남는 단계는 몇 개인가. 더 줄일 수 있는가.",
        "public/private/partner가 서로 다른 경로를 쓰는 이유가 실제로 존재하는가.",
        "고객이 실제로 이해해야 하는 값은 총 거래가, 현금 정산가, 공개 신뢰도 중 무엇인가.",
        "smoke 결과를 사람이 해석해야 한다면 아직 시스템 설계가 덜 끝난 것은 아닌가.",
    ]
    kill_list = [
        "수동 배포 분기",
        "중복 WordPress publish 로직",
        "smoke 입력 drift",
        "길지만 결론이 없는 결과 문구",
    ]
    force_multiplier_bets = [
        "public/private publish 단일 진입점",
        "post-publish verifier 자동화",
        "partner/live/private health contract 단일화",
        "결과 카드의 이유 칩 표준화",
    ]
    operator_loop = [
        "현재 one-line health를 읽고 빨간 항목 1개만 고른다.",
        "그 항목이 데이터 문제인지, UI 문제인지, smoke 문제인지 10분 안에 가설을 세운다.",
        "수정은 한 축만 건드린다. 동시에 여러 원인을 고치지 않는다.",
        "수정 후 `smoke -> regression -> publish gate` 순으로 다시 닫는다.",
        "남은 다음 병목 1개를 다시 고른다.",
    ]
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "packet_ready": True,
            "one_line_health": one_line,
            "blocking_issue_count": len(blocking),
            "current_bottleneck": current_bottleneck,
            "next_experiment_count": len(next_candidates[:5]),
            "critical_question_count": len(musk_questions),
            "gate_recommendation": gate_recommendation,
            "gate_partner_share_pct": gate_share_pct,
            "fallback_smoke_ok": fallback_smoke_ok,
        },
        "current_state": {
            "one_line_health": one_line,
            "regression_blocking_issues": blocking,
            "current_bottleneck": current_bottleneck,
        },
        "gate_decision": gate_review,
        "fallback_smoke": fallback_smoke,
        "first_principles_prompt": prompt_block,
        "musk_style_questions": musk_questions,
        "kill_list": kill_list,
        "force_multiplier_bets": force_multiplier_bets,
        "next_experiments": next_candidates[:5],
        "operator_loop": operator_loop,
        "decision": {
            "primary_focus": current_bottleneck,
            "secondary_focus": "특허/고도화보다 재현 가능한 판단 체계와 운영 자동 검증 고정",
        },
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    state = payload.get("current_state") if isinstance(payload.get("current_state"), dict) else {}
    gate = payload.get("gate_decision") if isinstance(payload.get("gate_decision"), dict) else {}
    gate_timing = gate.get("timing") if isinstance(gate.get("timing"), dict) else {}
    fallback_smoke = payload.get("fallback_smoke") if isinstance(payload.get("fallback_smoke"), dict) else {}
    fallback_timing = fallback_smoke.get("timing") if isinstance(fallback_smoke.get("timing"), dict) else {}
    lines = [
        "# AI Platform First-Principles Review",
        "",
        f"Updated: {payload.get('generated_at', '')} KST",
        "",
        "## Current State",
        f"- One-line health: `{state.get('one_line_health') or '(missing)'}`",
        f"- Regression blocking issues: `{', '.join(state.get('regression_blocking_issues') or []) or 'none'}`",
        f"- Current bottleneck: `{state.get('current_bottleneck') or '(missing)'}`",
        "",
        "## Gate Decision",
        f"- Recommendation: `{gate.get('recommendation') or '(missing)'}`",
        f"- Decision label: `{gate.get('decision_label') or '(missing)'}`",
        f"- Partner share: `{gate_timing.get('partner_share_pct')}`%",
        f"- Partner duration: `{gate_timing.get('partner_api_contract_smoke_sec')}` sec",
        "",
        "## Fallback Smoke",
        f"- Status: `{fallback_smoke.get('ok')}`",
        f"- Total duration: `{fallback_timing.get('total_duration_sec')}` sec",
        f"- Blocking issues: `{', '.join(fallback_smoke.get('blocking_issues') or []) or 'none'}`",
        "",
        "## First-Principles Prompt",
        "```text",
        str(payload.get("first_principles_prompt") or "").rstrip(),
        "```",
        "",
        "## Musk-Style Questions",
    ]
    for item in payload.get("musk_style_questions") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Kill List"])
    for item in payload.get("kill_list") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Force-Multiplier Bets"])
    for item in payload.get("force_multiplier_bets") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Experiments"])
    for item in payload.get("next_experiments") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Operator Loop"])
    for idx, item in enumerate(payload.get("operator_loop") or [], start=1):
        lines.append(f"{idx}. {item}")
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    lines.extend([
        "",
        "## Decision",
        f"- primary_focus: {decision.get('primary_focus') or '(missing)'}",
        f"- secondary_focus: {decision.get('secondary_focus') or '(missing)'}",
        "",
        "## Summary",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- blocking_issue_count: {summary.get('blocking_issue_count')}",
        f"- next_experiment_count: {summary.get('next_experiment_count')}",
        f"- gate_recommendation: {summary.get('gate_recommendation')}",
    ])
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a first-principles review for the SeoulMNA AI platform.")
    parser.add_argument("--json", default=str(DEFAULT_JSON))
    parser.add_argument("--md", default=str(DEFAULT_MD))
    args = parser.parse_args()
    json_path = Path(str(args.json)).resolve()
    md_path = Path(str(args.md)).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_review_payload()
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_path), "md": str(md_path)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
