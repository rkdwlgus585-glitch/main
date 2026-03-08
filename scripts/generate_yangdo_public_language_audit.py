#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "yangdo_calculator.py"
DEFAULT_JSON = ROOT / "logs" / "yangdo_public_language_audit_latest.json"
DEFAULT_MD = ROOT / "logs" / "yangdo_public_language_audit_latest.md"


@dataclass(frozen=True)
class PhraseRule:
    phrase_id: str
    phrase: str
    suggestion: str
    reason: str
    pattern: str | None = None


PHRASE_RULES: List[PhraseRule] = [
    PhraseRule("evidence_count_label", "근거 매물", "비슷한 사례", "사용자는 '근거'보다 '비슷한 사례'를 더 빨리 이해합니다."),
    PhraseRule("evidence_table_label", "근거 표", "비슷한 사례 표", "대표는 '근거 표'보다 '사례 표'를 더 쉽게 읽습니다."),
    PhraseRule("comparison_table_word", "비교표", "사례표", "무엇을 여는지 바로 보이게 해야 합니다."),
    PhraseRule("recommend_action_label", "추천 액션", "지금 하면 좋은 순서", "영어식 표현보다 바로 행동이 보이는 말이 낫습니다."),
    PhraseRule("range_first_label", "범위 우선 안내", "범위 먼저 보기", "결과 상태를 더 짧게 읽히게 해야 합니다."),
    PhraseRule(
        "confirm_later_label",
        "확인 후 안내",
        "먼저 확인 필요",
        "대기 상태를 더 명확히 보여줘야 합니다.",
        pattern=r"(?<!자세히 )확인 후 안내",
    ),
    PhraseRule("sample_needed_label", "표본 확인 필요", "사례 더 필요", "입력 보강이 필요한 상태를 쉬운 말로 보여줘야 합니다."),
    PhraseRule("settlement_label", "정산 해석", "정산 안내", "해석보다 안내가 더 직관적입니다."),
    PhraseRule("public_chip_prefix", "공개 ·", "상태를 바로 읽는 짧은 말", "칩 문구의 사무식 접두어를 줄여야 합니다."),
    PhraseRule("consult_mode_word", "상담형", "자세히 확인 후 안내", "전문 용어 대신 결과 상태를 바로 말해야 합니다."),
]


def _scan_lines(source_text: str, rules: List[PhraseRule]) -> List[Dict[str, Any]]:
    lines = str(source_text or "").splitlines()
    findings: List[Dict[str, Any]] = []
    for rule in rules:
        matched_lines: List[Dict[str, Any]] = []
        total_hits = 0
        compiled = re.compile(rule.pattern or re.escape(rule.phrase))
        for idx, line in enumerate(lines, start=1):
            count = len(list(compiled.finditer(line)))
            if count <= 0:
                continue
            total_hits += count
            matched_lines.append(
                {
                    "line": idx,
                    "count": count,
                    "snippet": line.strip(),
                }
            )
        if total_hits <= 0:
            continue
        findings.append(
            {
                "phrase_id": rule.phrase_id,
                "phrase": rule.phrase,
                "count": total_hits,
                "suggestion": rule.suggestion,
                "reason": rule.reason,
                "matches": matched_lines[:12],
            }
        )
    findings.sort(key=lambda row: (-int(row.get("count") or 0), str(row.get("phrase_id") or "")))
    return findings


def build_public_language_audit(*, source_text: str) -> Dict[str, Any]:
    findings = _scan_lines(source_text, PHRASE_RULES)
    jargon_total = sum(int(row.get("count") or 0) for row in findings)
    remaining_phrase_count = len(findings)
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "yangdo_public_language_audit_latest",
        "summary": {
            "packet_ready": True,
            "source_file": str(DEFAULT_SOURCE),
            "phrase_rule_count": len(PHRASE_RULES),
            "remaining_phrase_count": remaining_phrase_count,
            "jargon_total": jargon_total,
            "public_language_ready": jargon_total == 0,
        },
        "top_blockers": findings[:5],
        "findings": findings,
        "next_actions": [
            "공개 화면에서 먼저 보이는 카드, 칩, 버튼 라벨부터 생활 언어로 바꿉니다.",
            "같은 뜻의 표현은 한 가지 말로 통일해 대표가 다시 해석하지 않게 만듭니다.",
            "변경 후에는 계산기 HTML 회귀와 live smoke로 실제 노출 문구를 확인합니다.",
        ],
    }


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = dict(payload.get("summary") or {})
    blockers = list(payload.get("top_blockers") or [])
    lines = [
        "# Yangdo Public Language Audit",
        "",
        "## Summary",
        f"- phrase_rule_count: `{summary.get('phrase_rule_count', 0)}`",
        f"- remaining_phrase_count: `{summary.get('remaining_phrase_count', 0)}`",
        f"- jargon_total: `{summary.get('jargon_total', 0)}`",
        f"- public_language_ready: `{summary.get('public_language_ready', False)}`",
        "",
        "## Top Blockers",
    ]
    if not blockers:
        lines.append("- none")
    else:
        for item in blockers:
            lines.append(
                f"- `{item.get('phrase')}` x{item.get('count')}: "
                f"{item.get('suggestion')} / {item.get('reason')}"
            )
    lines.extend(["", "## Next Actions"])
    for item in payload.get("next_actions") or []:
        lines.append(f"- {item}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit remaining public-facing jargon in the yangdo calculator.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    source_text = args.source.expanduser().resolve().read_text(encoding="utf-8")
    payload = build_public_language_audit(source_text=source_text)

    json_output = args.json_output.expanduser().resolve()
    md_output = args.md_output.expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
