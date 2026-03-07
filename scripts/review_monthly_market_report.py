#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_JSON = ROOT / "logs" / "monthly_market_report_review_latest.json"
DEFAULT_REPORT_MD = ROOT / "logs" / "monthly_market_report_review_latest.md"

INTERNAL_ONLY_TOKENS = [
    "snapshot",
    "운영 문서",
    "기준 레퍼런스",
    "실시간 건설업 키워드",
    "CTA",
    "체류시간",
    "노출 후보",
    "대표님 실행 체크리스트",
    "발행 직전",
    "실시간 검색 흐름 요약",
    "먼저 확인할 키워드",
    "먼저 보는 키워드",
]

CUSTOMER_FACING_TOKENS = [
    "시장 흐름",
    "먼저 확인",
    "상담",
    "고객",
    "안내",
    "대표",
    "전망",
    "대응",
    "의사결정",
    "실무 전략",
]

REQUIRED_HEADINGS = [
    "30초 핵심 요약",
    "시장 한 문장 정리",
    "공공 vs 민간",
    "현장 체감이 늦는 이유",
    "상반기 변수 5가지",
    "실무 전략 7가지",
    "면허/실적 전략",
    "FAQ",
]

REQUIRED_SIGNAL_LABELS = [
    "경기 전망",
    "기업진단",
    "실태조사",
    "양도양수",
    "신규등록",
    "시공능력평가",
]


def _read_text(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp949"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _month_token_ok(subject: str, month_key: str) -> bool:
    match = re.fullmatch(r"(\d{4})-(\d{2})", str(month_key or "").strip())
    if not match:
        return False
    year = int(match.group(1))
    month = int(match.group(2))
    yy = year % 100
    tokens = [
        f"{yy}년 {month}월",
        f"{yy}년 {month:02d}월",
        f"{year}년 {month}월",
        f"{year}년 {month:02d}월",
        f"{year}.{month:02d}",
    ]
    src = re.sub(r"\s+", " ", subject or "")
    return any(token in src for token in tokens)


def _source_live_keywords(source_snapshot_path: Path | None) -> list[str]:
    if not source_snapshot_path or not source_snapshot_path.exists():
        return []
    try:
        payload = json.loads(_read_text(source_snapshot_path))
    except Exception:
        return []
    rows = list(payload.get("live_snapshot", {}).get("overall_ranked", []) or [])
    out: list[str] = []
    for row in rows[:6]:
        keyword = re.sub(r"\s+", " ", str(row.get("keyword", ""))).strip()
        if keyword and keyword not in out:
            out.append(keyword)
    return out


def _keyword_to_signal_label(keyword: str) -> str:
    src = re.sub(r"\s+", " ", str(keyword or "")).strip()
    if not src:
        return ""
    if "기업진단" in src or "실질자본금" in src:
        return "기업진단"
    if "실태조사" in src or "행정처분" in src or "등록말소" in src:
        return "실태조사"
    if "양도양수" in src:
        return "양도양수"
    if "신규등록" in src or "등록기준" in src or "기술인력" in src:
        return "신규등록"
    if "시공능력평가" in src or "입찰" in src or "공공 발주" in src:
        return "시공능력평가"
    if "경기" in src or "시장 리포트" in src or "상반기" in src:
        return "경기 전망"
    return ""


def review_bundle(subject_path: Path, body_path: Path, month_key: str, source_snapshot_path: Path | None = None) -> dict[str, Any]:
    blocking: list[str] = []
    warnings: list[str] = []
    if not subject_path.exists():
        blocking.append("subject_file_missing")
    if not body_path.exists():
        blocking.append("body_file_missing")
    if blocking:
        return {"month_key": month_key, "status": "fail", "blocking_issues": blocking, "warnings": warnings, "stats": {}}

    subject = _read_text(subject_path).strip()
    body = _read_text(body_path)
    soup = BeautifulSoup(body, "html.parser")
    plain = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    heading_texts = [re.sub(r"\s+", " ", node.get_text(" ", strip=True)) for node in soup.select("h1, h2, h3")]
    lower_plain = plain.lower()
    source_live_keywords = _source_live_keywords(source_snapshot_path)
    intro_excerpt = plain[:900]
    mentioned_live_keywords = [keyword for keyword in source_live_keywords if keyword in plain or keyword in subject]
    raw_keyword_heading_hits = [
        keyword
        for keyword in source_live_keywords
        if any(keyword in heading for heading in heading_texts)
    ]
    raw_keyword_intro_hits = [keyword for keyword in source_live_keywords if keyword in intro_excerpt]
    source_signal_labels = []
    for keyword in source_live_keywords:
        label = _keyword_to_signal_label(keyword)
        if label and label not in source_signal_labels:
            source_signal_labels.append(label)
    mentioned_signal_labels = [
        label for label in source_signal_labels if label in plain or label in subject
    ]

    stats: dict[str, Any] = {
        "subject_chars": len(subject),
        "body_chars": len(body),
        "plain_chars": len(plain),
        "heading_count": len(heading_texts),
        "faq_count": len(re.findall(r"Q\d+\.", plain)),
        "cta_phone": bool(re.search(r"tel:\d{8,}", body)),
        "cta_kakao": "open.kakao.com" in body,
        "has_legal_notice": ("법무" in plain and "세무" in plain and "실사" in plain and "확정" in plain),
        "month_token_ok": _month_token_ok(subject, month_key),
        "internal_only_hits": [token for token in INTERNAL_ONLY_TOKENS if token.lower() in lower_plain or token.lower() in subject.lower()],
        "customer_facing_hits": [token for token in CUSTOMER_FACING_TOKENS if token in plain or token in subject],
        "cta_subtitle_visible_style": "#e2e8f0" in body or "#eff6ff" in body,
        "source_live_keywords": source_live_keywords,
        "mentioned_live_keywords": mentioned_live_keywords,
        "source_signal_labels": source_signal_labels,
        "mentioned_signal_labels": mentioned_signal_labels,
        "raw_keyword_heading_hits": raw_keyword_heading_hits,
        "raw_keyword_intro_hits": raw_keyword_intro_hits,
        "keyword_centric_heading": any(("키워드" in heading or "검색 흐름" in heading) for heading in heading_texts),
        "required_heading_hits": [token for token in REQUIRED_HEADINGS if any(token in heading for heading in heading_texts)],
        "executive_identity_ok": ("건설업 대표" in subject) or ("건설업 대표" in plain),
    }

    if not subject:
        blocking.append("subject_empty")
    if not body.strip():
        blocking.append("body_empty")
    if not stats["month_token_ok"]:
        blocking.append("month_token_missing")
    if not stats["has_legal_notice"]:
        blocking.append("legal_notice_missing")
    if not (stats["cta_phone"] or stats["cta_kakao"]):
        blocking.append("cta_missing")
    if stats["internal_only_hits"]:
        blocking.append("internal_only_language_detected")
    if len(stats["customer_facing_hits"]) < 3:
        blocking.append("customer_facing_language_insufficient")
    if not stats["cta_subtitle_visible_style"]:
        blocking.append("cta_visibility_style_missing")
    if source_signal_labels and len(mentioned_signal_labels) < min(4, len(source_signal_labels), len(REQUIRED_SIGNAL_LABELS)):
        blocking.append("market_signal_coverage_low")
    if stats["keyword_centric_heading"]:
        blocking.append("keyword_centric_heading_detected")
    if raw_keyword_heading_hits:
        blocking.append("raw_keyword_heading_detected")
    if len(raw_keyword_intro_hits) > 1:
        blocking.append("raw_keyword_intro_exposure_high")
    if len(stats["required_heading_hits"]) < len(REQUIRED_HEADINGS):
        blocking.append("required_report_structure_missing")
    if not stats["executive_identity_ok"]:
        blocking.append("executive_identity_missing")
    if stats["plain_chars"] < 3200:
        blocking.append("report_depth_too_low")
    if stats["faq_count"] < 8:
        blocking.append("faq_depth_too_low")

    if stats["subject_chars"] < 24:
        warnings.append("subject_too_short")
    if stats["subject_chars"] > 120:
        warnings.append("subject_too_long")
    if len(heading_texts) < 5:
        warnings.append("heading_count_low")

    return {
        "month_key": month_key,
        "status": "pass" if not blocking else "fail",
        "blocking_issues": blocking,
        "warnings": warnings,
        "stats": stats,
        "subject_path": str(subject_path),
        "body_path": str(body_path),
    }


def build_review_report(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "ok": result.get("status") == "pass",
        "result": result,
    }


def _build_markdown(report: dict[str, Any]) -> str:
    row = report["result"]
    stats = row.get("stats", {})
    lines = [
        f"# Monthly Market Report Review ({report['generated_at']})",
        "",
        f"- month_key: {row.get('month_key', '')}",
        f"- overall_ok: {report['ok']}",
        f"- blocking_issues: {', '.join(row.get('blocking_issues', [])) if row.get('blocking_issues') else 'none'}",
        f"- warnings: {', '.join(row.get('warnings', [])) if row.get('warnings') else 'none'}",
        "",
        "## Stats",
        "",
        f"- subject_chars: {stats.get('subject_chars', 0)}",
        f"- body_chars: {stats.get('body_chars', 0)}",
        f"- plain_chars: {stats.get('plain_chars', 0)}",
        f"- heading_count: {stats.get('heading_count', 0)}",
        f"- faq_count: {stats.get('faq_count', 0)}",
        f"- month_token_ok: {stats.get('month_token_ok', False)}",
        f"- cta_phone: {stats.get('cta_phone', False)}",
        f"- cta_kakao: {stats.get('cta_kakao', False)}",
        f"- has_legal_notice: {stats.get('has_legal_notice', False)}",
        f"- internal_only_hits: {', '.join(stats.get('internal_only_hits', [])) if stats.get('internal_only_hits') else 'none'}",
        f"- customer_facing_hits: {', '.join(stats.get('customer_facing_hits', [])) if stats.get('customer_facing_hits') else 'none'}",
        f"- cta_subtitle_visible_style: {stats.get('cta_subtitle_visible_style', False)}",
        f"- mentioned_live_keywords: {', '.join(stats.get('mentioned_live_keywords', [])) if stats.get('mentioned_live_keywords') else 'none'}",
        f"- source_signal_labels: {', '.join(stats.get('source_signal_labels', [])) if stats.get('source_signal_labels') else 'none'}",
        f"- mentioned_signal_labels: {', '.join(stats.get('mentioned_signal_labels', [])) if stats.get('mentioned_signal_labels') else 'none'}",
        f"- raw_keyword_heading_hits: {', '.join(stats.get('raw_keyword_heading_hits', [])) if stats.get('raw_keyword_heading_hits') else 'none'}",
        f"- raw_keyword_intro_hits: {', '.join(stats.get('raw_keyword_intro_hits', [])) if stats.get('raw_keyword_intro_hits') else 'none'}",
        f"- keyword_centric_heading: {stats.get('keyword_centric_heading', False)}",
        f"- required_heading_hits: {', '.join(stats.get('required_heading_hits', [])) if stats.get('required_heading_hits') else 'none'}",
        f"- executive_identity_ok: {stats.get('executive_identity_ok', False)}",
        "",
    ]
    return "\n".join(lines)


def write_review_report(report_json: Path, report_md: Path, report: dict[str, Any]) -> None:
    _save_json(report_json, report)
    report_md.parent.mkdir(parents=True, exist_ok=True)
    report_md.write_text(_build_markdown(report), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review monthly market report bundle before publish.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "output" / "monthly_market_report"))
    parser.add_argument("--report-json", default=str(DEFAULT_REPORT_JSON))
    parser.add_argument("--report-md", default=str(DEFAULT_REPORT_MD))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    month_key = f"{int(args.year):04d}-{int(args.month):02d}"
    month_dir = Path(args.output_dir) / f"{int(args.year):04d}_{int(args.month):02d}"
    subject_path = month_dir / f"market_report_{int(args.year):04d}_{int(args.month):02d}_subject.txt"
    body_path = month_dir / f"market_report_{int(args.year):04d}_{int(args.month):02d}_body.html"
    source_snapshot_path = month_dir / f"market_report_{int(args.year):04d}_{int(args.month):02d}_source_snapshot.json"
    result = review_bundle(subject_path, body_path, month_key, source_snapshot_path=source_snapshot_path)
    report = build_review_report(result)
    report_json = Path(args.report_json)
    report_md = Path(args.report_md)
    write_review_report(report_json, report_md, report)
    print(f"[saved] {report_json}")
    print(f"[saved] {report_md}")
    print(f"[summary] ok={report['ok']} month={month_key}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
