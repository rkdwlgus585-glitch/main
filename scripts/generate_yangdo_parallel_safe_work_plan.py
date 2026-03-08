#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
DEFAULT_SECTOR_AUDIT = LOG_DIR / "yangdo_sector_price_audit_latest.json"
DEFAULT_BRAINSTORM = LOG_DIR / "yangdo_price_logic_brainstorm_latest.json"
DEFAULT_JSON = LOG_DIR / "yangdo_parallel_safe_work_plan_latest.json"
DEFAULT_MD = LOG_DIR / "yangdo_parallel_safe_work_plan_latest.md"

CORE_RUNTIME_FILES = {
    "yangdo_blackbox_api.py",
    "yangdo_calculator.py",
    "permit_diagnosis_calculator.py",
}

PUBLISH_RUNTIME_PREFIXES = (
    "scripts/publish_",
    "scripts/run_calculator_browser_smoke.py",
    "scripts/run_public_calculator_post_publish_verify.py",
    "scripts/refresh_wordpress_platform_artifacts.py",
)

LAB_RUNTIME_PREFIXES = (
    "workspace_partitions/site_session/wp_surface_lab/",
    "scripts/bootstrap_wp_surface_lab_php_fallback.py",
    "scripts/run_wp_surface_lab_fallback_smoke.py",
)

SAFE_PRICE_ANALYSIS_PREFIXES = (
    "scripts/generate_yangdo_",
    "tests/test_generate_yangdo_",
    "docs/yangdo_",
)

SAFE_PRICE_ANALYSIS_EXACT = {
    "tests/test_fire_guarded_prior.py",
}


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _run_git_status(cwd: Path) -> List[str]:
    completed = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [line.rstrip() for line in completed.stdout.splitlines() if line.strip()]


def _extract_path(status_line: str) -> str:
    text = str(status_line or "").rstrip()
    if len(text) <= 3:
        return ""
    return text[3:].strip()


def _classify_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized in CORE_RUNTIME_FILES:
        return "blocked_runtime"
    if any(normalized.startswith(prefix) for prefix in PUBLISH_RUNTIME_PREFIXES):
        return "blocked_publish"
    if any(normalized.startswith(prefix) for prefix in LAB_RUNTIME_PREFIXES):
        return "ops_only_lab"
    if normalized.startswith("scripts/generate_permit_") or normalized.startswith("tests/test_generate_permit_"):
        return "permit_parallel"
    if any(normalized.startswith(prefix) for prefix in SAFE_PRICE_ANALYSIS_PREFIXES) or normalized in SAFE_PRICE_ANALYSIS_EXACT:
        return "safe_price_analysis"
    if normalized.startswith("config/") or normalized.startswith("docs/") or normalized.startswith("tests/") or normalized.startswith("scripts/"):
        return "shared_misc"
    return "uncategorized"


def _top_hotspot_names(sector_audit: Dict[str, Any], status_name: str, limit: int = 6) -> List[str]:
    rows = [row for row in sector_audit.get("sectors") or [] if str(row.get("status") or "") == status_name]
    rows.sort(
        key=lambda row: (
            -_safe_float((row.get("price_metrics") or {}).get("under_67_share")),
            -int(row.get("observed_record_count") or 0),
            str(row.get("sector") or ""),
        )
    )
    return [str(row.get("sector") or "") for row in rows[:limit] if str(row.get("sector") or "").strip()]


def build_report(*, git_status_lines: List[str], sector_audit: Dict[str, Any], brainstorm: Dict[str, Any]) -> Dict[str, Any]:
    classified: Dict[str, List[Dict[str, str]]] = {
        "blocked_runtime": [],
        "blocked_publish": [],
        "ops_only_lab": [],
        "safe_price_analysis": [],
        "permit_parallel": [],
        "shared_misc": [],
        "uncategorized": [],
    }
    for line in git_status_lines:
        path = _extract_path(line)
        category = _classify_path(path)
        classified[category].append({"status": line[:2], "path": path})

    status_counts = {key: len(value) for key, value in classified.items()}
    hotspot_under = _top_hotspot_names(sector_audit, "underpricing_hotspot")
    hotspot_sparse = _top_hotspot_names(sector_audit, "sparse_support_hotspot")
    primary_lane = dict(brainstorm.get("current_execution_lane") or {})
    parallel_lane = dict(brainstorm.get("parallel_execution_lane") or brainstorm.get("parallel_brainstorm_lane") or {})

    safe_now = [
        "새 yangdo 감사/실험 스크립트 추가",
        "새 test_generate_yangdo_* 테스트 추가",
        "price-logic 브레인스토밍/리포트 재생성",
        "미관측 업종 매핑 카탈로그 정리",
    ]
    blocked_now = [
        "yangdo_blackbox_api.py 직접 수정",
        "yangdo_calculator.py 직접 수정",
        "publish/private/public 배포 스크립트 수정",
        "permit_diagnosis_calculator.py 수정",
    ]

    return {
        "generated_at": _now_str(),
        "packet_id": "yangdo_parallel_safe_work_plan_latest",
        "summary": {
            "dirty_file_count": sum(status_counts.values()),
            "category_counts": status_counts,
            "primary_lane": str(primary_lane.get("id") or ""),
            "parallel_lane": str(parallel_lane.get("id") or ""),
            "underpricing_hotspots": hotspot_under,
            "sparse_support_hotspots": hotspot_sparse,
            "safe_to_edit_now": status_counts["safe_price_analysis"] + status_counts["permit_parallel"],
            "blocked_to_edit_now": status_counts["blocked_runtime"] + status_counts["blocked_publish"],
        },
        "safe_workzones": {
            "safe_now": safe_now,
            "blocked_now": blocked_now,
            "blocked_runtime_files": classified["blocked_runtime"],
            "blocked_publish_files": classified["blocked_publish"][:12],
            "safe_price_analysis_files": classified["safe_price_analysis"][:20],
            "permit_parallel_files": classified["permit_parallel"][:12],
            "ops_only_lab_files": classified["ops_only_lab"][:12],
        },
        "collaboration_contract": {
            "touch_policy": [
                "core runtime, publish, permit runtime 파일은 이번 배치에서 잠근다.",
                "yangdo 분석/감사/브레인스토밍은 새 파일만 추가한다.",
                "테스트는 test_generate_yangdo_* 계열로 분리한다.",
                "배포/재기동은 별도 green gate 배치에서만 수행한다.",
            ],
            "primary_lane": primary_lane,
            "parallel_lane": parallel_lane,
        },
        "next_parallel_actions": [
            {
                "id": "fire_guarded_patch_validation",
                "why": "소방 guarded patch는 유일한 guarded-ready 후보라서 정확도와 과대평가 budget만 따로 검증하면 된다.",
                "safe": True,
            },
            {
                "id": "exact_combo_recovery_audit",
                "why": "토목/포장/상하수도/조경/토건/석공/석면/시설물은 가격식보다 cohort recovery가 먼저다.",
                "safe": True,
            },
            {
                "id": "unobserved_sector_catalog",
                "why": "미관측 14개 업종은 모델 수정이 아니라 매핑과 데이터 유입 문제라서 별도 카탈로그로 분리해야 한다.",
                "safe": True,
            },
            {
                "id": "runtime_patch_or_publish",
                "why": "핵심 엔진과 배포 파일은 현재 dirty 상태이므로 분석 산출물 확인 후 별도 배치에서 처리한다.",
                "safe": False,
            },
        ],
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    safe = payload.get("safe_workzones") or {}
    lines = [
        "# Yangdo Parallel Safe Work Plan",
        "",
        f"- generated_at: {payload.get('generated_at')}",
        f"- dirty_file_count: {summary.get('dirty_file_count')}",
        f"- primary_lane: {summary.get('primary_lane')}",
        f"- parallel_lane: {summary.get('parallel_lane')}",
        f"- safe_to_edit_now: {summary.get('safe_to_edit_now')}",
        f"- blocked_to_edit_now: {summary.get('blocked_to_edit_now')}",
        "",
        "## Underpricing Hotspots",
    ]
    for item in summary.get("underpricing_hotspots") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Sparse Support Hotspots"])
    for item in summary.get("sparse_support_hotspots") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Safe Now"])
    for item in safe.get("safe_now") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Blocked Now"])
    for item in safe.get("blocked_now") or []:
        lines.append(f"- {item}")
    lines.extend(["", "## Next Parallel Actions"])
    for item in payload.get("next_parallel_actions") or []:
        tag = "SAFE" if item.get("safe") else "BLOCKED"
        lines.append(f"- [{tag}] {item.get('id')}: {item.get('why')}")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a safe parallel work plan for yangdo pricing tasks.")
    parser.add_argument("--sector-audit", type=Path, default=DEFAULT_SECTOR_AUDIT)
    parser.add_argument("--brainstorm", type=Path, default=DEFAULT_BRAINSTORM)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()

    payload = build_report(
        git_status_lines=_run_git_status(ROOT),
        sector_audit=_load_json(args.sector_audit),
        brainstorm=_load_json(args.brainstorm),
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(json.dumps({"ok": True, "json": str(args.json), "md": str(args.md)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
