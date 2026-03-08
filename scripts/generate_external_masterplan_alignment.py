#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = Path(r"C:\Users\rkdwl\Desktop\cli 학습")
DEFAULT_MASTERPLAN = ROOT / "MASTERPLAN.md"


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")


def _contains_any(text: str, patterns: Sequence[str]) -> bool:
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in patterns)


DIRECTIVE_RULES: List[Dict[str, Any]] = [
    {
        "key": "yangdo_system_priority",
        "label": "AI 양도가 산정 시스템 최우선",
        "source_patterns": ["AI 양도가 산정 시스템", "AI양도가 산정 시스템", "ai양도양수 계산기"],
        "masterplan_patterns": ["AI 양도가 산정", "yangdo"],
    },
    {
        "key": "permit_system_priority",
        "label": "AI 인허가 사전검토 시스템 최우선",
        "source_patterns": ["AI 인허가 사전검토 시스템", "AI인허가 사전검토 시스템", "ai인허가 사전검토"],
        "masterplan_patterns": ["AI 인허가 사전검토", "permit"],
    },
    {
        "key": "kr_platformization",
        "label": "seoulmna.kr 플랫폼화",
        "source_patterns": ["seoulmna.kr 플랫폼화", "seoulmna.kr 플랫폼 형식으로 전면 개편", "플랫폼을 탑재할 수 있는 플랫폼"],
        "masterplan_patterns": ["seoulmna.kr", "플랫폼 전면 개편", "WordPress/Astra 기반 플랫폼 전면 개편"],
    },
    {
        "key": "patent_preparation",
        "label": "특허 준비/고도화",
        "source_patterns": ["특허를 위한 고도화", "특허 등록 기반", "위 2가지 시스템 특허", "특허"],
        "masterplan_patterns": ["특허", "attorney handoff"],
    },
    {
        "key": "rental_widget_model",
        "label": "타 사이트 위젯/임대 구조",
        "source_patterns": ["타 사이트 위젯", "위젯 형태", "임대 가능하도록 구축", "타 사 임대방식"],
        "masterplan_patterns": ["위젯/API 임대", "타 사이트 위젯", "임대 구조"],
    },
    {
        "key": "continuous_brainstorm_loop",
        "label": "브레인스토밍/비판적 사고 반복",
        "source_patterns": ["브레인스토밍", "비판적 사고", "문제 해결 반복", "계속해서 스스로 되묻기"],
        "masterplan_patterns": ["브레인스토밍", "비판적 사고", "first-principles review", "next action brainstorm"],
    },
    {
        "key": "full_autonomy",
        "label": "사용자 최소 개입/총괄 자율 진행",
        "source_patterns": ["나는 엔터만 누르는 사람이", "총괄 진행은 니가", "혼자 수행", "알아서 반복 진행"],
        "masterplan_patterns": ["사용자 확인을 기다리지 않는다", "모든 배치는", "Continuous Improvement Rule"],
    },
    {
        "key": "sector_focus",
        "label": "전기/통신/소방 집중",
        "source_patterns": ["전기/통신/소방", "전기/소방/통신", "전기/소방/정보통신"],
        "masterplan_patterns": ["전기", "소방", "정보통신"],
    },
    {
        "key": "permit_law_exception_case_collection",
        "label": "인허가 법령/특례/사례 데이터 수집",
        "source_patterns": ["관계 법령", "특례", "사례 등 데이터 수집", "등록기준"],
        "masterplan_patterns": ["법령", "특례", "사례", "등록기준", "typed_criteria"],
    },
    {
        "key": "qa_ui_ux_full_cycle",
        "label": "총괄 테스트/QA/UI/UX 개선",
        "source_patterns": ["총괄 테스트/qa/ui/ux", "총괄 테스트/QA/UI/UX", "모든 문제점 파악 및 개선/해결"],
        "masterplan_patterns": ["QA", "UX", "운영 자동화"],
    },
    {
        "key": "launch_to_patent_end_to_end",
        "label": "출시와 특허 등록까지 종단 관리",
        "source_patterns": ["출시와 특허 등록까지", "브레인스토밍->기획->수행->검수->최종 완료"],
        "masterplan_patterns": ["Completion Criteria", "특허", "live", "최종"],
    },
]


def _normalize_source_paths(source_paths: Iterable[Path] | Path) -> List[Path]:
    if isinstance(source_paths, Path):
        return [source_paths]
    out: List[Path] = []
    seen: set[str] = set()
    for path in source_paths:
        text = str(path)
        if text not in seen:
            seen.add(text)
            out.append(path)
    return out


def discover_default_sources(source_dir: Path) -> List[Path]:
    if not source_dir.exists():
        return []
    names = {
        "0. 마스터플랜.txt",
        "AI계산기.txt",
        "양도양수 테스트.txt",
        "인허가 테스트.txt",
        "계산기 UI,UX.txt",
        "0. 계산기 학습 관련.txt",
    }
    matches = [path for path in sorted(source_dir.glob("*.txt")) if path.name in names]
    return matches


def build_alignment(source_paths: Iterable[Path] | Path, masterplan_path: Path) -> Dict[str, Any]:
    normalized_paths = _normalize_source_paths(source_paths)
    source_blobs: List[Dict[str, Any]] = []
    source_texts: List[str] = []

    for path in normalized_paths:
        text = _read_text(path)
        source_blobs.append(
            {
                "path": str(path),
                "exists": path.exists(),
                "nonempty": bool(text.strip()),
            }
        )
        if text:
            source_texts.append(text)

    combined_source_text = "\n\n".join(source_texts)
    masterplan_text = _read_text(masterplan_path)

    checks: List[Dict[str, Any]] = []
    missing: List[str] = []
    source_hits = 0

    for rule in DIRECTIVE_RULES:
        source_present = _contains_any(combined_source_text, list(rule["source_patterns"]))
        if source_present:
            source_hits += 1
        masterplan_present = _contains_any(masterplan_text, list(rule["masterplan_patterns"]))
        aligned = (not source_present) or masterplan_present
        row = {
            "key": rule["key"],
            "label": rule["label"],
            "source_present": source_present,
            "masterplan_present": masterplan_present,
            "aligned": aligned,
        }
        checks.append(row)
        if source_present and not masterplan_present:
            missing.append(rule["key"])

    summary = {
        "packet_ready": bool(source_texts and masterplan_text),
        "source_file_count": len(normalized_paths),
        "loaded_source_count": len(source_texts),
        "masterplan_exists": masterplan_path.exists(),
        "directive_count": len(checks),
        "source_directive_count": source_hits,
        "missing_count": len(missing),
        "alignment_ok": len(missing) == 0 and bool(source_texts and masterplan_text),
        "missing_keys": missing,
    }
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_files": source_blobs,
        "masterplan_path": str(masterplan_path),
        "summary": summary,
        "checks": checks,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    lines = [
        "# External Masterplan Alignment",
        "",
        f"- masterplan_path: {payload.get('masterplan_path') or '(none)'}",
        f"- source_file_count: {summary.get('source_file_count')}",
        f"- loaded_source_count: {summary.get('loaded_source_count')}",
        f"- packet_ready: {summary.get('packet_ready')}",
        f"- alignment_ok: {summary.get('alignment_ok')}",
        f"- source_directive_count: {summary.get('source_directive_count')}",
        f"- missing_count: {summary.get('missing_count')}",
        f"- missing_keys: {', '.join(summary.get('missing_keys') or []) or '(none)'}",
        "",
        "## Source Files",
    ]
    for row in payload.get("source_files") or []:
        lines.append(f"- {row.get('path')}: exists={row.get('exists')} nonempty={row.get('nonempty')}")
    lines.append("")
    lines.append("## Checks")
    for row in payload.get("checks") or []:
        lines.append(
            f"- {row.get('key')}: source_present={row.get('source_present')} "
            f"masterplan_present={row.get('masterplan_present')} aligned={row.get('aligned')}"
        )
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare external instruction txt files against the canonical MASTERPLAN.")
    parser.add_argument("--source", dest="sources", action="append", type=Path, default=[])
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--masterplan", type=Path, default=DEFAULT_MASTERPLAN)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "external_masterplan_alignment_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "external_masterplan_alignment_latest.md")
    args = parser.parse_args()

    source_paths = _normalize_source_paths(args.sources or discover_default_sources(args.source_dir))
    payload = build_alignment(source_paths, args.masterplan)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "json": str(args.json),
                "md": str(args.md),
                "alignment_ok": payload.get("summary", {}).get("alignment_ok"),
                "source_file_count": payload.get("summary", {}).get("source_file_count"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
