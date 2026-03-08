#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRECISION_INPUT = ROOT / "logs" / "yangdo_recommendation_precision_matrix_latest.json"
DEFAULT_QA_INPUT = ROOT / "logs" / "yangdo_recommendation_qa_matrix_latest.json"
DEFAULT_DIVERSITY_INPUT = ROOT / "logs" / "yangdo_recommendation_diversity_audit_latest.json"
DEFAULT_ALIGNMENT_INPUT = ROOT / "logs" / "yangdo_recommendation_alignment_audit_latest.json"
DEFAULT_COMPARABLE_INPUT = ROOT / "logs" / "yangdo_comparable_selection_overall_latest.json"
DEFAULT_UX_INPUT = ROOT / "logs" / "yangdo_recommendation_ux_packet_latest.json"
DEFAULT_SERVICE_COPY_INPUT = ROOT / "logs" / "yangdo_service_copy_packet_latest.json"
DEFAULT_PROMPT_DOC_INPUT = ROOT / "docs" / "yangdo_critical_thinking_prompt.md"
DEFAULT_RUNTIME_SOURCE = ROOT / "yangdo_calculator.py"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "yangdo_next_action_brainstorm_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "yangdo_next_action_brainstorm_latest.md"


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


def _doc_excerpt(prompt_doc: str, limit: int = 8) -> str:
    lines = [line.rstrip() for line in str(prompt_doc or "").splitlines() if line.strip()]
    return "\n".join(lines[:limit])


def _load_runtime_flags(source_text: str) -> Dict[str, bool]:
    text = str(source_text or "")
    return {
        "autoloop_ready": all(
            marker in text
            for marker in [
                "recommendAutoLoopFieldId",
                "scheduleRecommendAutoLoopEstimate",
                "maybeRunRecommendAutoLoop",
            ]
        ),
        "zero_recovery_ready": "recommend-panel-followup-secondary-action" in text,
    }


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


def _safe_bool(value: Any) -> bool:
    return bool(value)


def _make_item(
    *,
    item_id: str,
    priority: str,
    track: str,
    title: str,
    current_gap: str,
    evidence: str,
    proposed_next_step: str,
    success_metric: str,
    parallelizable_with: List[str],
) -> Dict[str, Any]:
    return {
        "id": item_id,
        "priority": priority,
        "track": track,
        "title": title,
        "current_gap": current_gap,
        "evidence": evidence,
        "proposed_next_step": proposed_next_step,
        "success_metric": success_metric,
        "parallelizable_with": parallelizable_with,
    }


def _select_execution_lane(
    *,
    regression_fail_total: int,
    alignment_issue_count: int,
    one_or_less_display_total: int,
    special_sector_scenario_total: int,
    zero_display_total: int,
    autoloop_ready: bool,
) -> str:
    if regression_fail_total > 0 or alignment_issue_count > 0:
        return "recommendation_regression_repair"
    if one_or_less_display_total >= 200 and not autoloop_ready:
        return "single_recommendation_autoloop"
    if special_sector_scenario_total < 6:
        return "special_sector_split_precision_expansion"
    if zero_display_total > 0:
        return "zero_display_recovery_guard"
    return "public_language_normalization"


def _select_parallel_lane(
    *,
    primary_id: str,
    one_or_less_display_total: int,
    special_sector_scenario_total: int,
    zero_display_total: int,
    prompt_doc_ready: bool,
    autoloop_ready: bool,
) -> str:
    candidates: List[str] = []
    if special_sector_scenario_total < 6:
        candidates.append("special_sector_split_precision_expansion")
    if one_or_less_display_total >= 200 and not autoloop_ready:
        candidates.append("single_recommendation_autoloop")
    if zero_display_total > 0:
        candidates.append("zero_display_recovery_guard")
    candidates.append("public_language_normalization")
    if prompt_doc_ready:
        candidates.append("prompt_loop_operationalization")
    for candidate in candidates:
        if candidate != primary_id:
            return candidate
    return ""


def _build_execution_prompt(
    *,
    primary_title: str,
    regression_fail_total: int,
    one_or_less_display_total: int,
    zero_display_total: int,
    special_sector_scenario_total: int,
    avg_display_neighbors: float,
) -> str:
    return "\n".join(
        [
            "너는 서울MNA 양도가 시스템의 운영 책임자다.",
            f"이번 배치의 주 병목은 '{primary_title}'이다.",
            (
                "현황: "
                f"회귀 실패 {regression_fail_total}건, 추천 1건 이하 {one_or_less_display_total}건, "
                f"추천 0건 {zero_display_total}건, 특수 업종 시나리오 {special_sector_scenario_total}건, "
                f"평균 노출 비교매물 {avg_display_neighbors:.2f}건."
            ),
            "먼저 병목을 입력 문제, 추천 점수 문제, 결과 배치 문제, 후속 CTA 문제로 분해하라.",
            "문구 추가보다 실제 동작 개선을 우선한다. 자동 재계산, 입력 복귀, 보강 CTA, 추천 카드 배치를 먼저 본다.",
            "전기/정보통신/소방 분할·합병 규칙은 입력, 결과, 추천 설명에서 같은 메시지로 보이게 유지한다.",
            "수정 후에는 추천 QA, 정밀도, 다양성, 공개 계약, 서비스 UX를 모두 다시 닫는다.",
        ]
    )


def _build_brainstorm_prompt(primary_title: str) -> str:
    return "\n".join(
        [
            f"현재 실행 lane은 '{primary_title}'이다.",
            "다음 배치를 위한 후보는 아래 기준을 모두 통과한 것만 올린다.",
            "1. 입력 시간 또는 판단 시간을 실제로 줄이는가.",
            "2. 추천 설명을 더 해석 가능하게 만드는가.",
            "3. 특수 업종 규칙의 오해 가능성을 낮추는가.",
            "4. 기존 테스트와 운영 아티팩트로 바로 검증할 수 있는가.",
            "조건을 만족하지 못하면 아이디어로 남기지 말고 보류한다.",
        ]
    )


def _build_first_principles_prompt(primary_title: str) -> str:
    return "\n".join(
        [
            f"'{primary_title}'를 다시 1차 원리로 분해하라.",
            "추천이 약하게 보이는 이유가 데이터 부족인지, 필터 과잉인지, 설명 부족인지, 후속 CTA 설계 문제인지 분리한다.",
            "없어도 되는 단계는 제거하고, 남겨야 하는 단계만 가장 작은 인터페이스로 다시 고정한다.",
            "전기/정보통신/소방 분할·합병 규칙은 예외가 아니라 핵심 계약으로 취급한다.",
            "이번 배치에서는 입력 부담, 결과 이해도, 후속 행동 유도 중 최소 두 축을 함께 개선한다.",
        ]
    )


def _founder_mode_questions() -> List[str]:
    return [
        "이 수정이 실제 입력 시간 또는 판단 시간을 줄이는가.",
        "추천 1건 또는 0건 상황에서 다음 행동이 충분히 빠르게 이어지는가.",
        "특수 업종 분할·합병 리스크가 결과와 설명에 동시에 반영되는가.",
        "이번 수정은 테스트와 live 시나리오로 바로 검증 가능한가.",
    ]


def build_brainstorm(
    *,
    precision_matrix: Dict[str, Any],
    qa_matrix: Dict[str, Any],
    diversity_audit: Dict[str, Any],
    alignment_audit: Dict[str, Any],
    comparable_selection_overall: Dict[str, Any],
    ux_packet: Dict[str, Any] | None = None,
    service_copy_packet: Dict[str, Any] | None = None,
    prompt_doc: str = "",
    runtime_source_text: str = "",
) -> Dict[str, Any]:
    precision_summary = dict(precision_matrix.get("summary") or {})
    qa_summary = dict(qa_matrix.get("summary") or {})
    diversity_summary = dict(diversity_audit.get("summary") or {})
    alignment_summary = dict(alignment_audit.get("summary") or {})
    ux_summary = dict((ux_packet or {}).get("summary") or {})
    service_copy_summary = dict((service_copy_packet or {}).get("summary") or {})
    precision_sector_groups = dict(precision_summary.get("sector_groups") or {})
    balance_excluded_sector = dict(precision_sector_groups.get("balance_excluded_sector") or {})

    precision_failed_count = _safe_int(precision_summary.get("failed_count"))
    qa_failed_count = _safe_int(qa_summary.get("failed_count"))
    diversity_failed_count = _safe_int(diversity_summary.get("failed_count"))
    alignment_issue_count = _safe_int(alignment_summary.get("issue_count"))
    regression_fail_total = precision_failed_count + qa_failed_count + diversity_failed_count + alignment_issue_count
    special_sector_scenario_total = _safe_int(balance_excluded_sector.get("scenario_count"))
    one_or_less_display_total = _safe_int(comparable_selection_overall.get("records_one_or_less_display"))
    zero_display_total = _safe_int(comparable_selection_overall.get("records_zero_display"))
    avg_display_neighbors = _safe_float(comparable_selection_overall.get("avg_display_neighbors"))
    prompt_doc_ready = bool(str(prompt_doc or "").strip())
    prompt_doc_excerpt = _doc_excerpt(prompt_doc)
    public_copy_ready = _safe_bool(service_copy_summary.get("service_copy_ready"))
    ux_packet_ready = _safe_bool(ux_summary.get("packet_ready"))
    runtime_flags = _load_runtime_flags(runtime_source_text)
    autoloop_ready = _safe_bool(runtime_flags.get("autoloop_ready"))
    zero_recovery_ready = _safe_bool(runtime_flags.get("zero_recovery_ready"))

    brainstorm_items = [
        _make_item(
            item_id="recommendation_regression_repair",
            priority="P0",
            track="execution",
            title="회귀 실패 우선 복구",
            current_gap=(
                f"정밀도/QA/다양성/정렬 감사에서 총 {regression_fail_total}건의 적색이 남아 있으면 "
                "새 기능을 올릴수록 추천 흐름 신뢰도가 더 흔들린다."
            ),
            evidence=(
                f"precision_failed={precision_failed_count}, qa_failed={qa_failed_count}, "
                f"diversity_failed={diversity_failed_count}, alignment_issue={alignment_issue_count}"
            ),
            proposed_next_step="실패 시나리오를 먼저 고치고 추천, 결과, 배포 회귀를 녹색으로 되돌린다.",
            success_metric="precision/qa/diversity failed_count 0, alignment issue_count 0",
            parallelizable_with=["single_recommendation_autoloop", "special_sector_split_precision_expansion"],
        ),
        _make_item(
            item_id="single_recommendation_autoloop",
            priority="P1",
            track="execution",
            title="추천 1건 이하 반자동 보강 루프",
            current_gap=(
                f"추천이 1건 이하로 끝나는 레코드가 {one_or_less_display_total}건이고, "
                f"0건인 경우도 {zero_display_total}건이라 사용자는 다음 행동을 스스로 찾기 어렵다."
            ),
            evidence=(
                f"records_one_or_less_display={one_or_less_display_total}, "
                f"records_zero_display={zero_display_total}, avg_display_neighbors={avg_display_neighbors:.2f}"
            ),
            proposed_next_step="단일 추천 상태에서 보강 버튼, 입력 복귀, 자동 재계산을 하나의 연속 동작으로 묶는다.",
            success_metric="single-recommendation and zero-display runtime scenarios pass with direct follow-up actions",
            parallelizable_with=["special_sector_split_precision_expansion", "public_language_normalization", "zero_display_recovery_guard"],
        ),
        _make_item(
            item_id="special_sector_split_precision_expansion",
            priority="P1",
            track="quality",
            title="전기·소방·통신 분할·합병 정밀도 확장",
            current_gap=(
                f"특수 업종 시나리오가 {special_sector_scenario_total}건이면 분할·합병, 최근 3년 실적, 자본금 조합을 설명하기엔 부족하다."
            ),
            evidence=f"balance_excluded_sector scenario_count={special_sector_scenario_total}",
            proposed_next_step="전기·정보통신·소방의 포괄/분할 조합을 최소 6개 이상으로 늘리고 추천 설명까지 같이 검증한다.",
            success_metric="special-sector scenario_count >= 6 and all special-sector regression tests green",
            parallelizable_with=["single_recommendation_autoloop", "public_language_normalization", "prompt_loop_operationalization"],
        ),
        _make_item(
            item_id="public_language_normalization",
            priority="P2",
            track="product",
            title="결과·추천 문구 생활 언어화",
            current_gap="정책과 계약은 맞아도 사용자가 결과를 즉시 행동으로 옮길 수 있을 만큼 쉬운 문구는 아직 부족하다.",
            evidence=(
                f"service_copy_ready={public_copy_ready}, ux_packet_ready={ux_packet_ready}, "
                f"precision_label_count={_safe_int(service_copy_summary.get('precision_label_count'))}"
            ),
            proposed_next_step="가격 계산이 아니라 시장 적합도 해석으로 읽히도록 CTA와 결과 카피를 다시 정리한다.",
            success_metric="public UI smoke shows only plain-language labels and no technical helper wording",
            parallelizable_with=["single_recommendation_autoloop", "special_sector_split_precision_expansion"],
        ),
        _make_item(
            item_id="zero_display_recovery_guard",
            priority="P2",
            track="quality",
            title="추천 0건 fallback 복구 가드",
            current_gap=f"비교매물이 0건인 케이스가 {zero_display_total}건이라 fallback CTA의 순서와 문구가 제품 신뢰에 직접 영향을 준다.",
            evidence=f"records_zero_display={zero_display_total}",
            proposed_next_step="0건 케이스를 별도 회귀로 고정하고 보강 입력과 상담 CTA의 노출 순서를 계약으로 묶는다.",
            success_metric="zero-display fallback scenarios pass and publish the intended CTA order",
            parallelizable_with=["single_recommendation_autoloop", "public_language_normalization"],
        ),
        _make_item(
            item_id="prompt_loop_operationalization",
            priority="P2",
            track="research",
            title="비판적 사고 프롬프트 운영 패킷 유지",
            current_gap="프롬프트 문서가 있어도 최신 로그와 연결되지 않으면 다음 액션 선정이 다시 감에 의존하게 된다.",
            evidence=f"prompt_doc_ready={prompt_doc_ready}",
            proposed_next_step="프롬프트 문서와 최신 추천 로그를 함께 읽는 next-action packet을 배치 산출물로 유지한다.",
            success_metric="latest JSON/MD brainstorm packet exists and MASTERPLAN points to it",
            parallelizable_with=["special_sector_split_precision_expansion", "public_language_normalization"],
        ),
    ]

    primary_id = _select_execution_lane(
        regression_fail_total=regression_fail_total,
        alignment_issue_count=alignment_issue_count,
        one_or_less_display_total=one_or_less_display_total,
        special_sector_scenario_total=special_sector_scenario_total,
        zero_display_total=zero_display_total,
        autoloop_ready=autoloop_ready,
    )
    primary_execution = next((item for item in brainstorm_items if item.get("id") == primary_id), {})
    parallel_id = _select_parallel_lane(
        primary_id=primary_id,
        one_or_less_display_total=one_or_less_display_total,
        special_sector_scenario_total=special_sector_scenario_total,
        zero_display_total=zero_display_total,
        prompt_doc_ready=prompt_doc_ready,
        autoloop_ready=autoloop_ready,
    )
    primary_parallel = next((item for item in brainstorm_items if item.get("id") == parallel_id), {})

    execution_prompt = _build_execution_prompt(
        primary_title=str(primary_execution.get("title") or primary_id),
        regression_fail_total=regression_fail_total,
        one_or_less_display_total=one_or_less_display_total,
        zero_display_total=zero_display_total,
        special_sector_scenario_total=special_sector_scenario_total,
        avg_display_neighbors=avg_display_neighbors,
    )
    brainstorm_prompt = _build_brainstorm_prompt(str(primary_execution.get("title") or primary_id))
    first_principles_prompt = _build_first_principles_prompt(str(primary_execution.get("title") or primary_id))

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "packet_id": "yangdo_next_action_brainstorm_latest",
        "summary": {
            "precision_scenario_count": _safe_int(precision_summary.get("scenario_count")),
            "precision_failed_count": precision_failed_count,
            "qa_scenario_count": _safe_int(qa_summary.get("scenario_count")),
            "qa_failed_count": qa_failed_count,
            "diversity_scenario_count": _safe_int(diversity_summary.get("scenario_count")),
            "diversity_failed_count": diversity_failed_count,
            "alignment_issue_count": alignment_issue_count,
            "one_or_less_display_total": one_or_less_display_total,
            "zero_display_total": zero_display_total,
            "avg_display_neighbors": round(avg_display_neighbors, 4),
            "special_sector_scenario_total": special_sector_scenario_total,
            "prompt_doc_ready": prompt_doc_ready,
            "service_copy_ready": public_copy_ready,
            "ux_packet_ready": ux_packet_ready,
            "autoloop_ready": autoloop_ready,
            "zero_recovery_ready": zero_recovery_ready,
            "all_green": regression_fail_total == 0,
        },
        "current_execution_lane": primary_execution,
        "parallel_brainstorm_lane": primary_parallel,
        "execution_prompt": execution_prompt,
        "brainstorm_prompt": brainstorm_prompt,
        "first_principles_prompt": first_principles_prompt,
        "critical_prompts": {
            "execution_prompt": execution_prompt,
            "brainstorm_prompt": brainstorm_prompt,
            "first_principles_prompt": first_principles_prompt,
            "founder_mode_questions": _founder_mode_questions(),
            "prompt_doc_excerpt": prompt_doc_excerpt,
            "self_questions": [
                "이 수정이 실제 입력 시간 또는 판단 시간을 줄이는가.",
                "이 수정이 추천 설명을 더 해석 가능하게 만드는가.",
                "이 수정이 특수 업종 규칙 오해 가능성을 낮추는가.",
                "이 수정 결과를 기존 테스트와 운영 아티팩트로 즉시 검증할 수 있는가.",
            ],
        },
        "brainstorm_items": brainstorm_items,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    execution_lane = dict(report.get("current_execution_lane") or {})
    parallel_lane = dict(report.get("parallel_brainstorm_lane") or {})
    prompts = dict(report.get("critical_prompts") or {})
    lines = [
        "# Yangdo Next Action Brainstorm",
        "",
        "## Summary",
        f"- precision_scenario_count: `{summary.get('precision_scenario_count', 0)}`",
        f"- precision_failed_count: `{summary.get('precision_failed_count', 0)}`",
        f"- qa_scenario_count: `{summary.get('qa_scenario_count', 0)}`",
        f"- qa_failed_count: `{summary.get('qa_failed_count', 0)}`",
        f"- diversity_scenario_count: `{summary.get('diversity_scenario_count', 0)}`",
        f"- diversity_failed_count: `{summary.get('diversity_failed_count', 0)}`",
        f"- alignment_issue_count: `{summary.get('alignment_issue_count', 0)}`",
        f"- one_or_less_display_total: `{summary.get('one_or_less_display_total', 0)}`",
        f"- zero_display_total: `{summary.get('zero_display_total', 0)}`",
        f"- avg_display_neighbors: `{summary.get('avg_display_neighbors', 0)}`",
        f"- special_sector_scenario_total: `{summary.get('special_sector_scenario_total', 0)}`",
        f"- prompt_doc_ready: `{summary.get('prompt_doc_ready', False)}`",
        f"- service_copy_ready: `{summary.get('service_copy_ready', False)}`",
        f"- ux_packet_ready: `{summary.get('ux_packet_ready', False)}`",
        f"- autoloop_ready: `{summary.get('autoloop_ready', False)}`",
        f"- zero_recovery_ready: `{summary.get('zero_recovery_ready', False)}`",
        f"- all_green: `{summary.get('all_green', False)}`",
        "",
        "## Active Execution Lane",
    ]
    if execution_lane:
        lines.extend([
            f"- id: `{execution_lane.get('id', '')}`",
            f"- title: {execution_lane.get('title', '')}",
            f"- current_gap: {execution_lane.get('current_gap', '')}",
            f"- evidence: {execution_lane.get('evidence', '')}",
            f"- proposed_next_step: {execution_lane.get('proposed_next_step', '')}",
            f"- success_metric: {execution_lane.get('success_metric', '')}",
        ])
    else:
        lines.append("- none")
    lines.extend(["", "## Parallel Brainstorm Lane"])
    if parallel_lane:
        lines.extend([
            f"- id: `{parallel_lane.get('id', '')}`",
            f"- title: {parallel_lane.get('title', '')}",
            f"- current_gap: {parallel_lane.get('current_gap', '')}",
            f"- evidence: {parallel_lane.get('evidence', '')}",
            f"- proposed_next_step: {parallel_lane.get('proposed_next_step', '')}",
            f"- success_metric: {parallel_lane.get('success_metric', '')}",
        ])
    else:
        lines.append("- none")
    lines.extend([
        "",
        "## Critical Prompt",
        "```text",
        str(prompts.get("execution_prompt") or "").strip(),
        "```",
        "",
        "## Brainstorm Prompt",
        "```text",
        str(prompts.get("brainstorm_prompt") or "").strip(),
        "```",
        "",
        "## First-Principles Prompt",
        "```text",
        str(prompts.get("first_principles_prompt") or "").strip(),
        "```",
        "",
        "## Founder Mode Questions",
    ])
    for question in list(prompts.get("founder_mode_questions") or []):
        lines.append(f"- {question}")
    prompt_doc_excerpt = str(prompts.get("prompt_doc_excerpt") or "").strip()
    if prompt_doc_excerpt:
        lines.extend([
            "",
            "## Prompt Doc Excerpt",
            "```text",
            prompt_doc_excerpt,
            "```",
            "",
        ])
    lines.extend(["## Self Questions"])
    for question in list(prompts.get("self_questions") or []):
        lines.append(f"- {question}")
    lines.extend(["", "## Brainstorm Items"])
    for item in list(report.get("brainstorm_items") or []):
        if not isinstance(item, dict):
            continue
        lines.append(
            f"- `{item.get('id', '')}` [{item.get('priority', '')}] {item.get('title', '')}"
            f" / next {item.get('proposed_next_step', '')}"
            f" / metric {item.get('success_metric', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the next action brainstorm for the yangdo scope.")
    parser.add_argument("--precision-input", default=str(DEFAULT_PRECISION_INPUT))
    parser.add_argument("--qa-input", default=str(DEFAULT_QA_INPUT))
    parser.add_argument("--diversity-input", default=str(DEFAULT_DIVERSITY_INPUT))
    parser.add_argument("--alignment-input", default=str(DEFAULT_ALIGNMENT_INPUT))
    parser.add_argument("--comparable-input", default=str(DEFAULT_COMPARABLE_INPUT))
    parser.add_argument("--ux-input", default=str(DEFAULT_UX_INPUT))
    parser.add_argument("--service-copy-input", default=str(DEFAULT_SERVICE_COPY_INPUT))
    parser.add_argument("--prompt-doc-input", default=str(DEFAULT_PROMPT_DOC_INPUT))
    parser.add_argument("--runtime-source", default=str(DEFAULT_RUNTIME_SOURCE))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    report = build_brainstorm(
        precision_matrix=_load_json(Path(args.precision_input).expanduser().resolve()),
        qa_matrix=_load_json(Path(args.qa_input).expanduser().resolve()),
        diversity_audit=_load_json(Path(args.diversity_input).expanduser().resolve()),
        alignment_audit=_load_json(Path(args.alignment_input).expanduser().resolve()),
        comparable_selection_overall=_load_json(Path(args.comparable_input).expanduser().resolve()),
        ux_packet=_load_json(Path(args.ux_input).expanduser().resolve()),
        service_copy_packet=_load_json(Path(args.service_copy_input).expanduser().resolve()),
        prompt_doc=_load_text(Path(args.prompt_doc_input).expanduser().resolve()),
        runtime_source_text=_load_text(Path(args.runtime_source).expanduser().resolve()),
    )

    json_output = Path(args.json_output).expanduser().resolve()
    md_output = Path(args.md_output).expanduser().resolve()
    json_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(json_output), "md": str(md_output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
