from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PERMIT_INPUT = ROOT / "logs" / "permit_next_action_brainstorm_latest.json"
DEFAULT_YANGDO_INPUT = ROOT / "logs" / "yangdo_next_action_brainstorm_latest.json"
DEFAULT_PERMIT_PROMPT_DOC = ROOT / "docs" / "permit_critical_thinking_prompt.md"
DEFAULT_YANGDO_PROMPT_DOC = ROOT / "docs" / "yangdo_critical_thinking_prompt.md"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "founder_mode_prompt_bundle_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "founder_mode_prompt_bundle_latest.md"


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
    return path.read_text(encoding="utf-8")


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _priority_rank(value: Any) -> int:
    mapping = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return mapping.get(_safe_str(value).upper(), 9)


def _doc_excerpt(text: str, limit: int = 6) -> str:
    lines = [line.rstrip() for line in str(text or "").splitlines() if line.strip()]
    return "\n".join(lines[:limit])


def _system_pressure(system: str, report: Dict[str, Any]) -> int:
    summary = dict(report.get("summary") or {})
    if system == "permit":
        return (
            _safe_int(summary.get("runtime_failed_case_total")) * 1000
            + _safe_int(summary.get("case_release_guard_failed_total")) * 600
            + (0 if bool(summary.get("case_release_guard_ready")) else 80)
            + (0 if bool(summary.get("story_contract_surface_ready")) else 50)
            + (0 if bool(summary.get("runtime_review_preset_surface_ready")) else 30)
        )
    return (
        _safe_int(summary.get("precision_failed_count")) * 1000
        + _safe_int(summary.get("qa_failed_count")) * 800
        + _safe_int(summary.get("diversity_failed_count")) * 700
        + _safe_int(summary.get("alignment_issue_count")) * 900
        + _safe_int(summary.get("one_or_less_display_total"))
        + (_safe_int(summary.get("zero_display_total")) * 2)
        + max(0, 6 - _safe_int(summary.get("special_sector_scenario_total"))) * 40
    )


def _make_lane_snapshot(system: str, lane_type: str, lane: Dict[str, Any], report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "system": system,
        "lane_type": lane_type,
        "id": _safe_str(lane.get("id")),
        "priority": _safe_str(lane.get("priority")),
        "track": _safe_str(lane.get("track")),
        "title": _safe_str(lane.get("title")),
        "current_gap": _safe_str(lane.get("current_gap")),
        "evidence": _safe_str(lane.get("evidence") or lane.get("why_now")),
        "proposed_next_step": _safe_str(lane.get("proposed_next_step")),
        "success_metric": _safe_str(lane.get("success_metric")),
        "pressure_score": _system_pressure(system, report),
    }


def _sort_key(item: Dict[str, Any]) -> tuple[int, int, int, str]:
    lane_type_penalty = 0 if _safe_str(item.get("lane_type")) == "execution" else 1
    return (
        _priority_rank(item.get("priority")),
        lane_type_penalty,
        -_safe_int(item.get("pressure_score")),
        _safe_str(item.get("system")),
    )


def _build_unified_execution_prompt(primary: Dict[str, Any], secondary: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "너는 서울MNA 전체 제품 흐름을 동시에 책임지는 총괄 실행자다.",
            f"이번 배치의 1순위 실행 lane은 {primary.get('system')} / {primary.get('title')} 이다.",
            (
                f"동시에 병렬 브레인스토밍 lane은 {secondary.get('system')} / {secondary.get('title')} 으로 둔다."
                if secondary
                else "병렬 브레인스토밍 lane은 비워 둔다."
            ),
            "머스크식으로 1차원 분해하라. 가장 큰 병목 하나만 먼저 없애고, 나머지는 순서를 다시 매겨라.",
            "UI 문구만 고치지 말고 입력 시간, 결과 이해도, 전달 속도, 회귀 안전성 중 최소 두 개를 같이 개선하라.",
            "산출 형식은 병목, 증거, 수정, 검증, 다음 우선순위로 고정한다.",
        ]
    )


def _build_parallel_brainstorm_prompt(primary: Dict[str, Any], secondary: Dict[str, Any], next_actions: List[Dict[str, Any]]) -> str:
    candidate_lines = [
        f"- {item.get('system')} / {item.get('title')} / next {item.get('proposed_next_step')}"
        for item in next_actions[:4]
    ]
    return "\n".join(
        [
            f"실행 lane은 {primary.get('system')} / {primary.get('title')} 이다.",
            (
                f"병렬 검토 lane은 {secondary.get('system')} / {secondary.get('title')} 이다."
                if secondary
                else "병렬 검토 lane은 없다."
            ),
            "다음 후보를 압축하라. 아이디어를 늘리지 말고 바로 배치 가능한 것만 남겨라.",
            "질문: 대표의 입력 시간을 줄이는가, 결과 오해를 줄이는가, 전달 동선을 줄이는가, 기존 테스트로 바로 검증 가능한가.",
            *candidate_lines,
        ]
    )


def _build_first_principles_prompt() -> str:
    return "\n".join(
        [
            "지금 보이는 문제를 관성적으로 다루지 마라.",
            "무엇이 사실이고, 무엇이 가설이며, 무엇이 단순한 익숙함인지 분리하라.",
            "없어도 되는 단계, 문구, 입력칸은 제거 대상으로 보고, 꼭 필요한 축은 더 강하게 드러내라.",
            "한 번의 수정으로 입력 부담과 전달 속도를 동시에 줄이지 못하면 우선순위를 낮춰라.",
        ]
    )


def _combined_founder_questions(permit_report: Dict[str, Any], yangdo_report: Dict[str, Any]) -> List[str]:
    ordered: List[str] = []
    for report in (permit_report, yangdo_report):
        prompts = dict(report.get("critical_prompts") or {})
        for item in list(prompts.get("founder_mode_questions") or []):
            text = _safe_str(item)
            if text and text not in ordered:
                ordered.append(text)
    ordered.extend(
        [
            "이 배치가 실제 사용자 시간을 줄이는가, 아니면 설명만 늘리는가.",
            "이 배치가 다음 상담 전달 동선을 더 짧게 만드는가.",
        ]
    )
    deduped: List[str] = []
    for item in ordered:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _anti_patterns() -> List[str]:
    return [
        "문구만 다듬고 입력 동선은 그대로 두는 개선",
        "필수와 선택 정보를 다시 섞어 버리는 개선",
        "브라우저 스모크 없이 전달/추천 흐름을 바꾸는 수정",
        "특수 업종 분할·합병 규칙을 예외 처리로만 숨기는 설계",
    ]


def _execution_checklist(primary: Dict[str, Any], secondary: Dict[str, Any]) -> List[str]:
    lane_id = _safe_str(primary.get("id"))
    checklist: List[str]
    if lane_id == "single_recommendation_autoloop":
        checklist = [
            "Instrument zero/one-recommendation states with ranked fallback CTAs instead of a single generic recovery button.",
            "Do not expose price or price-band hints inside recommendation cards; keep the recommendation surface focused on industry, performance, and fit signals.",
            "Verify each fallback CTA lands on the intended wizard step, field focus target, and visible highlight state.",
            "Lock one-or-less recommendation behavior in smoke/runtime tests before expanding copy or layout polish.",
        ]
    elif lane_id == "preset_story_release_guard":
        checklist = [
            "Lock runtime preset markers and story contract markers in one release-level parity guard.",
            "Fail the release when preset/story coverage drifts instead of allowing manual review to catch it later.",
            "Expose guard pass/fail counts in release-facing summaries so operators do not need raw JSON to judge readiness.",
        ]
    else:
        checklist = [
            "Reduce user input time, result interpretation time, and delivery friction in the same patch.",
            "Bind the primary lane to a measurable regression or smoke gate before polishing secondary surfaces.",
            "Keep the next batch small enough that the success metric can move in one execution cycle.",
        ]
    if secondary:
        checklist.append(
            f"Keep `{_safe_str(secondary.get('system'))}/{_safe_str(secondary.get('id'))}` in parallel-brainstorm mode only until the primary success metric moves."
        )
    return checklist


def _shipping_gates(primary: Dict[str, Any], secondary: Dict[str, Any]) -> List[str]:
    gates = [
        "No copy-only patch: every batch must change runtime behavior, QA coverage, or operator delivery leverage.",
        f"Primary lane success metric must show movement: {_safe_str(primary.get('success_metric')) or 'metric not declared'}.",
        "Browser smoke and targeted regression tests must pass on the changed path before the lane can be considered closed.",
    ]
    if _safe_str(primary.get("id")) == "single_recommendation_autoloop":
        gates.append("Recommendation cards must not expose price figures or price-band wording.")
    if secondary:
        gates.append(
            f"Do not switch focus to `{_safe_str(secondary.get('id'))}` unless `{_safe_str(primary.get('id'))}` is green or demonstrably blocked."
        )
    return gates


def build_bundle(
    *,
    permit_report: Dict[str, Any],
    yangdo_report: Dict[str, Any],
    permit_prompt_doc: str = "",
    yangdo_prompt_doc: str = "",
) -> Dict[str, Any]:
    permit_execution = _make_lane_snapshot(
        "permit",
        "execution",
        dict(permit_report.get("current_execution_lane") or {}),
        permit_report,
    )
    permit_parallel = _make_lane_snapshot(
        "permit",
        "parallel",
        dict(permit_report.get("parallel_brainstorm_lane") or {}),
        permit_report,
    )
    yangdo_execution = _make_lane_snapshot(
        "yangdo",
        "execution",
        dict(yangdo_report.get("current_execution_lane") or {}),
        yangdo_report,
    )
    yangdo_parallel = _make_lane_snapshot(
        "yangdo",
        "parallel",
        dict(yangdo_report.get("parallel_brainstorm_lane") or {}),
        yangdo_report,
    )
    candidates = [
        item
        for item in [permit_execution, permit_parallel, yangdo_execution, yangdo_parallel]
        if _safe_str(item.get("id"))
    ]
    ordered = sorted(candidates, key=_sort_key)
    primary = dict(ordered[0]) if ordered else {}
    secondary = {}
    if primary:
        for item in ordered[1:]:
            if _safe_str(item.get("system")) != _safe_str(primary.get("system")):
                secondary = dict(item)
                break
        if not secondary and len(ordered) > 1:
            secondary = dict(ordered[1])

    permit_summary = dict(permit_report.get("summary") or {})
    yangdo_summary = dict(yangdo_report.get("summary") or {})
    founder_questions = _combined_founder_questions(permit_report, yangdo_report)
    next_actions = ordered[:4]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "founder_mode_prompt_bundle_latest",
        "summary": {
            "primary_system": _safe_str(primary.get("system")),
            "primary_lane_id": _safe_str(primary.get("id")),
            "parallel_system": _safe_str(secondary.get("system")),
            "parallel_lane_id": _safe_str(secondary.get("id")),
            "permit_pressure_score": _system_pressure("permit", permit_report),
            "yangdo_pressure_score": _system_pressure("yangdo", yangdo_report),
            "permit_runtime_failed_case_total": _safe_int(permit_summary.get("runtime_failed_case_total")),
            "yangdo_one_or_less_display_total": _safe_int(yangdo_summary.get("one_or_less_display_total")),
            "yangdo_special_sector_scenario_total": _safe_int(yangdo_summary.get("special_sector_scenario_total")),
            "permit_prompt_doc_ready": bool(str(permit_prompt_doc or "").strip()),
            "yangdo_prompt_doc_ready": bool(str(yangdo_prompt_doc or "").strip()),
        },
        "primary_execution": primary,
        "parallel_brainstorm": secondary,
        "next_actions": next_actions,
        "unified_prompts": {
            "execution_prompt": _build_unified_execution_prompt(primary, secondary),
            "parallel_brainstorm_prompt": _build_parallel_brainstorm_prompt(primary, secondary, next_actions),
            "first_principles_prompt": _build_first_principles_prompt(),
        },
        "execution_checklist": _execution_checklist(primary, secondary),
        "shipping_gates": _shipping_gates(primary, secondary),
        "founder_mode_questions": founder_questions,
        "anti_patterns": _anti_patterns(),
        "source_packets": {
            "permit": {
                "current_execution_lane": permit_execution,
                "parallel_brainstorm_lane": permit_parallel,
                "prompt_doc_excerpt": _doc_excerpt(permit_prompt_doc),
            },
            "yangdo": {
                "current_execution_lane": yangdo_execution,
                "parallel_brainstorm_lane": yangdo_parallel,
                "prompt_doc_excerpt": _doc_excerpt(yangdo_prompt_doc),
            },
        },
    }


def render_markdown(bundle: Dict[str, Any]) -> str:
    summary = dict(bundle.get("summary") or {})
    primary = dict(bundle.get("primary_execution") or {})
    secondary = dict(bundle.get("parallel_brainstorm") or {})
    prompts = dict(bundle.get("unified_prompts") or {})
    lines = [
        "# Founder Mode Prompt Bundle",
        "",
        "## Summary",
        f"- primary_system: `{summary.get('primary_system', '')}`",
        f"- primary_lane_id: `{summary.get('primary_lane_id', '')}`",
        f"- parallel_system: `{summary.get('parallel_system', '')}`",
        f"- parallel_lane_id: `{summary.get('parallel_lane_id', '')}`",
        f"- permit_pressure_score: `{summary.get('permit_pressure_score', 0)}`",
        f"- yangdo_pressure_score: `{summary.get('yangdo_pressure_score', 0)}`",
        f"- permit_runtime_failed_case_total: `{summary.get('permit_runtime_failed_case_total', 0)}`",
        f"- yangdo_one_or_less_display_total: `{summary.get('yangdo_one_or_less_display_total', 0)}`",
        f"- yangdo_special_sector_scenario_total: `{summary.get('yangdo_special_sector_scenario_total', 0)}`",
        "",
        "## Primary Execution",
        f"- system: `{primary.get('system', '')}`",
        f"- lane: `{primary.get('id', '')}`",
        f"- title: {primary.get('title', '')}",
        f"- current_gap: {primary.get('current_gap', '')}",
        f"- proposed_next_step: {primary.get('proposed_next_step', '')}",
        "",
        "## Parallel Brainstorm",
        f"- system: `{secondary.get('system', '')}`",
        f"- lane: `{secondary.get('id', '')}`",
        f"- title: {secondary.get('title', '')}",
        f"- current_gap: {secondary.get('current_gap', '')}",
        f"- proposed_next_step: {secondary.get('proposed_next_step', '')}",
        "",
        "## Unified Execution Prompt",
        "```text",
        _safe_str(prompts.get("execution_prompt")),
        "```",
        "",
        "## Parallel Brainstorm Prompt",
        "```text",
        _safe_str(prompts.get("parallel_brainstorm_prompt")),
        "```",
        "",
        "## First-Principles Prompt",
        "```text",
        _safe_str(prompts.get("first_principles_prompt")),
        "```",
        "",
        "## Execution Checklist",
    ]
    for item in list(bundle.get("execution_checklist") or []):
        lines.append(f"- {item}")
    lines.extend(["", "## Shipping Gates"])
    for item in list(bundle.get("shipping_gates") or []):
        lines.append(f"- {item}")
    lines.extend(["", "## Founder Mode Questions"])
    for item in list(bundle.get("founder_mode_questions") or []):
        lines.append(f"- {item}")
    lines.extend(["", "## Anti-Patterns"])
    for item in list(bundle.get("anti_patterns") or []):
        lines.append(f"- {item}")
    lines.extend(["", "## Next Actions"])
    for item in list(bundle.get("next_actions") or []):
        if not isinstance(item, dict):
            continue
        lines.append(
            f"- `{item.get('system', '')}/{item.get('id', '')}` [{item.get('priority', '')}] "
            f"{item.get('title', '')} / next {item.get('proposed_next_step', '')}"
        )
    source_packets = dict(bundle.get("source_packets") or {})
    for system in ("permit", "yangdo"):
        packet = dict(source_packets.get(system) or {})
        excerpt = _safe_str(packet.get("prompt_doc_excerpt"))
        if excerpt:
            lines.extend(
                [
                    "",
                    f"## {system.title()} Prompt Doc Excerpt",
                    "```text",
                    excerpt,
                    "```",
                ]
            )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the unified founder-mode prompt bundle.")
    parser.add_argument("--permit-input", default=str(DEFAULT_PERMIT_INPUT))
    parser.add_argument("--yangdo-input", default=str(DEFAULT_YANGDO_INPUT))
    parser.add_argument("--permit-prompt-doc", default=str(DEFAULT_PERMIT_PROMPT_DOC))
    parser.add_argument("--yangdo-prompt-doc", default=str(DEFAULT_YANGDO_PROMPT_DOC))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    bundle = build_bundle(
        permit_report=_load_json(Path(args.permit_input).expanduser().resolve()),
        yangdo_report=_load_json(Path(args.yangdo_input).expanduser().resolve()),
        permit_prompt_doc=_load_text(Path(args.permit_prompt_doc).expanduser().resolve()),
        yangdo_prompt_doc=_load_text(Path(args.yangdo_prompt_doc).expanduser().resolve()),
    )

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(bundle), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
