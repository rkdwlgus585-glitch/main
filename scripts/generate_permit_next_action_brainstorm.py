from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MASTER_INPUT = ROOT / "logs" / "permit_master_catalog_latest.json"
DEFAULT_PROVENANCE_INPUT = ROOT / "logs" / "permit_provenance_audit_latest.json"
DEFAULT_FOCUS_INPUT = ROOT / "logs" / "permit_focus_priority_latest.json"
DEFAULT_BACKLOG_INPUT = ROOT / "logs" / "permit_source_upgrade_backlog_latest.json"
DEFAULT_PATENT_INPUT = ROOT / "logs" / "permit_patent_evidence_bundle_latest.json"
DEFAULT_WIDGET_INPUT = ROOT / "logs" / "widget_rental_catalog_latest.json"
DEFAULT_JSON_OUTPUT = ROOT / "logs" / "permit_next_action_brainstorm_latest.json"
DEFAULT_MD_OUTPUT = ROOT / "logs" / "permit_next_action_brainstorm_latest.md"


def _load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("permit brainstorm input must be a JSON object")
    return payload


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except Exception:
        return 0


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _has_encoding_noise(value: Any) -> bool:
    text = _safe_str(value)
    return bool(text) and "\ufffd" in text


def _count_encoding_noise(rows: List[Dict[str, Any]]) -> int:
    noisy = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        fields = (
            row.get("service_name"),
            row.get("major_name"),
            row.get("group_name"),
            row.get("law_title"),
            row.get("legal_basis_title"),
        )
        if any(_has_encoding_noise(value) for value in fields):
            noisy += 1
    return noisy


def build_brainstorm(
    *,
    master_catalog: Dict[str, Any],
    provenance_audit: Dict[str, Any],
    focus_report: Dict[str, Any],
    source_upgrade_backlog: Dict[str, Any],
    permit_patent_evidence_bundle: Dict[str, Any] | None = None,
    widget_rental_catalog: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    master_summary = dict(master_catalog.get("summary") or {})
    provenance_summary = dict(provenance_audit.get("summary") or {})
    focus_summary = dict(focus_report.get("summary") or {})
    backlog_summary = dict(source_upgrade_backlog.get("summary") or {})
    patent_summary = (
        dict((permit_patent_evidence_bundle or {}).get("summary") or {})
        if isinstance(permit_patent_evidence_bundle, dict)
        else {}
    )
    widget_summary = (
        dict((widget_rental_catalog or {}).get("summary") or {})
        if isinstance(widget_rental_catalog, dict)
        else {}
    )
    master_rows = [row for row in list(master_catalog.get("industries") or []) if isinstance(row, dict)]
    focus_seed_groups = list(
        ((source_upgrade_backlog.get("upgrade_tracks") or {}).get("focus_seed_source_groups") or [])
    )
    absorbed_groups = list(
        ((source_upgrade_backlog.get("upgrade_tracks") or {}).get("absorbed_source_groups") or [])
    )
    candidate_pack_groups = list(
        ((source_upgrade_backlog.get("upgrade_tracks") or {}).get("candidate_pack_stabilization_groups") or [])
    )

    focus_seed_total = _safe_int(provenance_summary.get("focus_seed_row_total"))
    focus_family_registry_total = _safe_int(provenance_summary.get("focus_family_registry_row_total"))
    focus_family_registry_missing_raw_source_proof_total = _safe_int(
        provenance_summary.get("focus_family_registry_missing_raw_source_proof_total")
    )
    absorbed_total = _safe_int(master_summary.get("master_absorbed_row_total"))
    candidate_pack_total = _safe_int(provenance_summary.get("candidate_pack_total"))
    inferred_total = _safe_int(provenance_summary.get("master_inferred_overlay_total"))
    real_focus_target_total = _safe_int(
        focus_summary.get("real_focus_target_total", focus_summary.get("real_high_confidence_focus_total"))
    )
    focus_registry_total = _safe_int(master_summary.get("master_focus_registry_row_total"))
    patent_family_total = _safe_int(patent_summary.get("focus_source_family_total"))
    claim_packet_family_total = _safe_int(patent_summary.get("claim_packet_family_total"))
    claim_packet_complete_family_total = _safe_int(patent_summary.get("claim_packet_complete_family_total"))
    checksum_sample_family_total = _safe_int(patent_summary.get("checksum_sample_family_total"))
    widget_claim_packet_family_total = _safe_int(widget_summary.get("permit_claim_packet_family_total"))
    widget_checksum_sample_family_total = _safe_int(widget_summary.get("permit_checksum_sample_family_total"))
    encoding_noise_total = _count_encoding_noise(master_rows)

    brainstorm_items: List[Dict[str, Any]] = []
    if focus_seed_total:
        top_group = _safe_str(focus_seed_groups[0].get("group_key")) if focus_seed_groups else "top focus-seed family"
        brainstorm_items.append(
            {
                "id": "focus_seed_source_upgrade",
                "priority": "P1",
                "track": "execution",
                "title": f"Focus-seed {focus_seed_total}건 official source upgrade",
                "current_gap": f"중간 원천 focus-seed row {focus_seed_total}건이 아직 official raw source로 고정되지 않음",
                "why_now": "제품 coverage는 확보됐지만, 특허·임대형 계약 기준으로는 중간 seed 의존을 줄여야 함",
                "proposed_next_step": f"`{top_group}`부터 official source snapshot 또는 raw master seed로 치환",
                "success_metric": f"focus_seed_row_total {focus_seed_total} -> 0",
                "parallelizable_with": ["candidate_pack_rule_upgrade", "encoding_noise_repair"],
            }
        )
        brainstorm_items.append(
            {
                "id": "patent_evidence_bundle",
                "priority": "P2",
                "track": "research",
                "title": "특허 근거 패킷 병렬 정리",
                "current_gap": f"focus-seed 법령군 {max(1, len(focus_seed_groups))}개가 제품에는 반영됐지만 특허 claim/evidence packet으로는 아직 분리되지 않음",
                "why_now": "official source upgrade와 병렬로 진행해도 충돌이 없고, 이후 플랫폼/임대형 설명자료의 정합성을 높일 수 있음",
                "proposed_next_step": "법령군별로 법령 근거, 입력 변수, 계산 결과, UI 노출 문구를 묶은 특허 증빙 패킷을 생성",
                "success_metric": f"focus_seed_group_total {max(1, len(focus_seed_groups))} families documented",
                "parallelizable_with": ["focus_seed_source_upgrade"],
            }
        )
    elif focus_family_registry_total and focus_family_registry_missing_raw_source_proof_total:
        brainstorm_items.append(
            {
                "id": "focus_family_registry_hardening",
                "priority": "P1",
                "track": "execution",
                "title": f"Curated family registry {focus_family_registry_total}건 raw-source hardening",
                "current_gap": (
                    f"focus-family-registry row {focus_family_registry_total}건 중 "
                    f"{focus_family_registry_missing_raw_source_proof_total}건이 raw-source proof 없이 남아 있음"
                ),
                "why_now": "focus-seed 잔량은 정리됐고, 이제 남은 핵심 리스크는 curated registry의 증빙 밀도와 원천화 수준임",
                "proposed_next_step": "법령군별로 official snapshot note, raw source checksum, 증빙 캡처 메타를 family registry row에 추가",
                "success_metric": (
                    f"focus_family_registry_missing_raw_source_proof_total "
                    f"{focus_family_registry_missing_raw_source_proof_total} -> 0"
                ),
                "parallelizable_with": ["patent_evidence_bundle"],
            }
        )
        brainstorm_items.append(
            {
                "id": "patent_evidence_bundle",
                "priority": "P2",
                "track": "research",
                "title": "특허 근거 패킷 병렬 정리",
                "current_gap": "family registry가 제품에는 반영됐지만 특허 claim/evidence packet과 raw-source proof packet이 완전히 결합되지는 않음",
                "why_now": "registry hardening과 병렬로 정리하면 플랫폼/임대형/특허 설명자료 정합성을 바로 끌어올릴 수 있음",
                "proposed_next_step": "법령군별 claim, 입력 변수, 계산 로직, UI 노출, source proof를 하나의 증빙 packet으로 통합",
                "success_metric": "all curated family registry groups documented with claim+source proof",
                "parallelizable_with": ["focus_family_registry_hardening"],
            }
        )
    elif focus_family_registry_total and claim_packet_complete_family_total < max(1, patent_family_total):
        brainstorm_items.append(
            {
                "id": "patent_evidence_bundle_lock",
                "priority": "P1",
                "track": "execution",
                "title": "특허 증빙 패킷 고도화",
                "current_gap": (
                    f"curated family registry {focus_family_registry_total}건은 raw-source proof까지 채워졌지만 "
                    "claim/evidence 설명 패킷이 아직 제품 계약·특허 서술 기준으로 완전히 고정되지는 않음"
                ),
                "why_now": "raw-source hardening이 끝난 뒤에는 특허 및 외부 설명자료 정밀화가 다음 병목이 됨",
                "proposed_next_step": "법령군별 claim, 입력 변수, 계산 로직, UI 노출, checksum proof를 하나의 특허 증빙 패킷으로 통합",
                "success_metric": (
                    f"claim_packet_complete_family_total {claim_packet_complete_family_total}"
                    f" -> {max(1, patent_family_total)}"
                ),
                "parallelizable_with": ["platform_contract_proof_surface"],
            }
        )
        brainstorm_items.append(
            {
                "id": "platform_contract_proof_surface",
                "priority": "P2",
                "track": "product",
                "title": "플랫폼 계약에 provenance 노출",
                "current_gap": "widget/API/master 계약은 준비됐지만 raw-source proof 요약이 외부 계약 필드로는 충분히 드러나지 않음",
                "why_now": "특허·임대형·운영 QA가 같은 source proof를 보도록 맞춰야 이후 설명 불일치가 줄어듦",
                "proposed_next_step": "master/widget/api summary에 raw-source proof coverage와 family checksum 요약을 추가",
                "success_metric": "external contracts expose proof coverage + checksum summary",
                "parallelizable_with": ["patent_evidence_bundle_lock"],
            }
        )
    elif checksum_sample_family_total and (
        widget_claim_packet_family_total < claim_packet_complete_family_total
        or widget_checksum_sample_family_total < checksum_sample_family_total
    ):
        brainstorm_items.append(
            {
                "id": "platform_contract_proof_surface",
                "priority": "P1",
                "track": "execution",
                "title": "플랫폼 계약에 claim/proof surface 고정",
                "current_gap": (
                    f"특허 증빙 family {claim_packet_complete_family_total}건은 claim packet이 완성됐지만 "
                    f"외부 계약면에는 checksum sample family {widget_checksum_sample_family_total}/{checksum_sample_family_total}만 노출됨"
                ),
                "why_now": "patent bundle 정합성이 확보된 뒤에는 widget/API/master 계약에 같은 checksum sample과 claim packet 지표를 바로 노출해야 함",
                "proposed_next_step": "widget/API/master summary와 proof examples에 family checksum sample 및 claim packet coverage를 동기화",
                "success_metric": (
                    f"widget checksum surface {widget_checksum_sample_family_total}/{checksum_sample_family_total}"
                    f" and claim packet surface {widget_claim_packet_family_total}/{claim_packet_complete_family_total}"
                ),
                "parallelizable_with": ["family_case_goldset"],
            }
        )
        brainstorm_items.append(
            {
                "id": "family_case_goldset",
                "priority": "P2",
                "track": "research",
                "title": "법령군별 검증 사례 gold-set 구축",
                "current_gap": "구조화된 claim packet은 생겼지만 family별 대표 입력/예상결과 사례 세트는 아직 없음",
                "why_now": "계약면과 특허 서술이 정리된 뒤에는 계산 검증 표본이 있어야 QA와 특허 근거가 같이 버틸 수 있음",
                "proposed_next_step": "6개 법령군별 최소/경계/실패 사례 입력과 예상 결과를 gold-set JSON으로 고정",
                "success_metric": f"family case gold-set documented for {max(1, claim_packet_complete_family_total)} families",
                "parallelizable_with": ["platform_contract_proof_surface"],
            }
        )
    elif focus_family_registry_total:
        brainstorm_items.append(
            {
                "id": "runtime_proof_disclosure",
                "priority": "P1",
                "track": "execution",
                "title": "런타임 proof/claim 노출 정렬",
                "current_gap": (
                    f"family claim packet {claim_packet_family_total}건과 checksum sample {checksum_sample_family_total}건은 준비됐지만 "
                    "실제 런타임/운영 화면에서는 proof badge와 claim summary가 바로 보이지 않음"
                ),
                "why_now": "특허 번들과 외부 계약면이 정리된 뒤에는 QA와 운영자가 같은 근거를 제품 화면에서 바로 확인할 수 있어야 함",
                "proposed_next_step": "permit runtime bootstrap과 UI에 family claim id, checksum sample, official snapshot note를 노출",
                "success_metric": "runtime proof badge and claim summary visible across focus rows",
                "parallelizable_with": ["family_case_goldset"],
            }
        )
        brainstorm_items.append(
            {
                "id": "family_case_goldset",
                "priority": "P2",
                "track": "research",
                "title": "법령군별 검증 사례 gold-set 구축",
                "current_gap": "family proof와 claim packet은 갖췄지만 대표 성공/실패/경계 사례 세트는 아직 별도 자산이 아님",
                "why_now": "UI proof disclosure와 병렬로 gold-set을 고정해 두면 이후 계산 regression과 특허 설명을 한 번에 검증할 수 있음",
                "proposed_next_step": "6개 법령군별 최소/경계/실패 사례 입력과 예상 결과를 gold-set JSON으로 생성",
                "success_metric": f"family case gold-set documented for {max(1, claim_packet_complete_family_total)} families",
                "parallelizable_with": ["runtime_proof_disclosure"],
            }
        )
    if absorbed_total:
        top_group = _safe_str(absorbed_groups[0].get("group_key")) if absorbed_groups else "top absorbed family"
        brainstorm_items.append(
            {
                "id": "materialize_absorbed_registry",
                "priority": "P1",
                "track": "execution",
                "title": "Absorbed 50건 raw registry materialization",
                "current_gap": f"runtime에서만 흡수된 row {absorbed_total}건이 남아 있음",
                "why_now": "현재 제품에서는 보이지만 원천 스냅샷으로 굳어 있지 않아 재생성 의존성이 큼",
                "proposed_next_step": f"`{top_group}`부터 raw/master seed 파일을 만들어 흡수 row를 원천화",
                "success_metric": "master_absorbed_row_total 50 -> 0",
                "parallelizable_with": ["candidate_pack_rule_upgrade", "encoding_noise_repair"],
            }
        )
    if candidate_pack_total:
        top_group = _safe_str(candidate_pack_groups[0].get("group_key")) if candidate_pack_groups else "top candidate-pack family"
        brainstorm_items.append(
            {
                "id": "candidate_pack_rule_upgrade",
                "priority": "P1",
                "track": "execution",
                "title": "Candidate-pack 3건 structured mapping 고정",
                "current_gap": f"법령 후보 기반 row {candidate_pack_total}건이 아직 구조화되지 않음",
                "why_now": "핵심 스코프가 53건으로 줄었기 때문에 3건만 해결해도 제품 신뢰도가 크게 올라감",
                "proposed_next_step": f"`{top_group}`부터 article/rule pack으로 승격하는 수동 매핑 seed 추가",
                "success_metric": "candidate_pack_total 3 -> 0",
                "parallelizable_with": ["materialize_absorbed_registry", "inferred_row_reverification"],
            }
        )
    if inferred_total:
        brainstorm_items.append(
            {
                "id": "inferred_row_reverification",
                "priority": "P1",
                "track": "research",
                "title": "Inferred 3건 재검증",
                "current_gap": f"추론 alias row {inferred_total}건이 partner 기본값으로 쓰이기엔 위험함",
                "why_now": "남은 실업종 3건이 모두 inferred/candidate-pack 계열이라 오탐 리스크가 집중됨",
                "proposed_next_step": "각 row의 법령명, 조문명, 등록기준 문장을 대조하는 gold-set 검증 추가",
                "success_metric": "master_inferred_overlay_total 3 -> 0 또는 명시적 verified flag 3/3",
                "parallelizable_with": ["candidate_pack_rule_upgrade", "encoding_noise_repair"],
            }
        )
    if focus_registry_total and real_focus_target_total < max(3, focus_registry_total // 5):
        brainstorm_items.append(
            {
                "id": "real_focus_catalog_gap",
                "priority": "P2",
                "track": "product",
                "title": "실업종 핵심 row 부재 해소",
                "current_gap": f"실업종 핵심 row가 {real_focus_target_total}건뿐이라 전부 focus registry/rule 계층에 의존",
                "why_now": "플랫폼/임대형 계약은 안정화됐지만 사용자 체감상 아직 real catalog 중심 제품처럼 보이기 어려움",
                "proposed_next_step": "건설·전기·소방 계열을 raw 업종 카탈로그로 승격하거나 별도 public focus registry를 정의",
                "success_metric": "real_focus_target_total -> 10+",
                "parallelizable_with": ["materialize_absorbed_registry"],
            }
        )
    if encoding_noise_total:
        brainstorm_items.append(
            {
                "id": "encoding_noise_repair",
                "priority": "P2",
                "track": "quality",
                "title": "문자 인코딩 오염 정리",
                "current_gap": f"출력 row {encoding_noise_total}건에서 깨진 문자열이 관찰됨",
                "why_now": "법령명/업종명이 깨지면 특허 근거와 partner 임대 자료의 신뢰도를 즉시 훼손함",
                "proposed_next_step": "master/focus 출력 전 텍스트 필드에 인코딩 이상 탐지와 교정 큐를 추가",
                "success_metric": "encoding_noise_row_total -> 0",
                "parallelizable_with": ["materialize_absorbed_registry", "candidate_pack_rule_upgrade"],
            }
        )

    primary_execution = next(
        (item for item in brainstorm_items if item.get("track") == "execution"),
        {},
    )
    if not primary_execution and brainstorm_items:
        primary_execution = dict(brainstorm_items[0])
    primary_parallel = next(
        (
            item
            for item in brainstorm_items
            if item.get("id") != primary_execution.get("id")
            and item.get("track") in {"research", "quality", "product"}
        ),
        {},
    )
    if not primary_parallel:
        primary_parallel = next(
            (
                item
                for item in brainstorm_items
                if item.get("id") != primary_execution.get("id")
            ),
            {},
        )

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "master_industry_total": _safe_int(master_summary.get("master_industry_total")),
            "focus_family_registry_row_total": _safe_int(
                provenance_summary.get("focus_family_registry_row_total")
            ),
            "focus_seed_row_total": focus_seed_total,
            "master_absorbed_row_total": absorbed_total,
            "candidate_pack_total": candidate_pack_total,
            "inferred_reverification_total": inferred_total,
            "real_focus_target_total": real_focus_target_total,
            "real_high_confidence_focus_total": real_focus_target_total,
            "encoding_noise_row_total": encoding_noise_total,
            "focus_seed_group_total": _safe_int(backlog_summary.get("focus_seed_group_total")),
            "absorbed_group_total": _safe_int(backlog_summary.get("absorbed_group_total")),
            "claim_packet_family_total": claim_packet_family_total,
            "claim_packet_complete_family_total": claim_packet_complete_family_total,
            "checksum_sample_family_total": checksum_sample_family_total,
            "widget_claim_packet_family_total": widget_claim_packet_family_total,
            "widget_checksum_sample_family_total": widget_checksum_sample_family_total,
        },
        "current_execution_lane": primary_execution,
        "parallel_brainstorm_lane": primary_parallel,
        "brainstorm_items": brainstorm_items,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    summary = dict(report.get("summary") or {})
    lines = [
        "# Permit Next Action Brainstorm",
        "",
        "## Summary",
        f"- master_industry_total: `{summary.get('master_industry_total', 0)}`",
        f"- focus_family_registry_row_total: `{summary.get('focus_family_registry_row_total', 0)}`",
        f"- focus_seed_row_total: `{summary.get('focus_seed_row_total', 0)}`",
        f"- master_absorbed_row_total: `{summary.get('master_absorbed_row_total', 0)}`",
        f"- candidate_pack_total: `{summary.get('candidate_pack_total', 0)}`",
        f"- inferred_reverification_total: `{summary.get('inferred_reverification_total', 0)}`",
        f"- real_focus_target_total: `{summary.get('real_focus_target_total', summary.get('real_high_confidence_focus_total', 0))}`",
        f"- encoding_noise_row_total: `{summary.get('encoding_noise_row_total', 0)}`",
        f"- focus_seed_group_total: `{summary.get('focus_seed_group_total', 0)}`",
        f"- absorbed_group_total: `{summary.get('absorbed_group_total', 0)}`",
        f"- claim_packet_family_total: `{summary.get('claim_packet_family_total', 0)}`",
        f"- claim_packet_complete_family_total: `{summary.get('claim_packet_complete_family_total', 0)}`",
        f"- checksum_sample_family_total: `{summary.get('checksum_sample_family_total', 0)}`",
        f"- widget_claim_packet_family_total: `{summary.get('widget_claim_packet_family_total', 0)}`",
        f"- widget_checksum_sample_family_total: `{summary.get('widget_checksum_sample_family_total', 0)}`",
        "",
        "## Active Execution Lane",
    ]
    execution_lane = dict(report.get("current_execution_lane") or {})
    if execution_lane:
        lines.extend(
            [
                f"- id: `{execution_lane.get('id', '')}`",
                f"- title: {execution_lane.get('title', '')}",
                f"- current_gap: {execution_lane.get('current_gap', '')}",
                f"- proposed_next_step: {execution_lane.get('proposed_next_step', '')}",
                f"- success_metric: {execution_lane.get('success_metric', '')}",
            ]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Parallel Brainstorm Lane"])
    brainstorm_lane = dict(report.get("parallel_brainstorm_lane") or {})
    if brainstorm_lane:
        lines.extend(
            [
                f"- id: `{brainstorm_lane.get('id', '')}`",
                f"- title: {brainstorm_lane.get('title', '')}",
                f"- current_gap: {brainstorm_lane.get('current_gap', '')}",
                f"- proposed_next_step: {brainstorm_lane.get('proposed_next_step', '')}",
                f"- success_metric: {brainstorm_lane.get('success_metric', '')}",
            ]
        )
    else:
        lines.append("- none")
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
    parser = argparse.ArgumentParser(description="Generate the next action brainstorm for the permit focus scope.")
    parser.add_argument("--master-input", default=str(DEFAULT_MASTER_INPUT))
    parser.add_argument("--provenance-input", default=str(DEFAULT_PROVENANCE_INPUT))
    parser.add_argument("--focus-input", default=str(DEFAULT_FOCUS_INPUT))
    parser.add_argument("--backlog-input", default=str(DEFAULT_BACKLOG_INPUT))
    parser.add_argument("--patent-input", default=str(DEFAULT_PATENT_INPUT))
    parser.add_argument("--widget-input", default=str(DEFAULT_WIDGET_INPUT))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON_OUTPUT))
    parser.add_argument("--md-output", default=str(DEFAULT_MD_OUTPUT))
    args = parser.parse_args()

    report = build_brainstorm(
        master_catalog=_load_json(Path(args.master_input).expanduser().resolve()),
        provenance_audit=_load_json(Path(args.provenance_input).expanduser().resolve()),
        focus_report=_load_json(Path(args.focus_input).expanduser().resolve()),
        source_upgrade_backlog=_load_json(Path(args.backlog_input).expanduser().resolve()),
        permit_patent_evidence_bundle=_load_json(Path(args.patent_input).expanduser().resolve()),
        widget_rental_catalog=_load_json(Path(args.widget_input).expanduser().resolve()),
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
